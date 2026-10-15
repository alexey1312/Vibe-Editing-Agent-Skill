#!/usr/bin/env python3
"""Report what this machine can do for a video edit, before anything is planned on it.

Read-only: it runs only version and capability queries (see ALLOWED) and reads
environment variable *names*, never their values. It answers: can this machine
probe media, cut frame-accurately, burn captions, measure loudness, convert HDR,
recognise speech locally, and run HyperFrames or Remotion?

    python3 scripts/toolchain_report.py --format markdown
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys

VERSION = "1.0.0"
# The only commands this script may run; tests/test_toolchain_report.py enforces it.
ALLOWED = {
    ("ffmpeg", "-hide_banner", "-version"),
    ("ffmpeg", "-hide_banner", "-filters"),
    ("ffmpeg", "-hide_banner", "-encoders"),
    ("ffprobe", "-hide_banner", "-version"),
    ("node", "--version"),
    ("python3", "--version"),
}
FILTERS = {
    "subtitles": "burn SRT/ASS captions (needs libass)",
    "ass": "burn ASS captions (needs libass)",
    "drawtext": "draw text (needs libfreetype)",
    "ebur128": "measure loudness and true peak",
    "loudnorm": "normalise loudness",
    "silencedetect": "find silences",
    "blackdetect": "find black frames",
    "freezedetect": "find frozen picture",
    "sidechaincompress": "duck music under speech",
    "afade": "fade audio at joins",
    "concat": "join clips",
    "trim": "cut video by time",
    "atrim": "cut audio by time",
    "zscale": "convert colour spaces (needs libzimg)",
    "tonemap": "map HDR to SDR",
    "libplacebo": "GPU colour and HDR processing",
}
ENCODERS = ["libx264", "libx265", "h264_videotoolbox", "hevc_videotoolbox", "aac", "libopus", "prores_ks"]
TOOLS = {
    "whisperx": "local speech recognition with word alignment",
    "whisper-ctranslate2": "local speech recognition",
    "parakeet-mlx": "local speech recognition on Apple silicon",
    "mlx_audio.stt.generate": "local speech recognition on Apple silicon (MLX Audio)",
    "auto-editor": "automatic cuts by loudness or motion",
    "yt-dlp": "download media from a URL (check the rights first)",
    "npx": "run HyperFrames or Remotion CLIs",
}
SECRET_NAMES = [
    "ELEVENLABS_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN", "DEEPGRAM_API_KEY", "ASSEMBLYAI_API_KEY", "DESCRIPT_API_KEY", "HEYGEN_API_KEY",
]
MIN_NODE_FOR_HYPERFRAMES = 22  # references/versions.md


def run(command: list[str]) -> str | None:
    key = (os.path.basename(command[0]), *command[1:])
    if key not in ALLOWED:
        raise PermissionError(f"command not allowed: {key}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (result.stdout or "") + (result.stderr or "")


def first_line(text: str | None) -> str | None:
    return text.strip().splitlines()[0] if text and text.strip() else None


def ffmpeg_report() -> dict:
    path = shutil.which("ffmpeg")
    report: dict = {"ffmpeg": path, "ffprobe": shutil.which("ffprobe"), "filters": {}, "encoders": {}}
    if not path:
        return report
    version = run([path, "-hide_banner", "-version"]) or ""
    report["version"] = first_line(version)
    configuration = re.search(r"configuration:(.*)", version)
    flags = configuration.group(1).split() if configuration else []
    report["gpl"] = "--enable-gpl" in flags
    report["nonfree"] = "--enable-nonfree" in flags
    report["libraries"] = sorted(f[len("--enable-"):] for f in flags if f.startswith("--enable-lib"))
    filters = run([path, "-hide_banner", "-filters"]) or ""
    names = set(re.findall(r"^\s*[.TSC|A-Z]{2,3}\s+(\S+)\s", filters, re.M))
    report["filters"] = {name: name in names for name in FILTERS}
    encoders = run([path, "-hide_banner", "-encoders"]) or ""
    available = set(re.findall(r"^\s*[VAS][.A-Z]{5}\s+(\S+)\s", encoders, re.M))
    report["encoders"] = {name: name in available for name in ENCODERS}
    if report["ffprobe"]:
        report["ffprobe_version"] = first_line(run([report["ffprobe"], "-hide_banner", "-version"]))
    return report


def node_report() -> dict:
    path = shutil.which("node")
    if not path:
        return {"node": None}
    version = first_line(run([path, "--version"]))
    major = None
    if version:
        match = re.match(r"v?(\d+)", version)
        major = int(match.group(1)) if match else None
    return {"node": path, "version": version, "major": major, "npx": shutil.which("npx")}


def report() -> dict:
    ffmpeg = ffmpeg_report()
    node = node_report()
    tools = {name: shutil.which(name) for name in TOOLS}
    secrets = {name: name in os.environ and bool(os.environ.get(name)) for name in SECRET_NAMES}
    apple_silicon = platform.system() == "Darwin" and platform.machine() == "arm64"
    f = ffmpeg.get("filters", {})
    e = ffmpeg.get("encoders", {})
    have_ffmpeg = bool(ffmpeg.get("ffmpeg"))
    capabilities = [
        ("Inventory media (media_probe.py)", bool(ffmpeg.get("ffprobe")), "needs ffprobe"),
        ("Cut and render frame-accurately (edl.py render)",
         have_ffmpeg and f.get("trim") and f.get("atrim") and f.get("concat") and e.get("libx264"),
         "needs ffmpeg with trim, atrim, concat and libx264"),
        ("Fade audio at every join", have_ffmpeg and f.get("afade"), "needs afade"),
        ("Burn captions into the picture with ffmpeg", have_ffmpeg and (f.get("subtitles") or f.get("ass")),
         "no libass in this build: burn captions in the engine (HyperFrames, Remotion), or install a libass "
         "build (Homebrew: ffmpeg-full) — an install needs approval"),
        ("Measure loudness and true peak; find black, frozen and silent intervals (qa_scan.py)",
         have_ffmpeg and f.get("ebur128") and f.get("blackdetect") and f.get("freezedetect") and f.get("silencedetect"),
         "needs ebur128, blackdetect, freezedetect, silencedetect"),
        ("Duck music under speech in ffmpeg", have_ffmpeg and f.get("sidechaincompress"), "needs sidechaincompress"),
        ("Convert HDR to SDR in ffmpeg", have_ffmpeg and ((f.get("zscale") and f.get("tonemap")) or f.get("libplacebo")),
         "needs zscale + tonemap or libplacebo; otherwise convert in an editor or the camera app"),
        ("Recognise speech locally",
         any(tools.get(n) for n in ("whisperx", "whisper-ctranslate2", "parakeet-mlx", "mlx_audio.stt.generate")),
         "no local recogniser on PATH; cloud ASR sends audio out (references/data-and-licences.md)"),
        ("Run HyperFrames", bool(node.get("npx")) and (node.get("major") or 0) >= MIN_NODE_FOR_HYPERFRAMES and have_ffmpeg,
         f"needs Node.js {MIN_NODE_FOR_HYPERFRAMES}+ with npx, and FFmpeg"),
        ("Run Remotion", bool(node.get("npx")), "needs Node.js with npx"),
    ]
    return {
        "tool": "toolchain_report", "version": VERSION,
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "apple_silicon": apple_silicon,
        "python": sys.version.split()[0],
        "ffmpeg": ffmpeg, "node": node, "tools": tools,
        "secrets_present": [name for name, present in secrets.items() if present],
        "capabilities": [{"capability": c, "available": bool(ok), "note": None if ok else note}
                         for c, ok, note in capabilities],
    }


def markdown(result: dict) -> str:
    ffmpeg, node = result["ffmpeg"], result["node"]
    lines = [f"# Toolchain report (toolchain_report {result['version']})", "",
             f"- Platform: {result['platform']}" + (" (Apple silicon)" if result["apple_silicon"] else ""),
             f"- Python: {result['python']}",
             f"- FFmpeg: {ffmpeg.get('version') or 'not found'}"
             + (f" · GPL build: {'yes' if ffmpeg.get('gpl') else 'no'}" if ffmpeg.get("ffmpeg") else ""),
             f"- Node.js: {node.get('version') or 'not found'}" + (" · npx" if node.get("npx") else ""),
             f"- Other tools: {', '.join(n for n, p in result['tools'].items() if p) or 'none'}",
             f"- Keys in the environment (names only): {', '.join(result['secrets_present']) or 'none'}",
             "", "| Capability | Here | If not |", "| --- | --- | --- |"]
    for item in result["capabilities"]:
        lines.append(f"| {item['capability']} | {'yes' if item['available'] else 'no'} | {item['note'] or ''} |")
    missing = [n for n, ok in ffmpeg.get("filters", {}).items() if not ok]
    if missing:
        lines += ["", f"FFmpeg filters missing from this build: {', '.join(missing)}."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args(argv)
    result = report()
    print(json.dumps(result, indent=2) if args.format == "json" else markdown(result), end="" if args.format != "json" else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
