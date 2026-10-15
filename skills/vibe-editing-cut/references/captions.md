# Captions

A wrong name, number or "not" in a caption is worse than any styling problem.
Fix the text and the timing first; choose the look last.

## Order of work

1. Get word timestamps for every source (the transcripts reference of `vibe-editing-cut`).
2. Correct the text against the recording and the glossary (`transcripts/glossary.txt`).
3. Move the words onto the final timeline after the cut is approved:
   `python3 scripts/edl.py retime edit/edl.json --words take_02=transcripts/take_02.json -o edit/words.out.json`.
4. Group them into cues:
   `python3 scripts/captions.py build --words edit/words.out.json -o exports/final.srt --duration <seconds>`.
5. Check the file:
   `python3 scripts/captions.py check exports/final.srt --video exports/final.mp4 --glossary transcripts/glossary.txt`.
6. Look at the longest cues on the real frame:
   next to the face, over the interface, at the platform's own buttons.

Never retime captions by hand after a cut: a removed pause shifts every later cue (*Measured* M1).

## Defaults and where they come from

| Limit | Default | Source |
| --- | --- | --- |
| Lines per cue | 2 | Netflix General Requirements; Netflix Russian guide |
| Characters per line | 42 | Netflix Russian guide (raised to 42 on 2025-12-19) |
| Reading speed | 17 characters per second (adult) | Netflix Russian guide; 13 for children's programmes |
| Duration on screen | 5/6 s to 7 s | Netflix General Requirements |
| Gap between cues | 2 frames (0.083 s at 24 fps, 0.067 s at 30 fps) | Netflix Subtitle Timing Guidelines |
| Vertical 9:16 | about 25 characters per line, up to 3 lines (`--layout vertical`) | BBC Subtitle Guidelines |
| Reading rate in words | 160–180 words per minute (`--max-wpm 180`) | BBC Subtitle Guidelines |

These are broadcast and streaming norms.
Social video has no published caption standard;
use them as a starting point and change them in the brief, not cue by cue.
For SDH (captions for deaf and hard-of-hearing viewers) Netflix allows faster reading speeds;
see `sources.md`.

## Line breaks

- Keep a caption on one line unless it is longer than the line limit.
- Break after punctuation; break before a conjunction or a preposition, not after it.
- Prefer a bottom-heavy pair (shorter top line), but never one or two short words alone on top.
- Keep tightly bound words together: a pronoun and its verb, a noun and its adjective, a number and its unit.
  `captions.py` handles the first three rules; the last needs a person who reads the language.

## Rules `captions.py check` applies

| Rule | Finds |
| --- | --- |
| `CAP001` | more lines than the limit |
| `CAP002` | a line longer than the limit |
| `CAP003` | reading speed above the limit (characters per second, and words per minute with `--max-wpm`) |
| `CAP004` | shorter than the minimum or longer than the maximum time on screen |
| `CAP005` | overlaps the next cue |
| `CAP006` | a gap shorter than the minimum, which flickers |
| `CAP007` | ends after the video ends — usually captions left on the source timeline |
| `CAP008` | a word that looks like a glossary term but is spelled differently |
| `CAP009` | a word that mixes Cyrillic and Latin (or Greek) letters, such as "Сlaude" with a Cyrillic С |
| `CAP010` | an empty, inverted or unreadable cue |
| `CAP011` | line 1 ends with a preposition or conjunction |

## Russian, and mixed scripts

- Put every name, brand and product into the glossary with its exact spelling and case.
  Recognisers often turn Latin product names into Cyrillic, or mix the two inside one word.
- Write numbers the way the brief wants them (digits or words) and keep it the same everywhere.
- Check the font: every glyph of the caption text must exist in it.
  A missing glyph silently falls back to another font, or to an empty box.

## Look

- Start a vertical 1080×1920 pilot at about 52–64 px with a contrasting box or outline;
  check it on a real phone. This is a starting design, not a platform rule.
- Show whole short phrases for calm explanation.
  Highlight word by word only where the word timings are exact and the emphasis helps.
- One large accent per block of thought, for about a second, then back to normal captions.

## Burned in, or a file

- Deliver an SRT with the video whenever the platform accepts one: the viewer can turn it off,
  and a later fix does not need a new render.
- To burn captions into the picture, use the engine (HyperFrames, Remotion)
  or an FFmpeg build with libass;
  the default Homebrew build has no `subtitles` filter (*Measured* M7; `toolchain_report.py` checks).
