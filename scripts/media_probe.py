#!/usr/bin/env python3
"""Inventory media files with ffprobe and report what affects an edit.

Read-only: the script runs ffprobe and never writes next to the media.
For each file it reports the container, duration, picture size as displayed
(rotation applied), frame rate and whether it varies, keyframe spacing,
HDR transfer, interlacing and audio layout, then lists findings that change
how the footage must be cut (`MED001`…`MED011`, see CHECKS.md).

    python3 scripts/media_probe.py originals/ --format markdown
    python3 scripts/media_probe.py exports/final.mp4 --format json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

VERSION = "1.0.0"
MEDIA_SUFFIXES = {
    ".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts", ".m2ts", ".mxf", ".mpg", ".mpeg",
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".aif", ".aiff",
}
# How much of each file the packet scan reads; enough to see a phone's frame-rate changes
# and a few keyframe intervals without decoding a long recording.
SCAN_SECONDS = 30
HDR_TRANSFERS = {"smpte2084": "PQ (HDR10 / Dolby Vision)", "arib-std-b67": "HLG"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


class ProbeError(RuntimeError):
    pass


def run_json(command: list[str]) -> dict:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProbeError(result.stderr.strip() or f"exit {result.returncode}")
    return json.loads(result.stdout or "{}")


def as_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def as_rate(text: str | None) -> float | None:
    if not text or text in {"0/0", "0/1"}:
        return None
    try:
        rate = Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None
    return float(rate) if rate > 0 else None


def rotation_of(stream: dict) -> int:
    for item in stream.get("side_data_list") or []:
        if "rotation" in item:
            return int(round(float(item["rotation"])))
    rotate = (stream.get("tags") or {}).get("rotate")
    if rotate is not None:
        # The legacy tag is clockwise; the display matrix is counter-clockwise.
        return -int(rotate)
    return 0


def has_dolby_vision(stream: dict) -> bool:
    return any("DOVI" in (item.get("side_data_type") or "") for item in stream.get("side_data_list") or [])


def packet_scan(ffprobe: str, path: Path) -> dict:
    """Read video packet timestamps from the first SCAN_SECONDS to find frame-rate changes and GOP size."""
    data = run_json([
        ffprobe, "-v", "error", "-select_streams", "v:0", "-read_intervals", f"%+{SCAN_SECONDS}",
        "-show_entries", "packet=pts_time,flags", "-of", "json", str(path),
    ])
    times = []
    keyframes = []
    for packet in data.get("packets", []):
        time = as_float(packet.get("pts_time"))
        if time is None:
            continue
        times.append(time)
        if "K" in (packet.get("flags") or ""):
            keyframes.append(time)
    times.sort()
    keyframes.sort()
    deltas = [round(b - a, 4) for a, b in zip(times, times[1:]) if b > a]
    result: dict = {"packets": len(times), "scanned_seconds": SCAN_SECONDS}
    if deltas:
        ordered = sorted(deltas)
        median = ordered[len(ordered) // 2]
        off = [d for d in deltas if abs(d - median) > median * 0.25]
        result.update({
            "median_frame_interval": median,
            "min_frame_interval": ordered[0],
            "max_frame_interval": ordered[-1],
            "irregular_share": round(len(off) / len(deltas), 4),
        })
    if len(keyframes) >= 2:
        gaps = [b - a for a, b in zip(keyframes, keyframes[1:])]
        result["max_keyframe_interval"] = round(max(gaps), 3)
        result["keyframes_seen"] = len(keyframes)
    elif keyframes:
        result["keyframes_seen"] = 1
    return result


def describe(ffprobe: str, path: Path, packets: bool = True) -> dict:
    data = run_json([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    info: dict = {
        "path": str(path),
        "container": fmt.get("format_name"),
        "duration": as_float(fmt.get("duration")),
        "size_bytes": int(fmt["size"]) if str(fmt.get("size", "")).isdigit() else None,
        "creation_time": (fmt.get("tags") or {}).get("creation_time"),
        "video": None,
        "audio": [],
    }
    if video:
        stream = video[0]
        width, height = stream.get("width"), stream.get("height")
        rotation = rotation_of(stream)
        display = (width, height)
        if width and height and abs(rotation) % 180 == 90:
            display = (height, width)
        transfer = stream.get("color_transfer")
        info["video"] = {
            "codec": stream.get("codec_name"),
            "profile": stream.get("profile"),
            "coded_width": width,
            "coded_height": height,
            "rotation": rotation,
            "display_width": display[0],
            "display_height": display[1],
            "sample_aspect_ratio": stream.get("sample_aspect_ratio"),
            "pix_fmt": stream.get("pix_fmt"),
            "r_frame_rate": stream.get("r_frame_rate"),
            "avg_frame_rate": stream.get("avg_frame_rate"),
            "frame_rate": as_rate(stream.get("avg_frame_rate")) or as_rate(stream.get("r_frame_rate")),
            "field_order": stream.get("field_order"),
            "color_transfer": transfer,
            "color_primaries": stream.get("color_primaries"),
            "hdr": HDR_TRANSFERS.get(transfer or "") or ("Dolby Vision" if has_dolby_vision(stream) else None),
            "duration": as_float(stream.get("duration")),
            "timecode": (stream.get("tags") or {}).get("timecode"),
        }
        if packets:
            info["video"]["scan"] = packet_scan(ffprobe, path)
    for stream in audio:
        info["audio"].append({
            "codec": stream.get("codec_name"),
            "sample_rate": int(stream["sample_rate"]) if str(stream.get("sample_rate", "")).isdigit() else None,
            "channels": stream.get("channels"),
            "channel_layout": stream.get("channel_layout"),
            "duration": as_float(stream.get("duration")),
            "language": (stream.get("tags") or {}).get("language"),
        })
    return info


def finding(rule: str, severity: str, path: str, message: str, action: str) -> dict:
    return {"rule": rule, "severity": severity, "path": path, "message": message, "action": action}


def file_findings(info: dict) -> list[dict]:
    path = info["path"]
    found = []
    video = info.get("video")
    audio = info.get("audio") or []
    name = Path(path).name
    if video:
        scan = video.get("scan") or {}
        r_rate = as_rate(video.get("r_frame_rate"))
        avg_rate = as_rate(video.get("avg_frame_rate"))
        mismatch = r_rate and avg_rate and abs(r_rate - avg_rate) / r_rate > 0.01
        irregular = scan.get("irregular_share", 0) > 0.02
        if irregular or (mismatch and scan.get("packets", 0) == 0):
            found.append(finding(
                "MED001", "high", path,
                f"variable frame rate: frame intervals range {scan.get('min_frame_interval')}–"
                f"{scan.get('max_frame_interval')} s ({scan.get('irregular_share', 0):.1%} off the median "
                f"in the first {SCAN_SECONDS} s); r_frame_rate {video.get('r_frame_rate')}, "
                f"avg_frame_rate {video.get('avg_frame_rate')}",
                "make a constant-frame-rate working copy before cutting, record the conversion in project.md, "
                "and cut the copy, not the original",
            ))
        if video.get("rotation"):
            found.append(finding(
                "MED002", "medium", path,
                f"rotation metadata {video['rotation']}°: coded {video['coded_width']}×{video['coded_height']}, "
                f"displayed {video['display_width']}×{video['display_height']}",
                "plan layouts on the displayed size; filters see the rotated picture only when ffmpeg autorotates "
                "on input (its default) — keep that default or apply the rotation explicitly",
            ))
        max_gop = scan.get("max_keyframe_interval")
        if max_gop and max_gop > 2.0:
            found.append(finding(
                "MED006", "info", path,
                f"keyframes up to {max_gop} s apart",
                "re-encode every cut; a stream copy can only start cleanly on a keyframe",
            ))
        if video.get("hdr"):
            found.append(finding(
                "MED010", "medium", path,
                f"HDR picture ({video['hdr']}, transfer {video.get('color_transfer')}, "
                f"primaries {video.get('color_primaries')}, {video.get('pix_fmt')})",
                "decide the delivery (SDR or HDR) before mixing it with SDR sources such as screen recordings; "
                "convert with a tone-mapping step, not a plain pixel-format change",
            ))
        if video.get("field_order") not in (None, "progressive", "unknown"):
            found.append(finding(
                "MED009", "medium", path,
                f"interlaced picture (field order {video['field_order']})",
                "deinterlace once in the working copy before scaling or cutting",
            ))
        if audio and video.get("duration") and audio[0].get("duration"):
            gap = abs(video["duration"] - audio[0]["duration"])
            if gap > 0.1:
                found.append(finding(
                    "MED008", "medium", path,
                    f"video and audio streams differ in length by {gap:.2f} s",
                    "check sync at the start and the end before cutting; trim the working copy to the shorter stream",
                ))
        if not audio:
            found.append(finding(
                "MED003", "info", path, "no audio stream",
                "fine for screen recordings and B-roll; a speech take without audio cannot be cut by transcript",
            ))
    elif not audio:
        found.append(finding("MED011", "high", path, "no video or audio stream ffprobe can read",
                             "check the file before planning around it"))
    if any(ch in name for ch in " ()[]{}&$#'\"") or not name.isascii():
        found.append(finding(
            "MED007", "low", path, "file name has spaces, brackets, quotes or non-ASCII characters",
            "give working copies stable names such as take_01.mp4 and screen_02.mov; keep the original untouched",
        ))
    return found


def cross_findings(infos: list[dict]) -> list[dict]:
    found = []
    rates = {}
    for info in infos:
        video = info.get("video")
        if video and video.get("frame_rate"):
            rates.setdefault(round(video["frame_rate"], 3), []).append(Path(info["path"]).name)
    if len(rates) > 1:
        listing = "; ".join(f"{rate:g} fps: {', '.join(names)}" for rate, names in sorted(rates.items()))
        found.append(finding(
            "MED004", "medium", "*", f"sources have different frame rates ({listing})",
            "choose one delivery frame rate in the brief and convert every working copy to it once",
        ))
    layouts = {}
    for info in infos:
        for stream in info.get("audio") or []:
            key = (stream.get("sample_rate"), stream.get("channels"))
            layouts.setdefault(key, []).append(Path(info["path"]).name)
    if len(layouts) > 1:
        listing = "; ".join(f"{rate} Hz × {channels} ch: {', '.join(names)}"
                            for (rate, channels), names in sorted(layouts.items(), key=str))
        found.append(finding(
            "MED005", "low", "*", f"audio streams differ in sample rate or channels ({listing})",
            "resample to one rate and layout when the working copies are made",
        ))
    return found


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*")
                                if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES and not p.name.startswith(".")))
        elif path.is_file():
            files.append(path)
        else:
            raise ProbeError(f"not found: {raw}")
    return files


def report(paths: list[str], packets: bool = True, ffprobe: str | None = None) -> dict:
    ffprobe = ffprobe or shutil.which("ffprobe")
    if not ffprobe:
        raise ProbeError("ffprobe not found on PATH; install FFmpeg first (it needs approval)")
    infos, errors = [], []
    for path in collect(paths):
        try:
            infos.append(describe(ffprobe, path, packets=packets))
        except ProbeError as error:
            errors.append({"path": str(path), "error": str(error)})
    findings = [item for info in infos for item in file_findings(info)] + cross_findings(infos)
    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["rule"], item["path"]))
    return {"tool": "media_probe", "version": VERSION, "files": infos, "errors": errors, "findings": findings}


def seconds(value: float | None) -> str:
    if value is None:
        return "—"
    minutes, rest = divmod(value, 60)
    return f"{int(minutes):02d}:{rest:06.3f}"


def markdown(result: dict) -> str:
    lines = [f"# Media inventory (media_probe {result['version']})", ""]
    lines += ["| File | Duration | Picture (displayed) | Frame rate | Audio | Notes |",
              "| --- | --- | --- | --- | --- | --- |"]
    for info in result["files"]:
        video = info.get("video")
        picture = rate = "—"
        notes = []
        if video:
            picture = f"{video['display_width']}×{video['display_height']} {video['codec']}"
            rate = f"{video['frame_rate']:.3f}".rstrip("0").rstrip(".") if video.get("frame_rate") else "—"
            if video.get("rotation"):
                notes.append(f"rotated {video['rotation']}°")
            if video.get("hdr"):
                notes.append(video["hdr"])
        sound = ", ".join(f"{a['codec']} {a['sample_rate']} Hz {a['channels']} ch" for a in info["audio"]) or "none"
        lines.append(f"| `{info['path']}` | {seconds(info['duration'])} | {picture} | {rate} | {sound} | "
                     f"{'; '.join(notes) or ''} |")
    for error in result["errors"]:
        lines.append(f"| `{error['path']}` | — | — | — | — | ffprobe failed: {error['error']} |")
    lines += ["", "## Findings", ""]
    if not result["findings"]:
        lines.append("None.")
    for item in result["findings"]:
        lines.append(f"- **{item['rule']}** ({item['severity']}) `{item['path']}` — {item['message']}. "
                     f"Action: {item['action']}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", help="Media files or folders (searched recursively)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--no-packets", action="store_true",
                        help="Skip the packet scan (no frame-rate variation or keyframe findings)")
    args = parser.parse_args(argv)
    try:
        result = report(args.paths, packets=not args.no_packets)
    except ProbeError as error:
        print(f"media_probe: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(markdown(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
