#!/usr/bin/env python3
"""Work with an edit decision list (EDL): check it, map times, retime transcripts, render.

The EDL is a JSON file (references/edl-format.md): which interval of which source
goes into the cut, in what order, and why. Every other step reads it, so source
time and output time never get mixed up.

    python3 scripts/edl.py check edit/edl.json --probe
    python3 scripts/edl.py table edit/edl.json
    python3 scripts/edl.py cuts edit/edl.json
    python3 scripts/edl.py map edit/edl.json --source take_02 12.5 40.0
    python3 scripts/edl.py retime edit/edl.json --words take_02=transcripts/take_02.json -o edit/words.out.json
    python3 scripts/edl.py retime edit/edl.json --srt take_02=transcripts/take_02.srt -o edit/out.srt
    python3 scripts/edl.py candidates --words transcripts/take_02.json
    python3 scripts/edl.py render edit/edl.json -o renders/draft_v1.mp4 --dry-run
    python3 scripts/edl.py hyperframes edit/edl.json
    python3 scripts/edl.py remotion edit/edl.json --base public

Only `render` writes media, and only to the `-o` path:
it refuses to overwrite a file unless `--force` is given, and never writes over a source.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

VERSION = "1.0.0"
DEFAULT_FADE_MS = 10
TIME = re.compile(r"^(?:(\d+):)?(?:(\d+):)?(\d+(?:\.\d+)?)$")
SMPTE = re.compile(r"^(\d+):(\d\d):(\d\d)[:;](\d\d)$")


class EDLError(ValueError):
    pass


def parse_time(value, fps: float) -> float:
    """Seconds from a number, "SS.sss", "MM:SS.sss", "HH:MM:SS.sss", "HH:MM:SS:FF" or "<n>f"."""
    if isinstance(value, bool):
        raise EDLError(f"not a time: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.endswith("f") and text[:-1].isdigit():
        return int(text[:-1]) / fps
    match = SMPTE.match(text)
    if match:
        hours, minutes, secs, frames = (int(part) for part in match.groups())
        return hours * 3600 + minutes * 60 + secs + frames / fps
    match = TIME.match(text)
    if not match:
        raise EDLError(f"not a time: {value!r}")
    first, second, rest = match.groups()
    parts = [p for p in (first, second) if p is not None]
    total = float(rest)
    for multiplier, part in zip((60, 3600), reversed(parts)):
        total += int(part) * multiplier
    return total


def fmt(seconds: float) -> str:
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours >= 1:
        return f"{sign}{int(hours)}:{int(minutes):02d}:{secs:06.3f}"
    return f"{sign}{int(minutes):02d}:{secs:06.3f}"


@dataclass
class Clip:
    index: int
    id: str
    source: str
    in_frame: int
    out_frame: int
    role: str
    reason: str
    out_start_frame: int = 0

    @property
    def frames(self) -> int:
        return self.out_frame - self.in_frame


@dataclass
class EDL:
    path: Path
    fps: float
    sources: dict[str, Path]
    clips: list[Clip]
    width: int | None
    height: int | None
    sample_rate: int
    fade_ms: float
    warnings: list[str]

    def t(self, frame: int) -> float:
        return frame / self.fps

    @property
    def total_frames(self) -> int:
        return sum(clip.frames for clip in self.clips)


def load(path: str | Path) -> EDL:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise EDLError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise EDLError(f"{path}: the EDL must be a JSON object")
    fps = data.get("fps")
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
        raise EDLError("`fps` must be a positive number (the delivery frame rate)")
    sources = data.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise EDLError("`sources` must map source ids to file paths")
    base = path.parent
    resolved = {str(key): (base / str(value)) for key, value in sources.items()}
    raw_clips = data.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        raise EDLError("`clips` must be a non-empty list")
    clips: list[Clip] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    position = 0
    for index, raw in enumerate(raw_clips, start=1):
        if not isinstance(raw, dict):
            raise EDLError(f"clip {index}: must be an object")
        clip_id = str(raw.get("id") or f"c{index:02d}")
        if clip_id in seen_ids:
            raise EDLError(f"clip {index}: duplicate id {clip_id!r}")
        seen_ids.add(clip_id)
        source = raw.get("source")
        if source not in resolved:
            raise EDLError(f"clip {clip_id}: unknown source {source!r}")
        if "in" not in raw or "out" not in raw:
            raise EDLError(f"clip {clip_id}: needs `in` and `out`")
        start = parse_time(raw["in"], fps)
        end = parse_time(raw["out"], fps)
        in_frame, out_frame = round(start * fps), round(end * fps)
        for label, value, frame in (("in", start, in_frame), ("out", end, out_frame)):
            if abs(value * fps - frame) > 0.01:
                warnings.append(f"clip {clip_id}: `{label}` {fmt(value)} is not on a frame; "
                                f"snapped to {fmt(frame / fps)} (frame {frame})")
        if start < 0:
            raise EDLError(f"clip {clip_id}: `in` is negative")
        if out_frame <= in_frame:
            raise EDLError(f"clip {clip_id}: `out` must be at least one frame after `in`")
        if not str(raw.get("reason") or "").strip():
            warnings.append(f"clip {clip_id}: no `reason` — say why the interval is in the cut")
        clip = Clip(index, clip_id, str(source), in_frame, out_frame,
                    str(raw.get("role") or ""), str(raw.get("reason") or ""), position)
        if clip.frames < round(fps * 0.5):
            warnings.append(f"clip {clip_id}: only {clip.frames} frames long — check that it is intended")
        position += clip.frames
        clips.append(clip)
    fade = data.get("audio_fade_ms", DEFAULT_FADE_MS)
    if not isinstance(fade, (int, float)) or fade < 0:
        raise EDLError("`audio_fade_ms` must be zero or a positive number")
    for clip in clips:
        if fade and clip.frames / fps < 2 * fade / 1000:
            raise EDLError(f"clip {clip.id}: shorter than two audio fades of {fade} ms")
    return EDL(path, float(fps), resolved, clips, data.get("width"), data.get("height"),
               int(data.get("sample_rate") or 48000), float(fade), warnings)


def probe_durations(edl: EDL) -> dict[str, dict]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise EDLError("ffprobe not found on PATH")
    info: dict[str, dict] = {}
    for key, path in edl.sources.items():
        if not path.is_file():
            info[key] = {"error": f"missing file {path}"}
            continue
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                                 "format=duration:stream=codec_type,avg_frame_rate,r_frame_rate",
                                 "-of", "json", str(path)], capture_output=True, text=True)
        if result.returncode != 0:
            info[key] = {"error": result.stderr.strip()}
            continue
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        rate = None
        if video:
            num, _, den = (video.get("avg_frame_rate") or "0/1").partition("/")
            rate = float(num) / float(den) if den and float(den) else None
        info[key] = {
            "duration": float(data.get("format", {}).get("duration") or 0),
            "has_video": video is not None,
            "has_audio": any(s.get("codec_type") == "audio" for s in streams),
            "frame_rate": rate,
        }
    return info


def check(edl: EDL, probe: bool) -> list[str]:
    problems: list[str] = []
    if probe:
        info = probe_durations(edl)
        for key, item in info.items():
            if "error" in item:
                problems.append(f"source {key}: {item['error']}")
                continue
            if item["frame_rate"] and abs(item["frame_rate"] - edl.fps) / edl.fps > 0.001:
                edl.warnings.append(f"source {key}: {item['frame_rate']:.3f} fps differs from the EDL's "
                                    f"{edl.fps:g} fps; make a working copy at {edl.fps:g} fps for frame-exact cuts")
            if not item["has_audio"]:
                edl.warnings.append(f"source {key}: no audio stream; the render inserts silence for it")
        for clip in edl.clips:
            item = info.get(clip.source, {})
            duration = item.get("duration")
            if duration is not None and edl.t(clip.out_frame) > duration + 0.5 / edl.fps:
                problems.append(f"clip {clip.id}: `out` {fmt(edl.t(clip.out_frame))} is past the end of "
                                f"{clip.source} ({fmt(duration)})")
    by_source: dict[str, list[Clip]] = {}
    for clip in edl.clips:
        by_source.setdefault(clip.source, []).append(clip)
    for source, clips in by_source.items():
        ordered = sorted(clips, key=lambda c: c.in_frame)
        for a, b in zip(ordered, ordered[1:]):
            if b.in_frame < a.out_frame:
                edl.warnings.append(f"clips {a.id} and {b.id} reuse {fmt(edl.t(b.in_frame))}–"
                                    f"{fmt(edl.t(min(a.out_frame, b.out_frame)))} of {source}; "
                                    "fine for a repeat, wrong for a cut")
        if [c.index for c in clips] != [c.index for c in ordered]:
            edl.warnings.append(f"source {source} is used out of its recorded order "
                                "(a reordering: check that each moved thought still makes sense alone)")
    return problems


def table(edl: EDL) -> list[dict]:
    rows = []
    for clip in edl.clips:
        rows.append({
            "id": clip.id, "source": clip.source,
            "source_in": edl.t(clip.in_frame), "source_out": edl.t(clip.out_frame),
            "output_in": edl.t(clip.out_start_frame), "output_out": edl.t(clip.out_start_frame + clip.frames),
            "duration": clip.frames / edl.fps, "role": clip.role, "reason": clip.reason,
        })
    return rows


def removed_intervals(edl: EDL, durations: dict[str, float] | None = None) -> dict[str, list[tuple[float, float]]]:
    """Per source, the parts no clip uses: from 0 (or the first `in`) to the end (or the last `out`)."""
    result: dict[str, list[tuple[float, float]]] = {}
    for source in edl.sources:
        clips = sorted((c for c in edl.clips if c.source == source), key=lambda c: c.in_frame)
        if not clips:
            continue
        start = 0.0 if durations else edl.t(clips[0].in_frame)
        end = (durations or {}).get(source, edl.t(max(c.out_frame for c in clips)))
        gaps = []
        cursor = start
        for clip in clips:
            a, b = edl.t(clip.in_frame), edl.t(clip.out_frame)
            if a > cursor + 1e-9:
                gaps.append((cursor, a))
            cursor = max(cursor, b)
        if end > cursor + 1e-9:
            gaps.append((cursor, end))
        result[source] = gaps
    return result


def map_time(edl: EDL, source: str, time: float) -> list[float]:
    """Output times at which a source instant plays; empty when it was cut."""
    hits = []
    for clip in edl.clips:
        if clip.source == source and edl.t(clip.in_frame) <= time < edl.t(clip.out_frame):
            hits.append(edl.t(clip.out_start_frame) + time - edl.t(clip.in_frame))
    return hits


def map_interval(edl: EDL, source: str, start: float, end: float) -> list[tuple[float, float, Clip]]:
    pieces = []
    for clip in edl.clips:
        if clip.source != source:
            continue
        a, b = edl.t(clip.in_frame), edl.t(clip.out_frame)
        lo, hi = max(a, start), min(b, end)
        if hi > lo:
            offset = edl.t(clip.out_start_frame) - a
            pieces.append((lo + offset, hi + offset, clip))
    return sorted(pieces, key=lambda p: p[0])


# --- transcripts -----------------------------------------------------------------------------

def load_words(path: str | Path) -> list[dict]:
    """Words with start/end in seconds from WhisperX, Whisper-style, ElevenLabs-style or plain lists."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    words: list[dict] = []

    def add(text, start, end, speaker=None):
        if text is None or start is None or end is None:
            return
        text = str(text).strip()
        if text:
            item = {"word": text, "start": float(start), "end": float(end)}
            if speaker is not None:
                item["speaker"] = speaker
            words.append(item)

    if isinstance(data, dict) and isinstance(data.get("words"), list):
        for item in data["words"]:
            if item.get("type", "word") != "word":
                continue  # ElevenLabs marks spacing and audio events separately
            add(item.get("text", item.get("word")), item.get("start"), item.get("end"),
                item.get("speaker_id", item.get("speaker")))
    elif isinstance(data, dict) and isinstance(data.get("segments"), list):
        for segment in data["segments"]:
            for item in segment.get("words") or []:
                add(item.get("word", item.get("text")), item.get("start"), item.get("end"),
                    item.get("speaker", segment.get("speaker")))
    elif isinstance(data, list):
        for item in data:
            add(item.get("word", item.get("text")), item.get("start"), item.get("end"), item.get("speaker"))
    else:
        raise EDLError(f"{path}: no words with start and end times found")
    words.sort(key=lambda w: w["start"])
    return words


