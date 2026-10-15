#!/usr/bin/env python3
"""Re-measure the FFmpeg behaviour that references/measured-behavior.md records.

Every probe makes its own synthetic media (lavfi test patterns and tones) in a
temporary directory, runs the operation the skills advise for or against, and
returns what it observed. `--check` compares the observations with
expectations.json next to this file. Nothing outside the temporary directory
is written.

    python3 scripts/probes/ffmpeg_probes.py --format markdown
    python3 scripts/probes/ffmpeg_probes.py --check
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))

import edl as edl_module  # noqa: E402
import media_probe  # noqa: E402

GRAY_W, GRAY_H = 48, 27


def ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args],
                          capture_output=True, text=True)


def must(result: subprocess.CompletedProcess) -> None:
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def gray_frames(path: Path, ignore_editlist: bool = False) -> list[bytes]:
    command = ["ffmpeg", "-v", "error", "-nostdin"]
    if ignore_editlist:
        command += ["-ignore_editlist", "1"]
    command += ["-i", str(path), "-map", "0:v:0", "-vf", f"scale={GRAY_W}:{GRAY_H},format=gray",
                "-f", "rawvideo", "-"]
    raw = subprocess.run(command, capture_output=True, check=True).stdout
    size = GRAY_W * GRAY_H
    return [raw[i:i + size] for i in range(0, len(raw) - size + 1, size)]


def pcm(path: Path) -> tuple[int, ...]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "1",
                          "-ar", "48000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return struct.unpack(f"<{len(raw) // 2}h", raw)


def difference(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def nearest(frame: bytes, source: list[bytes], around: int | None = None, radius: int = 4) -> int:
    indices = range(len(source)) if around is None else range(max(0, around - radius),
                                                                min(len(source), around + radius + 1))
    return min(indices, key=lambda j: difference(frame, source[j]))


def onsets(samples: tuple[int, ...], threshold: float = 0.1, quiet: int = 480) -> list[float]:
    found, run = [], quiet + 1
    limit = threshold * 32767
    for i, value in enumerate(samples):
        if abs(value) > limit:
            if run > quiet:
                found.append(round(i / 48000, 4))
            run = 0
        else:
            run += 1
    return found


# --- probes -------------------------------------------------------------------------------------

def probe_edl_render(work: Path) -> dict:
    """M1: edl.py render keeps exactly the frames [in, out) and the audio lands where `map` says."""
    source = work / "take.mov"
    must(ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=10",
                "-f", "lavfi", "-i", "aevalsrc='0.5*sin(2*PI*440*t)*between(mod(t\\,2)\\,1.0\\,1.2)':s=48000:d=10",
                "-c:v", "libx264", "-g", "90", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ac", "1", str(source)))
    plan = {"fps": 30, "sources": {"take": "take.mov"}, "audio_fade_ms": 10, "clips": [
        {"id": "c01", "source": "take", "in": "00:00.50", "out": "00:02.00", "reason": "probe"},
        {"id": "c02", "source": "take", "in": "00:03.20", "out": "00:05.50", "reason": "probe"},
        {"id": "c03", "source": "take", "in": 8.0, "out": "00:09.40", "reason": "probe"}]}
    (work / "edl.json").write_text(json.dumps(plan), encoding="utf-8")
    edl = edl_module.load(work / "edl.json")
    output = work / "cut.mp4"
    command = edl_module.render_command(edl, output, crf=18, preset="veryfast")
    must(subprocess.run(command, capture_output=True, text=True))
    src_frames, out_frames = gray_frames(source), gray_frames(output)
    expected = [f for clip in edl.clips for f in range(clip.in_frame, clip.out_frame)]
    wrong = sum(1 for k, frame in enumerate(out_frames[:len(expected)]) if nearest(frame, src_frames, expected[k]) != expected[k])
    beeps_out = onsets(pcm(output))
    beeps_mapped = [t for beep in (1.0, 3.0, 5.0, 7.0, 9.0) for t in edl_module.map_time(edl, "take", beep)]
    error_ms = max(abs(a - b) for a, b in zip(beeps_out, beeps_mapped)) * 1000 if beeps_out else None
    return {"frames_expected": len(expected), "frames_rendered": len(out_frames), "frames_wrong": wrong,
            "beeps_rendered": beeps_out, "beeps_mapped": [round(t, 4) for t in beeps_mapped],
            "beep_error_ms": round(error_ms, 2) if error_ms is not None else None}


def probe_stream_copy(work: Path) -> dict:
    """M2: `-ss` before `-i` with `-c copy` starts at the keyframe before the cut point."""
    source = work / "gop.mp4"
    must(ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=10", "-c:v", "libx264",
                "-g", "90", "-keyint_min", "90", "-sc_threshold", "0", "-pix_fmt", "yuv420p", str(source)))
    output = work / "copy.mp4"
    must(ffmpeg("-ss", "4", "-i", str(source), "-t", "2", "-c", "copy", str(output)))
    packets = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                              "stream=nb_read_packets", "-of", "csv=p=0", str(output)],
                             capture_output=True, text=True).stdout.strip()
    duration = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                               str(output)], capture_output=True, text=True).stdout.strip()
    src = gray_frames(source)
    honoured = gray_frames(output)
    ignored = gray_frames(output, ignore_editlist=True)
    return {"requested_start": 4.0, "requested_duration": 2.0, "keyframe_interval": 3.0,
            "packets_in_file": int(packets), "reported_duration": float(duration),
            "first_frame_editlist_honoured": round(nearest(honoured[0], src) / 30, 3),
            "first_frame_editlist_ignored": round(nearest(ignored[0], src) / 30, 3)}


def probe_join_click(work: Path) -> dict:
    """M3: a hard audio join steps far beyond the tone's own slope; 10 ms fades remove the step."""
    source = work / "tone.mov"
    must(ffmpeg("-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=4", "-f", "lavfi",
                "-i", "sine=frequency=440:sample_rate=48000:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "pcm_s16le", str(source)))
    result = {}
    for fade in (0, 10):
        plan = {"fps": 30, "sources": {"s": "tone.mov"}, "audio_fade_ms": fade, "clips": [
            {"id": "a", "source": "s", "in": "16f", "out": "31f", "reason": "probe"},
            {"id": "b", "source": "s", "in": "63f", "out": "90f", "reason": "probe"}]}
        (work / f"tone_{fade}.json").write_text(json.dumps(plan), encoding="utf-8")
        edl = edl_module.load(work / f"tone_{fade}.json")
        output = work / f"tone_{fade}.mov"
        command = edl_module.render_command(edl, output, crf=30, preset="ultrafast")
        command[command.index("aac")] = "pcm_s16le"
        must(subprocess.run(command, capture_output=True, text=True))
        samples = pcm(output)
        join = round(15 / 30 * 48000)
        steps = [abs(samples[i + 1] - samples[i]) for i in range(len(samples) - 1)]
        body = steps[2000:join - 1000] + steps[join + 1000:-2000]
        result[f"step_ratio_fade_{fade}ms"] = round(max(steps[join - 48:join + 48]) / max(body), 2)
    return result


def probe_concat_mismatch(work: Path) -> dict:
    """M4: the concat filter rejects mixed sizes; the concat demuxer with -c copy accepts them silently."""
    big, small = work / "big.mov", work / "small.mov"
    for path, size in ((big, "320x180"), (small, "160x90")):
        must(ffmpeg("-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration=1", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(path)))
    filtered = ffmpeg("-i", str(big), "-i", str(small), "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                      "-map", "[v]", "-f", "null", "-")
    listing = work / "list.txt"
    listing.write_text(f"file '{big}'\nfile '{small}'\n", encoding="utf-8")
    joined = work / "joined.mov"
    demuxed = ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined))
    size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", str(joined)], capture_output=True, text=True).stdout.strip()
    return {"filter_exit_ok": filtered.returncode == 0,
            "filter_error_says_do_not_match": "do not match" in filtered.stderr,
            "demuxer_exit_ok": demuxed.returncode == 0, "demuxer_reported_size": size.replace(",", "x")}


def probe_rotation(work: Path) -> dict:
    """M5: rotation metadata leaves coded width/height unchanged; media_probe reports the displayed size."""
    plain, rotated = work / "landscape.mp4", work / "rotated.mp4"
    must(ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", str(plain)))
    must(ffmpeg("-display_rotation", "90", "-i", str(plain), "-c", "copy", str(rotated)))
    info = media_probe.describe(shutil.which("ffprobe"), rotated, packets=False)["video"]
    still = work / "frame.png"
    must(ffmpeg("-i", str(rotated), "-frames:v", "1", str(still)))
    decoded = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                              str(still)], capture_output=True, text=True).stdout.strip().replace(",", "x")
    return {"coded": f"{info['coded_width']}x{info['coded_height']}", "rotation": info["rotation"],
            "displayed": f"{info['display_width']}x{info['display_height']}", "decoded_frame": decoded}


