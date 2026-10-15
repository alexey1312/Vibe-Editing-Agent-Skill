---
name: vibe-editing-cut
description: >-
  Use this skill when recorded footage must become a finished cut by talking
  to an agent ("vibe editing"): talking-head takes, interviews, podcasts,
  tutorials or screen recordings where the agent picks takes, removes pauses,
  false starts and fillers, shortens or reorders speech, or cuts a long
  recording into clips. It inventories sources (variable frame rate,
  rotation, HDR), works from word timestamps, writes an edit decision list
  with source and output times for approval, renders frame-accurately with
  FFmpeg, moves captions and inserts onto the new timeline, and plans sound
  (fades at joins, ducking, loudness). Also for choosing the tool for an edit
  and deciding which media may be uploaded. Not for HyperFrames or Remotion
  code, motion graphics or explainers without footage (hyperframes,
  general-video, remotion-best-practices), captions or overlays on footage
  that stays unchanged (embedded-captions, talking-head-recut), or checking a
  finished render (vibe-editing-review).
---

# Vibe editing: the cut

Turn raw takes into a cut that keeps the meaning, then hand it to the engine for graphics.
The agent proposes and writes; the renderer computes frames; the author decides and accepts.
Approve the story before the design: every change of meaning after the graphics forces a rebuild.

- Routes and tools by material: `references/routes.md`
- The EDL and the two clocks: `references/edl-format.md`
- Transcripts and recognisers: `references/transcripts.md`
- Cutting speech: `references/cutting.md`
- Captions: `references/captions.md`
- Sound: `references/audio.md`
- Inserts, layouts, 9:16, other languages: `references/inserts-and-layouts.md`
- Screen recordings: `references/screen-recordings.md`
- Folder, brief and `project.md`: `references/project-memory.md`
- Notes the author gives: `references/edit-requests.md`
- Data, licences and money: `references/data-and-licences.md`
- Plan format: `references/plan-format.md`
- What this repository measured: `references/measured-behavior.md`
- Versions and dates: `references/versions.md`
- Citations: `references/sources.md`

## Contract

- **Phase 1 is read-only.**
  The toolchain report, the media inventory, reading transcripts that exist,
  and writing the plan change nothing and send nothing anywhere.
- **No cut, render, upload, install or paid call without approval of item IDs**
  (`references/plan-format.md`).
  "Make it shorter" before a plan exists is a request for the plan.
- **Originals are never changed.**
  Working copies go to `work/`, renders to `renders/`, deliveries to `exports/`.
  `edl.py render` refuses to write over a source or an existing file without `--force`.
- **Two clocks.**
  Source time for takes, output time for everything a viewer sees;
  convert with `edl.py map` and `edl.py retime`, never by hand.
- **Cite or label.**
  A claim about a tool cites `references/sources.md` or a *Measured* section;
  versions and prices come from `references/versions.md` with its date;
  a judgement of taste or meaning is labelled as such.
- **Report verification honestly.**
  A frame check misses rhythm; a script misses meaning.
  Say what was watched, listened to, scanned — and what was not.

## 1. Preflight

```bash
python3 scripts/toolchain_report.py --format markdown
python3 scripts/media_probe.py originals/ --format markdown
```

- The toolchain report says what this machine can do:
  frame-accurate renders, burning captions (many FFmpeg builds cannot, *Measured* M7),
  loudness measurement, local speech recognition, HyperFrames, Remotion;
  and which API key names are set (never their values).
- The inventory flags what changes the cut:
  variable frame rate (`MED001`), rotation (`MED002`), HDR (`MED010`),
  mixed frame rates or audio formats (`MED004`, `MED005`); rules in `CHECKS.md` in this skill's repository.
- Read the project's own instructions and `project.md` if they exist.
- Write the brief, or ask for what it lacks: viewer and takeaway, delivery, must-stay, must-not, cloud (`references/project-memory.md`).

## 2. Route

