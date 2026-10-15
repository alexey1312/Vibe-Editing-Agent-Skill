#!/usr/bin/env python3
"""Build captions from word timestamps, and check an SRT file before it ships.

`build` groups words (already on the output timeline, see `edl.py retime`)
into cues of at most two lines, breaking at pauses and punctuation.
`check` reports cues that are too long, too fast, too short, overlapping,
past the end of the video, or that misspell a glossary term
(`CAP001`…`CAP011`, see CHECKS.md). Neither command touches media.

    python3 scripts/captions.py build --words edit/words.out.json -o exports/final.srt
    python3 scripts/captions.py check exports/final.srt --video exports/final.mp4 --glossary edit/glossary.txt

Defaults follow references/captions.md and its sources;
change them per platform and language with the options.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from itertools import combinations
from pathlib import Path

VERSION = "1.0.0"
# Netflix Timed Text Style Guides (Russian; General Requirements; Subtitle Timing), see references/captions.md.
DEFAULTS = {
    "max_lines": 2,
    "max_chars": 42,       # characters per line
    "max_cps": 17.0,       # reading speed, characters per second (adult programmes)
    "max_wpm": None,       # words per minute; BBC recommends 160-180
    "min_duration": 0.833,  # seconds (5/6 s, 20 frames at 24 fps)
    "max_duration": 7.0,    # seconds
    "min_gap": 0.083,       # seconds between cues (2 frames at 24 fps; 0.067 at 30 fps)
    "pause": 0.5,           # a pause this long ends a cue when building
}
# BBC Subtitle Guidelines: about 25 characters in 90 % of a 9:16 frame, up to three lines.
LAYOUTS = {
    "landscape": {"max_chars": 42, "max_lines": 2},
    "vertical": {"max_chars": 25, "max_lines": 3},
}
SENTENCE_END = re.compile(r"[.!?…]+[\"»”)]*$")
CLAUSE_END = re.compile(r"[,;:—–]+[\"»”)]*$")
# Words that should not end a line: they bind to the word after them.
WEAK_ENDINGS = {
    "a", "an", "the", "to", "of", "in", "on", "at", "for", "and", "or", "but", "with", "by", "from", "as",
    "в", "во", "на", "с", "со", "к", "ко", "у", "о", "об", "от", "до", "по", "из", "за", "и", "а", "но",
    "или", "не", "ни", "что", "как", "для", "при", "без", "под", "над",
}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


# --- SRT ----------------------------------------------------------------------------------------

SRT_TIME = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})")


def parse_srt(text: str) -> tuple[list[dict], list[str]]:
    cues, errors = [], []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").lstrip("﻿").strip())
    for number, block in enumerate(blocks, start=1):
        lines = block.strip().split("\n")
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            if block.strip():
                errors.append(f"block {number}: no timing line")
            continue
        start_text, _, end_text = lines[timing].partition("-->")
        start, end = SRT_TIME.search(start_text), SRT_TIME.search(end_text)
        if not start or not end:
            errors.append(f"block {number}: unreadable timing {lines[timing]!r}")
            continue

        def seconds(match):
            h, m, s, ms = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000

        cues.append({"index": len(cues) + 1, "start": seconds(start), "end": seconds(end),
                     "lines": [line for line in lines[timing + 1:]]})
    return cues, errors


def srt_time(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(cues: list[dict]) -> str:
    return "\n\n".join(f"{n}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n" + "\n".join(c["lines"])
                       for n, c in enumerate(cues, start=1)) + "\n"


def visible(text: str) -> str:
    return re.sub(r"<[^>]+>|\{\\[^}]*\}", "", text)


def fmt(seconds: float) -> str:
    minutes, secs = divmod(max(seconds, 0), 60)
    return f"{int(minutes):02d}:{secs:06.3f}"


# --- build --------------------------------------------------------------------------------------

def load_words(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("words") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError(f"{path}: expected a list of words or {{\"words\": [...]}}")
    words = []
    for item in items:
        text = str(item.get("word", item.get("text", ""))).strip()
        if text and item.get("start") is not None and item.get("end") is not None:
            word = {"word": text, "start": float(item["start"]), "end": float(item["end"])}
            if item.get("clip") is not None:
                word["clip"] = item["clip"]  # set by edl.py retime: a cue never spans a cut
            words.append(word)
    return sorted(words, key=lambda w: w["start"])


def bare(word: str) -> str:
    return word.lower().strip("\"«»“”()")


def split_lines(words: list[str], max_chars: int, max_lines: int) -> list[str]:
    """Fewest lines that fit; among those, break after punctuation, keep weak words with their phrase,
    prefer a bottom-heavy shape, and never leave one or two short words alone on top."""
    text = " ".join(words)
    if len(text) <= max_chars or max_lines == 1 or len(words) < 2:
        return [text]
    for count in range(2, max_lines + 1):
        best = None
        for cuts in combinations(range(1, len(words)), count - 1):
            bounds = (0, *cuts, len(words))
            groups = [words[a:b] for a, b in zip(bounds, bounds[1:])]
            lines = [" ".join(group) for group in groups]
            if any(len(line) > max_chars for line in lines):
                continue
            score = max(map(len, lines)) - min(map(len, lines))
            for group in groups[:-1]:
                if CLAUSE_END.search(group[-1]) or SENTENCE_END.search(group[-1]):
                    score -= 20
                if bare(group[-1]) in WEAK_ENDINGS:
                    score += 30
            score += sum(2 for a, b in zip(lines, lines[1:]) if len(a) > len(b))
            if len(groups[0]) <= 2 and len(lines[0]) <= 8:
                score += 25
            if best is None or score < best[0]:
                best = (score, lines)
        if best:
            return best[1]
    return [text]


def build(words: list[dict], options: dict) -> list[dict]:
    capacity = options["max_chars"] * options["max_lines"]
    cues: list[dict] = []
    current: list[dict] = []

    def emit(group: list[dict]) -> None:
        if group:
            cues.append({"start": group[0]["start"], "end": group[-1]["end"],
                         "lines": split_lines([w["word"] for w in group], options["max_chars"], options["max_lines"])})

    def fits(group: list[dict]) -> bool:
        text = " ".join(w["word"] for w in group)
        lines = split_lines([w["word"] for w in group], options["max_chars"], options["max_lines"])
        return (len(text) <= capacity and len(lines) <= options["max_lines"]
                and all(len(line) <= options["max_chars"] for line in lines)
                and group[-1]["end"] - group[0]["start"] <= options["max_duration"])

    for word in words:
        if current:
            pause = word["start"] - current[-1]["end"]
            sentence_done = SENTENCE_END.search(current[-1]["word"]) and len(" ".join(w["word"] for w in current)) >= 12
            across_cut = word.get("clip") != current[-1].get("clip")
            if pause >= options["pause"] or sentence_done or across_cut:
                emit(current)
                current = []
            elif not fits(current + [word]):
                # Close at the last clause boundary, or at least not after a preposition or conjunction.
                cut = next((i for i in range(len(current) - 1, 0, -1)
                            if CLAUSE_END.search(current[i]["word"]) or SENTENCE_END.search(current[i]["word"])), None)
                if cut is None and len(current) > 1 and bare(current[-1]["word"]) in WEAK_ENDINGS:
                    cut = len(current) - 2
                if cut is not None and fits(current[cut + 1:] + [word]):
                    emit(current[:cut + 1])
                    current = current[cut + 1:]
                else:
                    emit(current)
                    current = []
        current.append(word)
    emit(current)
    # Spacing: keep a gap between cues, then stretch short cues into the free time.
    for a, b in zip(cues, cues[1:]):
        if b["start"] - a["end"] < options["min_gap"]:
            a["end"] = max(a["start"] + 0.01, b["start"] - options["min_gap"])
    for i, cue in enumerate(cues):
        if i + 1 < len(cues):
            limit = cues[i + 1]["start"] - options["min_gap"]
        else:
            limit = options.get("duration") or cue["end"] + options["min_duration"]
        limit = min(limit, cue["start"] + options["max_duration"])
        characters = len(" ".join(cue["lines"]))
        wanted = max(cue["start"] + options["min_duration"], cue["start"] + characters / options["max_cps"])
        if wanted > cue["end"]:
            cue["end"] = max(cue["end"], min(wanted, limit))
    return cues


# --- check --------------------------------------------------------------------------------------

def scripts_of(word: str) -> set[str]:
    found = set()
    for char in word:
        if char.isalpha():
            name = unicodedata.name(char, "")
            if name.startswith("CYRILLIC"):
                found.add("Cyrillic")
            elif name.startswith("LATIN"):
                found.add("Latin")
            elif name.startswith("GREEK"):
                found.add("Greek")
    return found


def distance(a: str, b: str) -> int:
    """Edit distance where a swap of two neighbouring letters counts as one edit."""
    if abs(len(a) - len(b)) > 1:
        return 2
    rows = [list(range(len(b) + 1))]
    for i, ca in enumerate(a, start=1):
        row = [i]
        for j, cb in enumerate(b, start=1):
            cost = min(rows[-1][j] + 1, row[j - 1] + 1, rows[-1][j - 1] + (ca != cb))
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cost = min(cost, rows[-2][j - 2] + 1)
            row.append(cost)
        rows.append(row)
    return rows[-1][-1]


def load_glossary(path: str | Path) -> list[str]:
    terms = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            terms.append(line)
    return terms


def video_duration(path: str) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                            capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def finding(rule, severity, cue, message, action):
    item = {"rule": rule, "severity": severity, "message": message, "action": action}
    if cue is not None:
        item.update({"cue": cue["index"], "start": cue["start"], "end": cue["end"],
                     "text": " / ".join(cue["lines"])})
    return item


def check(cues: list[dict], options: dict, duration: float | None = None, glossary: list[str] = ()) -> list[dict]:
    found = []
    word_pattern = re.compile(r"[\w'’-]+", re.UNICODE)
    for i, cue in enumerate(cues):
        lines = [visible(line) for line in cue["lines"]]
        text = " ".join(line.strip() for line in lines)
        length = cue["end"] - cue["start"]
        if not text.strip():
            found.append(finding("CAP010", "medium", cue, "empty cue", "delete it or give it text"))
            continue
        if length <= 0:
            found.append(finding("CAP010", "high", cue, "ends before it starts", "fix the timing"))
            continue
        if len(lines) > options["max_lines"]:
            found.append(finding("CAP001", "medium", cue, f"{len(lines)} lines (max {options['max_lines']})",
                                 "split the cue in two at a phrase boundary"))
        for line in lines:
            if len(line) > options["max_chars"]:
                found.append(finding("CAP002", "medium", cue,
                                     f"line of {len(line)} characters (max {options['max_chars']}): {line!r}",
                                     "shorten the wording or move words to the other line"))
        cps = len(text) / length
        if cps > options["max_cps"] + 0.05:
            found.append(finding("CAP003", "medium", cue,
                                 f"{cps:.1f} characters per second (max {options['max_cps']:g}) over {length:.2f} s",
                                 "lengthen the cue into free time, split it, or condense the text"))
        words_per_minute = len(text.split()) / length * 60
        if options.get("max_wpm") and words_per_minute > options["max_wpm"] + 0.5:
            found.append(finding("CAP003", "medium", cue,
                                 f"{words_per_minute:.0f} words per minute (max {options['max_wpm']:g})",
                                 "lengthen the cue into free time, split it, or condense the text"))
        if length < options["min_duration"]:
            found.append(finding("CAP004", "low", cue, f"on screen {length:.2f} s (min {options['min_duration']:g} s)",
                                 "extend it into the gap after it"))
        if length > options["max_duration"]:
            found.append(finding("CAP004", "low", cue, f"on screen {length:.2f} s (max {options['max_duration']:g} s)",
                                 "split it at a phrase boundary"))
        if i + 1 < len(cues):
            gap = cues[i + 1]["start"] - cue["end"]
            if gap < 0:
                found.append(finding("CAP005", "high", cue, f"overlaps the next cue by {-gap:.3f} s",
                                     "end it before the next one starts"))
            elif 0.0005 < gap < options["min_gap"] - 0.0015:  # SRT keeps milliseconds
                found.append(finding("CAP006", "low", cue, f"gap of {gap * 1000:.0f} ms before the next cue "
                                     f"(min {options['min_gap'] * 1000:.0f} ms) flickers",
                                     "close the gap to zero or open it to the minimum"))
        if duration is not None and cue["end"] > duration + 0.01:
            found.append(finding("CAP007", "high", cue, f"ends at {fmt(cue['end'])}, after the video ({fmt(duration)})",
                                 "retime the captions against the final cut (edl.py retime)"))
        for word in word_pattern.findall(text):
            kinds = scripts_of(word)
            if len(kinds) > 1:
                found.append(finding("CAP009", "high", cue, f"{word!r} mixes {' and '.join(sorted(kinds))} letters",
                                     "retype the word in one alphabet; look-alike letters break search and fonts"))
        if len(lines) > 1:
            last = lines[0].strip().split(" ")[-1].lower().strip("\"«»“”()")
            if last in WEAK_ENDINGS:
                found.append(finding("CAP011", "low", cue, f"line 1 ends with {last!r}",
                                     "move it to the next line, with the phrase it starts"))
        for term in glossary:
            if " " in term:
                if term.lower() in text.lower() and term not in text:
                    found.append(finding("CAP008", "medium", cue, f"glossary term written differently: expected {term!r}",
                                         "use the glossary spelling"))
                continue
            for word in word_pattern.findall(text):
                if word == term:
                    continue
                if word.lower() == term.lower() or (len(term) >= 5 and distance(word.lower(), term.lower()) == 1):
                    found.append(finding("CAP008", "medium", cue, f"{word!r} looks like the glossary term {term!r}",
                                         "check the recording and use the glossary spelling"))
    if duration is not None and cues and cues[0]["start"] > duration:
        found.append(finding("CAP007", "high", None, "every cue starts after the video ends",
                             "the file is on the source timeline; retime it with edl.py retime"))
    found.sort(key=lambda f: (f.get("start", 0), SEVERITY_ORDER[f["severity"]], f["rule"]))
    return found


def options_from(args) -> dict:
    options = dict(DEFAULTS)
    options.update(LAYOUTS[getattr(args, "layout", None) or "landscape"])
    for key in DEFAULTS:
        value = getattr(args, key, None)
        if value is not None:
            options[key] = value
    return options


def add_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--layout", choices=sorted(LAYOUTS), default="landscape",
                        help="landscape: 42 characters × 2 lines; vertical: 25 × 3 (then --max-* override)")
    parser.add_argument("--max-wpm", dest="max_wpm", type=float, help="Words per minute (BBC: 160-180)")
    parser.add_argument("--max-lines", dest="max_lines", type=int)
    parser.add_argument("--max-chars", dest="max_chars", type=int, help="Characters per line")
    parser.add_argument("--max-cps", dest="max_cps", type=float, help="Characters per second")
    parser.add_argument("--min-duration", dest="min_duration", type=float)
    parser.add_argument("--max-duration", dest="max_duration", type=float)
    parser.add_argument("--min-gap", dest="min_gap", type=float)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="Group words into an SRT file")
    p.add_argument("--words", required=True, help="JSON words on the output timeline")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--pause", type=float, help="A pause this long ends a cue")
    p.add_argument("--duration", type=float, help="Video duration: the last cue never runs past it")
    p.add_argument("--force", action="store_true")
    add_options(p)
    p = sub.add_parser("check", help="Lint an SRT file")
    p.add_argument("srt")
    p.add_argument("--video", help="The final video, to compare durations")
    p.add_argument("--duration", type=float, help="Video duration in seconds, instead of --video")
    p.add_argument("--glossary", help="One term per line: names, brands, numbers as they must appear")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    add_options(p)
    args = parser.parse_args(argv)
    options = options_from(args)

    if args.command == "build":
        output = Path(args.output)
        if output.exists() and not args.force:
            print(f"captions: {output} exists; pass --force to overwrite it", file=sys.stderr)
            return 2
        options["duration"] = args.duration
        cues = build(load_words(args.words), options)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(write_srt(cues), encoding="utf-8")
        print(f"wrote {len(cues)} cues → {output}")
        return 0

    cues, errors = parse_srt(Path(args.srt).read_text(encoding="utf-8"))
    duration = args.duration if args.duration is not None else (video_duration(args.video) if args.video else None)
    glossary = load_glossary(args.glossary) if args.glossary else []
    found = [{"rule": "CAP010", "severity": "high", "message": e, "action": "fix the SRT syntax"} for e in errors]
    found += check(cues, options, duration, glossary)
    if args.format == "json":
        print(json.dumps({"tool": "captions", "version": VERSION, "cues": len(cues), "options": options,
                          "duration": duration, "findings": found}, indent=2, ensure_ascii=False))
    else:
        print(f"# Caption check (captions {VERSION})\n")
        print(f"{len(cues)} cues · limits: {options['max_lines']} lines × {options['max_chars']} characters, "
              f"{options['max_cps']:g} characters/s, {options['min_duration']:g}–{options['max_duration']:g} s on screen"
              + (f" · video {fmt(duration)}" if duration else "") + "\n")
        if not found:
            print("No findings.")
        for item in found:
            where = f"cue {item['cue']} {fmt(item['start'])} " if "cue" in item else ""
            print(f"- **{item['rule']}** ({item['severity']}) {where}— {item['message']}. Action: {item['action']}.")
    return 1 if any(f["severity"] == "high" for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
