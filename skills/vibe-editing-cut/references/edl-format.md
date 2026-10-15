# EDL format

The edit decision list (EDL) is the cut, written down:
which interval of which source goes into the video, in what order, and why.
The author approves the EDL before anything is rendered.
Every later step — the render, the captions, the inserts, the QA scan — reads the same file.

"EDL" here means this JSON list, not the CMX 3600 text format.
To move the cut into an editor, export from the tool that made it,
or rebuild it there from `edl.py table`.

## File

`edit/edl.json`, next to the project's `project.md`:

```json
{
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "sample_rate": 48000,
  "audio_fade_ms": 10,
  "sources": {
    "take_02": "../originals/take_02.mp4",
    "screen_01": "../work/screen_01_cfr30.mp4"
  },
  "clips": [
    {"id": "c01", "source": "take_02", "in": "00:14.20", "out": "00:20.40",
     "role": "problem", "reason": "first complete statement of the problem"},
    {"id": "c02", "source": "screen_01", "in": "01:02.00", "out": "01:10.80",
     "role": "action", "reason": "the click and its result, no loading wait"},
    {"id": "c03", "source": "take_02", "in": "00:42.60", "out": "00:50.00",
     "role": "result", "reason": "result in one sentence; take 1 stumbles here"}
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `fps` | yes | Delivery frame rate. Every `in` and `out` is snapped to this frame grid. |
| `sources` | yes | Source id → path, relative to the EDL file. Point at working copies, never at a file you will change. |
| `clips` | yes | The cut, in output order. |
| `clips[].source` | yes | A key of `sources`. |
| `clips[].in`, `out` | yes | Source time. `out` is exclusive: the frame at `out` is not in the cut. |
| `clips[].reason` | yes in practice | Why this interval is in the cut. `edl.py check` warns when it is missing. |
| `clips[].id` | no | Stable name used by captions, inserts and review findings. Default `c01`, `c02`, … |
| `clips[].role` | no | Its job in the story: hook, problem, action, result, next step, B-roll. |
| `width`, `height` | no | Output size; each clip is scaled to fit and padded. Without them the sources must match. |
| `sample_rate` | no | Output audio rate, default 48000. |
| `audio_fade_ms` | no | Fade out and in at every join, default 10 (*Measured* M3). `0` turns fades off. |

Times can be seconds (`14.2`), `MM:SS.sss`, `HH:MM:SS.sss`, SMPTE `HH:MM:SS:FF` at `fps`, or frames (`426f`).

## Two clocks

Every instant has a **source time** (where it is in a take)
and an **output time** (where it plays in the video).
Removing a pause shifts everything after it.
Never place a caption, an insert or a review note by source time.

```text
source  take_02: |--c01 14.2–20.4--|  ...  |--c03 42.6–50.0--|
output         : |0.0 ---- 6.2|6.2 ---- c02 ---- 15.0|15.0 ---- 22.4|
```

- `python3 scripts/edl.py table edit/edl.json` prints both clocks for every clip.
- `python3 scripts/edl.py map edit/edl.json --source take_02 44.0` gives the output time of a source instant,
  or `cut` when the instant was removed.
- `python3 scripts/edl.py retime …` moves word timestamps or SRT cues from source time to output time
  (*Measured* M1: the render and the mapping agree within 0.1 ms).
- `python3 scripts/edl.py cuts edit/edl.json --probe` lists what each source loses —
  the list of removed intervals the author reviews.

## Rules

- **One reason per clip.**
  "Clean take" is not a reason; "take 1 stumbles on the number" is.
- **Doubtful cuts go into a second EDL.**
  Keep version A conservative and write `edl_b.json` with the riskier cut;
  the author picks after listening to both.
- **Reordering is a decision.**
  `edl.py check` warns when a source plays out of its recorded order;
  confirm that each moved thought still makes sense alone.
- **Working copies, not originals.**
  A variable-frame-rate phone file, a rotated file or an HDR file gets a working copy first
  (`MED001`, `MED002`, `MED010`); the EDL points at the copy, and `project.md` records the conversion.
- **The EDL changes only with approval.**
  After approval, a new idea is a new version (`edl_v2.json`), not an edit of the approved file.

## Rendering and engines

- `edl.py render` re-encodes every clip:
  video between half-frame bounds, so exactly the frames `[in, out)` survive;
  audio on the exact frame times, with the fades;
  every clip scaled and padded to one size before the join
  (*Measured* M1; M4 shows why the size step matters).
  Use `--size 640x360 --preset veryfast` for a proxy draft.
- It never stream-copies a cut (*Measured* M2).
- `edl.py hyperframes` prints one `<video>` per clip with
  `data-start`, `data-duration` and `data-media-start` (seconds),
  the timing contract of the HyperFrames skills (`references/sources.md`).
  The default keeps the sound on the `<video>` (`data-has-audio="true"`), as current HyperFrames does;
  `--separate-audio` writes the older muted `<video>` plus `<audio>` form.
  Follow the installed `hyperframes-core` skill when the two disagree.
- `edl.py remotion` prints one `<Sequence>` per clip with `<Video trimBefore durationInFrames>`,
  in frames at the EDL's `fps`; the composition must use the same frame rate.
  Remotion deprecated `trimAfter`, `startFrom` and `endAt` (`references/versions.md`).