Pick the route from the material and the deliverable (`references/routes.md`).
This skill owns the cut: takes, joins, the EDL, the render, captions and sound on the new timeline.
Graphics belong to the engine's skills: HyperFrames (`hyperframes`, `general-video`, `hyperframes-core`)
or Remotion (`remotion-best-practices`).
Captions or overlays on footage that must not change belong to `embedded-captions` or `talking-head-recut`.

## 3. Transcripts

- Word timestamps per source, made once, kept in `transcripts/` (`references/transcripts.md`).
- Recognition in the cloud sends audio out and costs money; local recognition needs an install.
  Both wait for approval, with the provider, the cost and the data named in the plan.
- Correct names and numbers against a glossary before planning any cut.

## 4. Plan the story

1. Table of the material: source, in–out, verbatim phrase, sound, what is visible, possible role.
2. Three openings, each with what the viewer understands in the first seconds.
3. Candidates: `python3 scripts/edl.py candidates --words transcripts/<take>.json` —
   pauses, repeats and fillers to consider, never to cut automatically (`references/cutting.md`).
4. The story in beats, then `edit/edl.json`: every clip with a reason (`references/edl-format.md`).
5. `python3 scripts/edl.py check edit/edl.json --probe`, `table` and `cuts --probe`:
   the clips with both clocks, and every removed interval for the author to read.
6. Doubtful cuts go into `edit/edl_b.json`, not into version A.

## 5. Render the draft

```bash
python3 scripts/edl.py render edit/edl.json -o renders/draft_v1.mp4 --size 640x360 --preset veryfast
```

- Every clip is re-encoded on frame bounds, with 10 ms audio fades, scaled to one size
  (*Measured* M1, M3, M4). A stream-copy cut is never frame-exact (*Measured* M2).
- The first draft has no music, captions or effects: speech and picture only.
- Listen to every join on headphones; look at the frames either side.
  Fix with narrow notes (`references/edit-requests.md`) and a new EDL version.

## 6. Captions, sound, inserts

- **Captions:** `edl.py retime` moves word times onto the output timeline;
  `captions.py build` groups them; `captions.py check` applies the limits (`references/captions.md`).
- **Sound:** speech first, then music with ducking, then effects;
  measure loudness against the brief's target and set `loudnorm` targets explicitly (`references/audio.md`).
- **Inserts:** mark them on the output timeline (`edl.py map`), approve a still frame,
  then build them in the engine; `edl.py hyperframes` and `edl.py remotion` hand over the cut
  (`references/inserts-and-layouts.md`).
- **Other formats:** a 9:16 version is a new layout, not a centre crop.

## 7. Hand over

- Run the review before calling the video done:
  the `vibe-editing-review` skill, or at least `python3 scripts/qa_scan.py` with the brief, the EDL and the captions.
- Update `project.md`: approved EDL version, last good render, commands, assets and licences, open defects.

## Workflow

### Phase 1 — Recommend

1. **Preflight:** toolchain report, inventory, brief, project instructions.
2. **Plan** with `references/plan-format.md`:
   sources and conversions; the story and EDL v1; removed intervals; doubtful cuts;
   captions, sound and inserts; data, money and licences; what cannot be verified here.
3. **Ask** which item IDs to apply.

### Phase 2 — Apply and verify

1. Apply approved items only, one level at a time: story, pace, text, picture, sound.
2. After each change, render or preview the same range with a second of context, and listen.
3. Re-run `edl.py check` and `captions.py check`; run `qa_scan.py` on every draft that goes to the author.
4. Update item statuses and `project.md`; report what was not verified.

## Guardrails

- Do not cut, render, upload, transcribe in the cloud or install anything in Phase 1.
- Do not change or re-encode files in `originals/`.
- Do not stream-copy a cut that must be frame-exact.
- Do not place captions or inserts by source time.
- Do not remove every pause with one threshold, or synthesise a missing word without the author's decision.
- Do not print a key or a token in the chat, a log or a file.
- Do not add music, fonts or footage without a recorded source and licence.
- Do not take over the engine's ground: composition code belongs to the HyperFrames or Remotion skills.