def probe_vfr(work: Path) -> dict:
    """M6: a variable-frame-rate file is caught by the packet scan; a constant one is not."""
    vfr, cfr = work / "vfr.mp4", work / "cfr.mp4"
    must(ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=60:duration=6",
                "-vf", "setpts='if(lt(N,90),N*2/60/TB,(3+(N-90)/60)/TB)'", "-fps_mode", "vfr",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vfr)))
    must(ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=3", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", str(cfr)))
    result = {}
    for label, path in (("vfr", vfr), ("cfr", cfr)):
        info = media_probe.describe(shutil.which("ffprobe"), path)
        rules = [f["rule"] for f in media_probe.file_findings(info)]
        result[f"{label}_flagged"] = "MED001" in rules
        result[f"{label}_r_frame_rate"] = info["video"]["r_frame_rate"]
        result[f"{label}_avg_frame_rate"] = info["video"]["avg_frame_rate"]
    return result


PROBES = {
    "M1": probe_edl_render,
    "M2": probe_stream_copy,
    "M3": probe_join_click,
    "M4": probe_concat_mismatch,
    "M5": probe_rotation,
    "M6": probe_vfr,
}


def version() -> str:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True).stdout
    return out.splitlines()[0] if out else "unknown"


def compare(observed: dict, expected: dict) -> list[str]:
    failures = []
    for key, rule in expected.items():
        value = observed.get(key)
        if isinstance(rule, dict):
            if "max" in rule and not (value is not None and value <= rule["max"]):
                failures.append(f"{key}={value} is above {rule['max']}")
            if "min" in rule and not (value is not None and value >= rule["min"]):
                failures.append(f"{key}={value} is below {rule['min']}")
        elif value != rule:
            failures.append(f"{key}={value!r}, expected {rule!r}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", choices=sorted(PROBES))
    parser.add_argument("--check", action="store_true", help="Compare with expectations.json")
    parser.add_argument("--format", choices=["markdown", "json"], default="json")
    args = parser.parse_args(argv)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("ffmpeg_probes: ffmpeg and ffprobe must be on PATH", file=sys.stderr)
        return 2
    expectations = json.loads((HERE / "expectations.json").read_text(encoding="utf-8"))
    results = {"ffmpeg": version(), "probes": {}}
    failures = {}
    for name in args.only or sorted(PROBES):
        with tempfile.TemporaryDirectory(prefix=f"probe-{name}-") as directory:
            observed = PROBES[name](Path(directory))
        results["probes"][name] = observed
        problems = compare(observed, expectations[name]["expect"])
        if problems:
            failures[name] = problems
    results["failures"] = failures
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(f"# FFmpeg probes\n\n{results['ffmpeg']}\n")
        for name, observed in results["probes"].items():
            status = "differs: " + "; ".join(failures[name]) if name in failures else "as recorded"
            print(f"- **{name}** {expectations[name]['title']} — {status}")
            print(f"  `{json.dumps(observed, ensure_ascii=False)}`")
    return 1 if args.check and failures else 0


if __name__ == "__main__":
    sys.exit(main())
