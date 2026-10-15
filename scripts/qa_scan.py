#!/usr/bin/env python3
"""Scan a rendered video for defects a person should not have to find by eye.

Read-only: one ffmpeg decoding pass and ffprobe, nothing written unless
`--evidence-dir` asks for frames. It compares the file with the brief
(size, frame rate, duration), finds black and frozen intervals, long
silences, loudness and true peak, and with `--edl` and `--captions` checks the
cut's length and the subtitles against the final timeline
(`QA001`…`QA013`, see CHECKS.md). It never judges meaning, rhythm or taste:
the report lists those as not checked.

    python3 scripts/qa_scan.py exports/final.mp4 --width 1080 --height 1920 --fps 30 \\
        --edl edit/edl.json --captions exports/final.srt --loudness-target -14
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import captions as captions_module  # noqa: E402
import media_probe  # noqa: E402

VERSION = "1.0.0"
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
NOT_CHECKED = [
    "whether the cut keeps the meaning of what was said (compare with the approved script and the sources)",
    "rhythm, intonation and breath at every join (listen on headphones and on a phone speaker)",
    "faces, buttons or captions covered by graphics or by the platform's interface",
    "legibility of text on a real phone at the delivery size",
    "facts, names and numbers on screen against their sources",
    "rights to music, fonts, footage and voices (the asset log in project.md)",
    "personal data, notifications or test labels visible in the picture",
]


def finding(rule: str, severity: str, message: str, action: str, start: float | None = None,
            end: float | None = None) -> dict:
    item = {"rule": rule, "severity": severity, "message": message, "action": action}
    if start is not None:
        item["start"] = round(start, 3)
    if end is not None:
        item["end"] = round(end, 3)
    return item


def fmt(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    minutes, secs = divmod(max(seconds, 0), 60)
    return f"{int(minutes):02d}:{secs:06.3f}"


def mp4_box_order(path: Path) -> list[str]:
    """Top-level box types of an MP4/MOV file, in file order (stops at 64 boxes)."""
    order = []
    with path.open("rb") as handle:
        offset = 0
        size_total = path.stat().st_size
        while offset < size_total and len(order) < 64:
            handle.seek(offset)
            header = handle.read(16)
            if len(header) < 8:
                break
            size, kind = struct.unpack(">I4s", header[:8])
            if size == 1 and len(header) == 16:
                size = struct.unpack(">Q", header[8:16])[0]
            elif size == 0:
                size = size_total - offset
            if size < 8:
                break
            order.append(kind.decode("latin-1"))
            offset += size
    return order


def decode_pass(ffmpeg: str, path: Path, has_video: bool, has_audio: bool, options) -> dict:
    command = [ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-i", str(path)]
    if has_video:
        command += ["-map", "0:v:0", "-vf",
                    f"blackdetect=d={options.black_min}:pix_th={options.black_pixel},"
                    f"freezedetect=n={options.freeze_noise}:d={options.freeze_min}"]
    if has_audio:
        command += ["-map", "0:a:0", "-af",
                    f"silencedetect=n={options.silence_db}dB:d={options.silence_min},ebur128=peak=true:framelog=verbose"]
    command += ["-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True)
    log = result.stderr
    if result.returncode != 0:
        raise RuntimeError(log.strip().splitlines()[-1] if log.strip() else f"ffmpeg exit {result.returncode}")
    black = [(float(a), float(b)) for a, b in re.findall(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", log)]
    freeze_starts = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", log)]
    freeze_ends = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", log)]
    silence_starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    silence_ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    summary = log.rsplit("Summary:", 1)[-1] if "Summary:" in log else ""
    integrated = re.search(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", summary)
    lra = re.search(r"LRA:\s*([\d.]+)\s*LU", summary)
    peak = re.search(r"True peak:\s*\n\s*Peak:\s*(-?[\d.]+|-inf)\s*dBFS", summary)
    return {
        "black": black,
        "freeze": list(zip(freeze_starts, freeze_ends + [None] * (len(freeze_starts) - len(freeze_ends)))),
        "silence": list(zip(silence_starts, silence_ends + [None] * (len(silence_starts) - len(silence_ends)))),
        "integrated_lufs": None if not integrated or integrated.group(1) == "-inf" else float(integrated.group(1)),
        "loudness_range_lu": float(lra.group(1)) if lra else None,
        "true_peak_dbfs": None if not peak or peak.group(1) == "-inf" else float(peak.group(1)),
    }


def extract_frames(ffmpeg: str, path: Path, times: list[float], directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for time in times:
        target = directory / f"frame_{time:09.3f}.png"
        if target.exists():
            written.append(str(target))
            continue
        subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-ss", f"{time:.3f}", "-i", str(path), "-frames:v", "1",
                        str(target)], check=False)
        if target.exists():
            written.append(str(target))
    return written


def scan(path: Path, options) -> dict:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe must be on PATH")
    info = media_probe.describe(ffprobe, path)
    video, audio = info.get("video"), (info.get("audio") or [None])[0]
    duration = info.get("duration")
    found: list[dict] = []
    for item in media_probe.file_findings(info):
        if item["rule"] == "MED001":
            found.append(finding("QA011", "high", "the delivery file has a variable frame rate: " + item["message"],
                                 "re-render at a constant frame rate; some platforms and editors drift on VFR"))
        elif item["rule"] == "MED008":
            found.append(finding("QA010", "medium", item["message"], "find where sync drifts; re-render from the project"))
    if not video:
        found.append(finding("QA001", "high", "no video stream", "render the picture"))
    if not audio:
        found.append(finding("QA012", "medium", "no audio stream", "confirm a silent video is intended"))
    elif audio.get("channels") == 1:
        found.append(finding("QA012", "info", "mono audio", "fine for speech; say so in the handoff"))

    if video:
        expected = []
        if options.width and video["display_width"] != options.width:
            expected.append(f"width {video['display_width']} (brief {options.width})")
        if options.height and video["display_height"] != options.height:
            expected.append(f"height {video['display_height']} (brief {options.height})")
        if options.fps and video.get("frame_rate") and abs(video["frame_rate"] - options.fps) > 0.01:
            expected.append(f"{video['frame_rate']:.3f} fps (brief {options.fps:g})")
        if expected:
            found.append(finding("QA001", "high", "does not match the brief: " + ", ".join(expected),
                                 "render again with the brief's settings"))
        if video.get("pix_fmt") and video["pix_fmt"] != "yuv420p" and not video.get("hdr"):
            found.append(finding("QA013", "medium", f"pixel format {video['pix_fmt']}",
                                 "deliver yuv420p unless the platform asks otherwise; many players cannot decode "
                                 "4:2:2, 4:4:4 or 10-bit H.264"))
    if options.duration and duration is not None and abs(duration - options.duration) > options.duration_tolerance:
        found.append(finding("QA001", "high", f"duration {fmt(duration)}, brief {fmt(options.duration)} "
                             f"(± {options.duration_tolerance:g} s)", "check the cut against the brief"))

    if options.edl:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import edl as edl_module  # noqa: E402
        plan = edl_module.load(options.edl)
        planned = plan.total_frames / plan.fps
        tolerance = max(1.5 / plan.fps, 0.05)
        if duration is not None and abs(duration - planned) > tolerance:
            found.append(finding("QA009", "high", f"file lasts {fmt(duration)}, the EDL adds up to {fmt(planned)}",
                                 "the render is not the approved cut, or something was added after it; find out which"))

    if path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        order = mp4_box_order(path)
        if "moov" in order and "mdat" in order and order.index("moov") > order.index("mdat"):
            found.append(finding("QA007", "low", "the index (moov) sits after the media data",
                                 "remux with -movflags +faststart so playback can start before the download ends"))

    measured = decode_pass(ffmpeg, path, bool(video), bool(audio), options)
    for start, end in measured["black"]:
        at_start = start <= 0.05
        found.append(finding("QA002", "high" if at_start else "medium",
                             f"black picture {fmt(start)}–{fmt(end)} ({end - start:.2f} s)"
                             + (" at the very start" if at_start else ""),
                             "check that the fade or gap is intended; a black first frame often becomes the thumbnail",
                             start, end))
    for start, end in measured["freeze"]:
        found.append(finding("QA003", "low", f"picture does not change {fmt(start)}–{fmt(end)}",
                             "fine for a deliberate hold; otherwise a stalled source or a missing asset", start, end))
    for start, end in measured["silence"]:
        start = max(start, 0.0)
        tail = duration is not None and end is not None and end >= duration - 0.05
        if tail and (end - start) < 2.0:
            continue
        found.append(finding("QA004", "medium", f"silence {fmt(start)}–{fmt(end)}"
                             + (f" ({end - start:.2f} s)" if end is not None else ""),
                             "listen: a dropped track, a long pause, or an intended beat", start, end))
    lufs, peak = measured["integrated_lufs"], measured["true_peak_dbfs"]
    if audio and lufs is not None:
        if options.loudness_target is not None and abs(lufs - options.loudness_target) > options.loudness_tolerance:
            found.append(finding("QA005", "medium", f"integrated loudness {lufs:.1f} LUFS, target "
                                 f"{options.loudness_target:g} ± {options.loudness_tolerance:g} LU",
                                 "normalise the final mix (two-pass loudnorm), then re-measure"))
        if peak is not None and peak > options.true_peak_max:
            found.append(finding("QA006", "medium", f"true peak {peak:.1f} dBTP, ceiling {options.true_peak_max:g} dBTP",
                                 "lower the peaks with a true-peak limiter or loudnorm; lossy encoding adds overs"))

    if options.captions:
        cues, errors = captions_module.parse_srt(Path(options.captions).read_text(encoding="utf-8"))
        defaults = dict(captions_module.DEFAULTS)
        glossary = captions_module.load_glossary(options.glossary) if options.glossary else []
        for item in captions_module.check(cues, defaults, duration, glossary):
            item = dict(item)
            item["message"] = f"captions {item['rule']}: " + item["message"]
            item["rule"] = "QA008"
            found.append(item)
        for error in errors:
            found.append(finding("QA008", "high", f"captions: {error}", "fix the SRT syntax"))

    evidence = []
    if options.evidence_dir:
        times = sorted({f["start"] for f in found if "start" in f})[:24]
        evidence = extract_frames(ffmpeg, path, times, Path(options.evidence_dir))

    found.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f.get("start", -1), f["rule"]))
    return {"tool": "qa_scan", "version": VERSION, "file": str(path), "duration": duration,
            "video": video and {k: video[k] for k in ("display_width", "display_height", "frame_rate", "codec", "pix_fmt")},
            "audio": audio and {k: audio[k] for k in ("codec", "sample_rate", "channels")},
            "loudness": {"integrated_lufs": lufs, "loudness_range_lu": measured["loudness_range_lu"],
                         "true_peak_dbtp": peak},
            "findings": found, "evidence": evidence, "not_checked": NOT_CHECKED}


def markdown(result: dict) -> str:
    video, audio, loud = result["video"], result["audio"], result["loudness"]
    lines = [f"# QA scan (qa_scan {result['version']})", "", f"File: `{result['file']}` · {fmt(result['duration'])}"]
    if video:
        lines.append(f"Picture: {video['display_width']}×{video['display_height']} {video['codec']} {video['pix_fmt']}, "
                     f"{(video['frame_rate'] or 0):.3f} fps")
    if audio:
        lines.append(f"Sound: {audio['codec']} {audio['sample_rate']} Hz {audio['channels']} ch · "
                     f"integrated {loud['integrated_lufs'] if loud['integrated_lufs'] is not None else '—'} LUFS · "
                     f"LRA {loud['loudness_range_lu'] if loud['loudness_range_lu'] is not None else '—'} LU · "
                     f"true peak {loud['true_peak_dbtp'] if loud['true_peak_dbtp'] is not None else '—'} dBTP")
    lines += ["", "## Findings", ""]
    if not result["findings"]:
        lines.append("None.")
    for item in result["findings"]:
        where = f"{fmt(item['start'])} " if "start" in item else ""
        lines.append(f"- **{item['rule']}** ({item['severity']}) {where}— {item['message']}. Action: {item['action']}.")
    if result["evidence"]:
        lines += ["", "## Evidence frames", ""] + [f"- `{path}`" for path in result["evidence"]]
    lines += ["", "## Not checked by this scan", ""] + [f"- {item}" for item in result["not_checked"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--fps", type=float)
    parser.add_argument("--duration", type=float, help="Expected duration in seconds")
    parser.add_argument("--duration-tolerance", type=float, default=0.5)
    parser.add_argument("--edl", help="The approved EDL; the file must last as long as it adds up to")
    parser.add_argument("--captions", help="The SRT delivered with the video")
    parser.add_argument("--glossary", help="Terms the captions must spell exactly")
    parser.add_argument("--loudness-target", type=float, help="Integrated loudness target, LUFS")
    parser.add_argument("--loudness-tolerance", type=float, default=1.0)
    parser.add_argument("--true-peak-max", type=float, default=-1.0, help="dBTP ceiling")
    parser.add_argument("--black-min", type=float, default=0.1, help="Shortest black interval to report, s")
    parser.add_argument("--black-pixel", type=float, default=0.10, help="blackdetect pix_th")
    parser.add_argument("--freeze-min", type=float, default=2.0, help="Shortest frozen interval to report, s")
    parser.add_argument("--freeze-noise", default="-60dB", help="freezedetect noise tolerance")
    parser.add_argument("--silence-min", type=float, default=1.5, help="Shortest silence to report, s")
    parser.add_argument("--silence-db", type=float, default=-50.0, help="silencedetect threshold, dB")
    parser.add_argument("--evidence-dir", help="Write a PNG frame at each finding's start time here")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args(argv)
    path = Path(args.video)
    if not path.is_file():
        print(f"qa_scan: not found: {path}", file=sys.stderr)
        return 2
    try:
        result = scan(path, args)
    except (RuntimeError, media_probe.ProbeError, ValueError) as error:
        print(f"qa_scan: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(markdown(result), end="")
    return 1 if any(f["severity"] == "high" for f in result["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