def retime_words(edl: EDL, source: str, words: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep each word whose midpoint survives the cut, on the output timeline."""
    kept, dropped = [], []
    for word in words:
        middle = (word["start"] + word["end"]) / 2
        placed = False
        for clip in edl.clips:
            a, b = edl.t(clip.in_frame), edl.t(clip.out_frame)
            if clip.source == source and a <= middle < b:
                offset = edl.t(clip.out_start_frame) - a
                item = dict(word)
                item.update({
                    "start": round(max(word["start"], a) + offset, 3),
                    "end": round(min(word["end"], b) + offset, 3),
                    "source": source, "source_start": word["start"], "source_end": word["end"], "clip": clip.id,
                })
                if word["start"] < a - 0.02 or word["end"] > b + 0.02:
                    item["clipped"] = True
                kept.append(item)
                placed = True
        if not placed:
            dropped.append(dict(word, source=source))
    return kept, dropped


SRT_TIME = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})")


def parse_srt(text: str) -> list[dict]:
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = block.strip().split("\n")
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        start_text, _, end_text = lines[timing].partition("-->")
        start, end = SRT_TIME.search(start_text), SRT_TIME.search(end_text)
        if not start or not end:
            continue

        def seconds(match):
            h, m, s, ms = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000

        cues.append({"start": seconds(start), "end": seconds(end), "text": "\n".join(lines[timing + 1:])})
    return cues


def srt_time(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(cues: list[dict]) -> str:
    blocks = []
    for number, cue in enumerate(cues, start=1):
        blocks.append(f"{number}\n{srt_time(cue['start'])} --> {srt_time(cue['end'])}\n{cue['text']}")
    return "\n\n".join(blocks) + "\n"


def retime_cues(edl: EDL, source: str, cues: list[dict]) -> tuple[list[dict], list[str]]:
    out, notes = [], []
    for number, cue in enumerate(cues, start=1):
        pieces = map_interval(edl, source, cue["start"], cue["end"])
        if not pieces:
            notes.append(f"cue {number} ({fmt(cue['start'])}) falls inside a cut and was dropped")
            continue
        covered = sum(hi - lo for lo, hi, _ in pieces)
        if len(pieces) > 1 or covered < (cue["end"] - cue["start"]) - 0.05:
            notes.append(f"cue {number} ({fmt(cue['start'])}) crosses a cut: its text may name removed words; "
                         "rebuild it from word timestamps")
        for lo, hi, _ in pieces:
            out.append({"start": lo, "end": hi, "text": cue["text"], "source": source})
    out.sort(key=lambda c: c["start"])
    return out, notes


# --- cut candidates ----------------------------------------------------------------------------

FILLERS = {
    "en": {"um", "uh", "erm", "hmm", "like", "basically", "actually"},
    "ru": {"э", "ээ", "эээ", "м", "мм", "ну", "вот", "типа", "короче", "значит"},
}


def normalise(word: str) -> str:
    return re.sub(r"[^\w-]", "", word.lower())


def candidates(words: list[dict], min_gap: float, language: str | None, window: int = 12) -> list[dict]:
    """Pauses, repeated phrases and filler words as *candidates* for the plan — never as cuts."""
    found = []
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap >= min_gap:
            found.append({"kind": "pause", "start": a["end"], "end": b["start"], "duration": round(gap, 3),
                          "context": f"…{a['word']} ‖ {b['word']}…"})
    tokens = [normalise(w["word"]) for w in words]
    index = 0
    while index < len(tokens):
        hit = None
        for size in range(6, 1, -1):
            phrase = tokens[index:index + size]
            if len(phrase) < size or not all(phrase):
                continue
            for later in range(index + size, min(index + size + window, len(tokens) - size + 1)):
                if tokens[later:later + size] == phrase:
                    hit = (size, later)
                    break
            if hit:
                break
        if hit:
            size, later = hit
            found.append({"kind": "repeat", "start": words[index]["start"], "end": words[later]["start"],
                          "duration": round(words[later]["start"] - words[index]["start"], 3),
                          "context": " ".join(w["word"] for w in words[index:later + size]),
                          "note": "an earlier attempt of the same phrase; usually keep the later, complete one"})
            index = later
            continue
        index += 1
    filler_set = set().union(*FILLERS.values()) if language is None else FILLERS.get(language, set())
    for word in words:
        if normalise(word["word"]) in filler_set:
            found.append({"kind": "filler", "start": word["start"], "end": word["end"],
                          "duration": round(word["end"] - word["start"], 3), "context": word["word"],
                          "note": "listen first: some of these words carry meaning"})
    found.sort(key=lambda c: c["start"])
    return found


# --- render -------------------------------------------------------------------------------------

def render_command(edl: EDL, output: Path, crf: int, preset: str, has_audio: dict[str, bool] | None = None,
                   size: tuple[int, int] | None = None) -> list[str]:
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    order = list(dict.fromkeys(clip.source for clip in edl.clips))
    inputs: list[str] = []
    for source in order:
        inputs += ["-i", str(edl.sources[source])]
    width, height = size or (edl.width, edl.height)
    fade = edl.fade_ms / 1000
    filters, labels = [], []
    for k, clip in enumerate(edl.clips):
        i = order.index(clip.source)
        # Half-frame bounds pick exactly the frames [in, out) even when timestamps jitter.
        v_start, v_end = (clip.in_frame - 0.5) / edl.fps, (clip.out_frame - 0.5) / edl.fps
        a_start, a_end = edl.t(clip.in_frame), edl.t(clip.out_frame)
        duration = a_end - a_start
        chain = f"[{i}:v:0]trim=start={v_start:.6f}:end={v_end:.6f},setpts=PTS-STARTPTS,fps={edl.fps:g}"
        if width and height:
            chain += (f",scale={width}:{height}:force_original_aspect_ratio=decrease,"
                      f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
        chain += f",setsar=1,format=yuv420p[v{k}]"
        filters.append(chain)
        if has_audio is None or has_audio.get(clip.source, True):
            audio = (f"[{i}:a:0]atrim=start={a_start:.6f}:end={a_end:.6f},asetpts=PTS-STARTPTS,"
                     f"aresample={edl.sample_rate},aformat=sample_fmts=fltp:channel_layouts=stereo")
        else:
            audio = (f"anullsrc=r={edl.sample_rate}:cl=stereo,atrim=duration={duration:.6f},"
                     "aformat=sample_fmts=fltp")
        if fade > 0:
            audio += f",afade=t=in:d={fade:.4f},afade=t=out:st={max(duration - fade, 0):.6f}:d={fade:.4f}"
        filters.append(audio + f"[a{k}]")
        labels.append(f"[v{k}][a{k}]")
    filters.append("".join(labels) + f"concat=n={len(edl.clips)}:v=1:a=1[v][a]")
    return [ffmpeg, "-hide_banner", "-nostdin", *inputs, "-filter_complex", ";\n".join(filters),
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]


# --- engine snippets ---------------------------------------------------------------------------

def relative_src(edl: EDL, source: str, base: Path | None) -> str:
    path = edl.sources[source]
    try:
        return str(path.resolve().relative_to((base or edl.path.parent).resolve()))
    except ValueError:
        return str(path)


def hyperframes_snippet(edl: EDL, base: Path | None = None, separate_audio: bool = False) -> str:
    """One <video> per clip: data-start/data-duration on the output timeline, data-media-start in the source.

    The default keeps the sound on the <video> (data-has-audio), as current HyperFrames does;
    `separate_audio` writes the older form: a muted <video> plus an <audio> with the same timing.
    """
    lines = ["<!-- generated by edl.py from the approved EDL; seconds; check with `npx hyperframes check` -->"]
    for clip in edl.clips:
        src = relative_src(edl, clip.source, base)
        timing = (f'data-start="{edl.t(clip.out_start_frame):.3f}" data-duration="{clip.frames / edl.fps:.3f}" '
                  f'data-media-start="{edl.t(clip.in_frame):.3f}"')
        if separate_audio:
            lines.append(f'<video id="{clip.id}" src="{src}" {timing} data-track-index="0" muted playsinline></video>')
            lines.append(f'<audio id="{clip.id}-audio" src="{src}" {timing} data-track-index="10"></audio>')
        else:
            lines.append(f'<video id="{clip.id}" src="{src}" {timing} data-track-index="0" playsinline '
                         'data-has-audio="true"></video>')
    return "\n".join(lines) + "\n"


def remotion_snippet(edl: EDL, base: Path | None = None) -> str:
    """<Sequence> per clip with <Video trimBefore durationInFrames>, in frames at the EDL's fps."""
    lines = ["// generated by edl.py from the approved EDL; frames at "
             f"{edl.fps:g} fps; the composition must use the same fps",
             "// <Video> from @remotion/media; put the sources under public/ for staticFile()",
             "<>"]
    for clip in edl.clips:
        src = relative_src(edl, clip.source, base)
        lines.append(f'  <Sequence name="{clip.id}" from={{{clip.out_start_frame}}} durationInFrames={{{clip.frames}}}>')
        lines.append(f'    <Video src={{staticFile("{src}")}} trimBefore={{{clip.in_frame}}} '
                     f'durationInFrames={{{clip.frames}}} />')
        lines.append("  </Sequence>")
    lines.append("</>")
    return "\n".join(lines) + "\n"


# --- command line -------------------------------------------------------------------------------

def pair(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep or not key or not value:
        raise argparse.ArgumentTypeError("use SOURCE_ID=PATH")
    return key, value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="Validate the EDL; with --probe, also against the source files")
    p.add_argument("edl")
    p.add_argument("--probe", action="store_true")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p = sub.add_parser("table", help="Source and output time of every clip")
    p.add_argument("edl")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p = sub.add_parser("cuts", help="The intervals of each source that the cut leaves out")
    p.add_argument("edl")
    p.add_argument("--probe", action="store_true", help="Count from 0 to each source's end")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p = sub.add_parser("map", help="Where source instants land in the output")
    p.add_argument("edl")
    p.add_argument("--source", required=True)
    p.add_argument("times", nargs="+")

    p = sub.add_parser("retime", help="Move word timestamps or SRT cues onto the output timeline")
    p.add_argument("edl")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--words", type=pair, action="append", metavar="SOURCE=PATH")
    group.add_argument("--srt", type=pair, action="append", metavar="SOURCE=PATH")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("candidates", help="Pauses, repeats and fillers in a transcript, for the plan")
    p.add_argument("--words", required=True)
    p.add_argument("--min-gap", type=float, default=0.4, help="Shortest pause to list, seconds")
    p.add_argument("--language", choices=sorted(FILLERS), default=None)
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p = sub.add_parser("render", help="Render the cut with ffmpeg, re-encoding every clip")
    p.add_argument("edl")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--preset", default="medium")
    p.add_argument("--size", help="WIDTHxHEIGHT; overrides the EDL (e.g. 640x360 for a fast proxy)")
    p.add_argument("--dry-run", action="store_true", help="Print the command instead of running it")
    p.add_argument("--force", action="store_true", help="Overwrite the output file")

    p = sub.add_parser("hyperframes", help="Print HyperFrames <video> clips for the EDL")
    p.add_argument("edl")
    p.add_argument("--base", help="Directory the composition's src paths are relative to")
    p.add_argument("--separate-audio", action="store_true",
                   help="Older HyperFrames form: muted <video> plus an <audio> per clip")

    p = sub.add_parser("remotion", help="Print Remotion <Sequence> clips for the EDL")
    p.add_argument("edl")
    p.add_argument("--base", help="Directory staticFile() paths are relative to (the project's public/)")

    args = parser.parse_args(argv)
    try:
        return run(args)
    except EDLError as error:
        print(f"edl: {error}", file=sys.stderr)
        return 2


def guard_output(path: Path, force: bool, sources: list[Path] = ()) -> None:
    resolved = path.resolve()
    for source in sources:
        if source.exists() and source.resolve() == resolved:
            raise EDLError(f"refusing to write over a source: {path}")
    if path.exists() and not force:
        raise EDLError(f"{path} exists; pass --force to overwrite it")


def run(args) -> int:
    if args.command == "candidates":
        found = candidates(load_words(args.words), args.min_gap, args.language)
        if args.format == "json":
            print(json.dumps(found, indent=2, ensure_ascii=False))
        else:
            print("| Kind | Source time | Length | Context | Note |\n| --- | --- | --- | --- | --- |")
            for item in found:
                print(f"| {item['kind']} | {fmt(item['start'])}–{fmt(item['end'])} | {item['duration']:.2f} s | "
                      f"{item['context']} | {item.get('note', '')} |")
            print(f"\n{len(found)} candidates. Candidates are not cuts: approve each one in the plan.")
        return 0

    edl = load(args.edl)

    if args.command == "check":
        problems = check(edl, args.probe)
        result = {"tool": "edl", "version": VERSION, "clips": len(edl.clips), "fps": edl.fps,
                  "output_duration": edl.total_frames / edl.fps, "problems": problems, "warnings": edl.warnings}
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"EDL {edl.path}: {len(edl.clips)} clips, {edl.total_frames} frames at {edl.fps:g} fps "
                  f"= {fmt(edl.total_frames / edl.fps)}")
            for item in problems:
                print(f"- problem: {item}")
            for item in edl.warnings:
                print(f"- warning: {item}")
            if not problems and not edl.warnings:
                print("- no problems")
        return 1 if problems else 0

    if args.command == "table":
        rows = table(edl)
        if args.format == "json":
            print(json.dumps(rows, indent=2, ensure_ascii=False))
            return 0
        print("| # | Clip | Source | Source in–out | Output in–out | Length | Role | Reason |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for number, row in enumerate(rows, start=1):
            print(f"| {number} | {row['id']} | {row['source']} | {fmt(row['source_in'])}–{fmt(row['source_out'])} | "
                  f"{fmt(row['output_in'])}–{fmt(row['output_out'])} | {row['duration']:.2f} s | {row['role']} | "
                  f"{row['reason']} |")
        print(f"\nTotal {fmt(edl.total_frames / edl.fps)} ({edl.total_frames} frames at {edl.fps:g} fps).")
        return 0

    if args.command == "cuts":
        durations = None
        if args.probe:
            durations = {k: v["duration"] for k, v in probe_durations(edl).items() if "duration" in v}
        gaps = removed_intervals(edl, durations)
        if args.format == "json":
            print(json.dumps({k: [{"start": a, "end": b, "duration": b - a} for a, b in v] for k, v in gaps.items()},
                             indent=2))
            return 0
        print("| Source | Removed interval | Length |\n| --- | --- | --- |")
        for source, items in gaps.items():
            for a, b in items:
                print(f"| {source} | {fmt(a)}–{fmt(b)} | {b - a:.2f} s |")
        return 0

    if args.command == "map":
        if args.source not in edl.sources:
            raise EDLError(f"unknown source {args.source!r}")
        for raw in args.times:
            time = parse_time(raw, edl.fps)
            hits = map_time(edl, args.source, time)
            target = ", ".join(fmt(h) for h in hits) if hits else "cut"
            print(f"{args.source} {fmt(time)} → {target}")
        return 0

    if args.command == "retime":
        output = Path(args.output)
        guard_output(output, args.force, list(edl.sources.values()))
        if args.words:
            kept_all, dropped_all = [], []
            for source, path in args.words:
                if source not in edl.sources:
                    raise EDLError(f"unknown source {source!r}")
                kept, dropped = retime_words(edl, source, load_words(path))
                kept_all += kept
                dropped_all += dropped
            kept_all.sort(key=lambda w: w["start"])
            output.write_text(json.dumps({"words": kept_all}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            clipped = sum(1 for w in kept_all if w.get("clipped"))
            print(f"kept {len(kept_all)} words, dropped {len(dropped_all)} inside cuts, "
                  f"{clipped} clipped at a join → {output}")
            return 0
        cues_all, notes_all = [], []
        for source, path in args.srt:
            if source not in edl.sources:
                raise EDLError(f"unknown source {source!r}")
            cues, notes = retime_cues(edl, source, parse_srt(Path(path).read_text(encoding="utf-8")))
            cues_all += cues
            notes_all += [f"{source}: {n}" for n in notes]
        cues_all.sort(key=lambda c: c["start"])
        output.write_text(write_srt(cues_all), encoding="utf-8")
        print(f"wrote {len(cues_all)} cues → {output}")
        for note in notes_all:
            print(f"- {note}")
        return 0

    if args.command == "render":
        output = Path(args.output)
        size = None
        if args.size:
            match = re.match(r"^(\d+)x(\d+)$", args.size)
            if not match:
                raise EDLError("--size must look like 1280x720")
            size = (int(match.group(1)), int(match.group(2)))
        problems = check(edl, probe=shutil.which("ffprobe") is not None and not args.dry_run)
        if problems:
            raise EDLError("; ".join(problems))
        has_audio = None
        if not args.dry_run and shutil.which("ffprobe"):
            has_audio = {k: v.get("has_audio", True) for k, v in probe_durations(edl).items()}
        command = render_command(edl, output, args.crf, args.preset, has_audio, size)
        if args.dry_run:
            print(" ".join(shlex.quote(part) for part in command))
            return 0
        guard_output(output, args.force, list(edl.sources.values()))
        output.parent.mkdir(parents=True, exist_ok=True)
        command.insert(1, "-y" if args.force else "-n")
        result = subprocess.run(command)
        return result.returncode

    if args.command == "hyperframes":
        print(hyperframes_snippet(edl, Path(args.base) if args.base else None, args.separate_audio), end="")
        return 0

    if args.command == "remotion":
        print(remotion_snippet(edl, Path(args.base) if args.base else None), end="")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
