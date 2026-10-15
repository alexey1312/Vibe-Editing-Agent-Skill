# Measured behaviour

What this repository measured itself, as opposed to what it cites.
A claim is *Measured* only when a section below records it with `Status: measured`;
a test blocks citing a section that is not.

Every section except M7 is re-run by `scripts/probes/ffmpeg_probes.py`,
which makes its own synthetic media (lavfi test patterns and tones),
so anyone can repeat it:

```bash
python3 scripts/probes/ffmpeg_probes.py --check --format markdown
```

`--check` compares the result with `scripts/probes/expectations.json`
and fails when FFmpeg behaves differently.
CI runs it on every push (`.github/workflows/validate.yml`).

## M1 — `edl.py render` keeps exactly the planned frames

Status: measured · 2026-10-15 · FFmpeg 9.0.2 (Homebrew), macOS 27 on Apple silicon · probe `M1`

- A 10 s test pattern at 30 fps with a 3 s keyframe interval,
  and a 440 Hz beep from 1.0 to 1.2 s in every 2 s.
- An EDL with three clips (0.5–2.0, 3.2–5.5 and 8.0–9.4 s) rendered with `edl.py render`.
- **Result:** 156 frames, as the EDL adds up to;
  each output frame is the planned source frame (0 of 156 wrong, matched on 48×27 grey thumbnails);
  the beeps start at 0.500, 3.300 and 4.800 s,
  which is where `edl.py map` puts them, within 0.1 ms.
- **Why it matters:** the EDL, the subtitles retimed with it, and the render agree.
  Captions and inserts placed with `edl.py retime` and `edl.py map` land on the right frame.

## M2 — a stream-copy cut starts at the keyframe before the cut point

Status: measured · 2026-10-15 · FFmpeg 9.0.2 · probe `M2`

- Source: 10 s at 30 fps with a keyframe every 3 s.
- Command: `ffmpeg -ss 4 -i source.mp4 -t 2 -c copy out.mp4`.
- **Result:** the file holds 92 video packets, not 60:
  it starts at the keyframe at 3.0 s.
  An MP4 edit list hides the extra second.
  A decoder that honours the edit list shows the first frame from 4.0 s;
  with the edit list ignored (`-ignore_editlist 1`) the first frame is from 3.0 s.
  `ffprobe` reports a duration of 2.17 s.
- **Why it matters:** a tool that ignores edit lists shows a second that the edit removed,
  and an event time read from such a file is wrong.
  Re-encode every cut (`edl.py render` does); never stream-copy a cut that must be frame-exact.

## M3 — a hard audio join makes a step; 10 ms fades remove it

Status: measured · 2026-10-15 · FFmpeg 9.0.2 · probe `M3`

- Two clips of a 440 Hz tone, joined where the phase does not match, rendered as 16-bit PCM.
- **Result:** without fades, the largest sample-to-sample step at the join is 14.5 times
  the largest step anywhere in the tone.
  With 10 ms fades out and in (`audio_fade_ms: 10`, the default), it is 0.08 times.
- **Why it matters:** the step is the click a listener hears at a join.
  The measurement shows the step; how loud the click sounds on speech is not measured here.
  video-use uses 30 ms fades at every join (`references/sources.md`);
  a longer fade can soften the first or last sound of a word, so listen at every join.

## M4 — mixed picture sizes: the concat filter fails, the concat demuxer does not

Status: measured · 2026-10-15 · FFmpeg 9.0.2 · probe `M4`

- Two clips, 320×180 and 160×90.
- **Result:** the `concat` filter stops with
  "parameters … do not match the corresponding output link".
  The concat demuxer with `-c copy` exits with success
  and writes one stream that `ffprobe` reports as 320×180,
  although half of it is 160×90.
- **Why it matters:** a quick join of phone clips, screen recordings and exports
  can give a file that looks valid to `ffprobe` and fails in a player or an editor.
  `edl.py render` scales and pads every clip to one size before it joins them.

## M5 — rotation metadata does not change the coded size

Status: measured · 2026-10-15 · FFmpeg 9.0.2 · probe `M5`

- A 320×180 file remuxed with `-display_rotation 90`.
- **Result:** `ffprobe` reports width 320 and height 180, plus a display matrix with rotation 90.
  `media_probe.py` reports the displayed size, 180×320,
  and a frame that ffmpeg decodes with its default autorotation is 180×320.
- **Why it matters:** phone footage often stores portrait video as rotated landscape.
  A layout planned on the coded size is wrong; plan on the displayed size.

## M6 — a variable frame rate is visible in the packet timestamps

Status: measured · 2026-10-15 · FFmpeg 9.0.2 · probe `M6`

- A 60 fps pattern retimed so that its first 1.5 s run at 30 fps (`-fps_mode vfr`), and a constant 30 fps file.
- **Result:** `r_frame_rate` is 60/1 and `avg_frame_rate` is 5400/113 for the variable file;
  the packet scan in `media_probe.py` flags it (`MED001`) and does not flag the constant one.
- **Why it matters:** phones record a variable frame rate.
  Cutting it directly can drift picture against sound;
  make a constant-frame-rate working copy first.

## M7 — the default Homebrew FFmpeg cannot burn captions

Status: measured · 2026-10-15 · Homebrew `ffmpeg` 9.0.2_1 on macOS 27 · `scripts/toolchain_report.py`

- `ffmpeg -filters` on that build lists no `subtitles`, `ass` or `drawtext` filter,
  and `zscale` and `libplacebo` are missing too.
- Homebrew's formula metadata (`brew info --json=v2 ffmpeg ffmpeg-full`, 2026-10-15)
  lists 11 dependencies for `ffmpeg`, without libass or freetype,
  and 47 for `ffmpeg-full`, with both.
- **Why it matters:** "burn the subtitles in with ffmpeg" fails on a stock Homebrew install.
  Burn captions in the engine (HyperFrames or Remotion),
  or install a build with libass after approval.
  `toolchain_report.py` says which case applies on the machine at hand.
