# Checks

Every automated rule in the scripts, and the checks that need a person.
The scripts read media and text; only `edl.py render`, `edl.py retime`, `captions.py build`
and `qa_scan.py --evidence-dir` write, and only to the path they are given.
Findings are leads: the agent looks at the frame or listens before a finding becomes an item.

## `media_probe.py` — sources

| Rule | Severity | Finds | Source | Skill |
| --- | --- | --- | --- | --- |
| `MED001` | high | Variable frame rate: more than 2 % of frame intervals in the first 30 s differ from the median by over 25 % | `measured-behavior.md` M6 | `vibe-editing-cut` |
| `MED002` | medium | Rotation metadata (display matrix or legacy `rotate` tag); reports the displayed size | `measured-behavior.md` M5 | `vibe-editing-cut` |
| `MED003` | info | No audio stream | ffprobe stream list | `vibe-editing-cut` |
| `MED004` | medium | Sources at different frame rates | ffprobe `avg_frame_rate` | `vibe-editing-cut` |
| `MED005` | low | Sources at different sample rates or channel counts | FFmpeg filters › concat (common audio format) | `vibe-editing-cut` |
| `MED006` | info | Keyframes more than 2 s apart: a stream copy cannot cut there cleanly | FFmpeg › `-ss`; `measured-behavior.md` M2 | `vibe-editing-cut` |
| `MED007` | low | File name with spaces, brackets, quotes or non-ASCII characters | *inference*: shell quoting and tool paths | `vibe-editing-cut` |
| `MED008` | medium | Video and audio streams differ in length by more than 0.1 s | ffprobe stream durations | both |
| `MED009` | medium | Interlaced picture (`field_order` not progressive) | ffprobe `field_order` | `vibe-editing-cut` |
| `MED010` | medium | HDR transfer (PQ or HLG) or Dolby Vision side data | ffprobe `color_transfer`, side data | `vibe-editing-cut` |
| `MED011` | high | No stream ffprobe can read | ffprobe | both |

## `captions.py check` — captions

| Rule | Severity | Finds | Source | Skill |
| --- | --- | --- | --- | --- |
| `CAP001` | medium | More lines than the limit (2; 3 with `--layout vertical`) | Netflix General Requirements; BBC Subtitle Guidelines | both |
| `CAP002` | medium | A line longer than the limit (42; 25 with `--layout vertical`) | Netflix Russian guide; BBC Subtitle Guidelines | both |
| `CAP003` | medium | Reading speed over 17 characters per second, or over `--max-wpm` | Netflix Russian guide; BBC Subtitle Guidelines | both |
| `CAP004` | low | On screen under 5/6 s or over 7 s | Netflix General Requirements | both |
| `CAP005` | high | Overlaps the next cue | SRT timing | both |
| `CAP006` | low | Gap to the next cue under 2 frames (0.083 s by default) | Netflix Subtitle Timing Guidelines | both |
| `CAP007` | high | Ends after the video ends — often captions left on source time | `measured-behavior.md` M1 (the retime the fix uses) | both |
| `CAP008` | medium | A word one edit (or one swap of neighbours) away from a glossary term, or a term in the wrong case | *inference*: recognisers misspell names | both |
| `CAP009` | high | A word mixing Cyrillic, Latin or Greek letters | Unicode character names | both |
| `CAP010` | high/medium | Empty, inverted or unreadable cue | SRT syntax | both |
| `CAP011` | low | Line 1 ends with a preposition or conjunction | Netflix General Requirements (break before conjunctions and prepositions) | both |

## `qa_scan.py` — the rendered file

| Rule | Severity | Finds | Source | Skill |
| --- | --- | --- | --- | --- |
| `QA001` | high | Size, frame rate or duration differs from the brief | the brief | `vibe-editing-review` |
| `QA002` | high at the start, else medium | Black picture of 0.1 s or more (`blackdetect`, `pix_th` 0.10) | FFmpeg filters › blackdetect | `vibe-editing-review` |
| `QA003` | low | Picture unchanged for 2 s or more (`freezedetect`, −60 dB) | FFmpeg filters › freezedetect | `vibe-editing-review` |
| `QA004` | medium | Silence of 1.5 s or more under −50 dB, except a short tail | FFmpeg filters › silencedetect | `vibe-editing-review` |
| `QA005` | medium | Integrated loudness off the brief's target by more than 1 LU | FFmpeg filters › ebur128; EBU R 128 | `vibe-editing-review` |
| `QA006` | medium | True peak above the ceiling (−1 dBTP by default) | EBU R 128; Apple Podcasts; Spotify | `vibe-editing-review` |
| `QA007` | low | The MP4 index (`moov`) after the media data: no progressive playback | ISO base media box order; FFmpeg `-movflags +faststart` | `vibe-editing-review` |
| `QA008` | as the `CAP` rule | A caption rule, checked against the file's real duration | `captions.py` | `vibe-editing-review` |
| `QA009` | high | The file's length differs from the approved EDL by more than 1.5 frames | `edl.py`; `measured-behavior.md` M1 | `vibe-editing-review` |
| `QA010` | medium | Video and audio streams differ in length (`MED008`) | ffprobe | `vibe-editing-review` |
| `QA011` | high | Variable frame rate in the delivery (`MED001`) | `measured-behavior.md` M6 | `vibe-editing-review` |
| `QA012` | medium / info | No audio stream / mono audio | ffprobe | `vibe-editing-review` |
| `QA013` | medium | Pixel format other than `yuv420p` in an SDR delivery | *inference*: player and phone decoder support | `vibe-editing-review` |

### Known limits

- `MED001` reads packet timestamps of the first 30 s only; a phone file that changes its rate later passes.
- `MED007` and `CAP008` are heuristics; `CAP008` compares single words, and multi-word terms only by case.
- `CAP011` knows a fixed list of English and Russian prepositions and conjunctions;
  it does not see a split number and unit, or a split noun and adjective.
- `QA002`–`QA004` cannot tell an intended fade, hold or pause from a defect.
- `QA005` needs `--loudness-target`; there is no default target, because YouTube publishes none.
- No rule reads meaning, rhythm, framing, legibility on a phone or licences: those stay manual.

## `edl.py check` — the cut

| Problem or warning | Why |
| --- | --- |
| `out` past the end of the source (with `--probe`) | the render would stop short |
| `in` or `out` not on the frame grid | they are snapped; the warning shows where |
| Clip shorter than half a second, or shorter than two audio fades | usually a mistake |
| No `reason` | every clip says why it is in the cut |
| A source played out of its recorded order, or a range used twice | reordering and repeats are decisions |
| A source frame rate different from the EDL's (with `--probe`) | make a working copy for frame-exact cuts |

## Manual

| Check | How |
| --- | --- |
| Meaning at every join | read and listen against the source (`acceptance-checklist.md`) |
| Rhythm, breath, intonation | listen on headphones and on a phone speaker |
| Faces, captions and actions not covered | frames at every insert |
| Legibility on a phone | watch on a real device |
| Private data and test labels | every scene, by eye |
| Licences of music, fonts, footage and voices | `project.md` asset table |
