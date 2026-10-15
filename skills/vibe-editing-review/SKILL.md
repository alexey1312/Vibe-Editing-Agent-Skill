---
name: vibe-editing-review
description: >-
  Use this skill when a rendered video must be checked before it is published
  or handed over: does it match the brief (size, frame rate, duration), the
  approved edit and the script; are there black or frozen frames, dropped
  sound, long silences, clicks, loudness or true-peak problems; do the
  captions follow the final timeline, keep to line and reading-speed limits
  and spell names right; is private data visible. It scans the file read-only
  with FFmpeg, guides one full viewing with sound, and writes a report with
  output times, evidence and fixes, plus what it could not check. Also for
  diagnosing a broken render, writing the handoff for another agent, and
  turning an accepted video into a template for a series. Not for making the
  cut (vibe-editing-cut), or validating and rendering HyperFrames or Remotion
  projects (hyperframes-cli, remotion-render).
---

# Vibe editing: review

Check a rendered video against what was promised, with evidence, before anyone publishes it.
Scripts find what can be measured; a person watching once, with sound, finds the rest.
The report says which is which.

- What to check, and how: `references/acceptance-checklist.md`
- Symptoms, causes, next steps: `references/troubleshooting.md`
- Captions and their limits: `references/captions.md`
- Report format: `references/plan-format.md`
- Notes that lead to a fix: `references/edit-requests.md`
- Folder, brief, `project.md` and the handoff: `references/project-memory.md`
- From one video to a series: `references/series.md`
- Data, licences and money: `references/data-and-licences.md`
- What this repository measured: `references/measured-behavior.md`
- Versions and dates: `references/versions.md`
- Citations: `references/sources.md`

## Contract

- **The review is read-only.**
  The scans read the file; nothing is re-rendered, normalised or uploaded.
  Evidence frames go only where `--evidence-dir` points (`renders/verify/` by convention).
- **Every finding has a place, evidence and a fix:**
  output time (and source time when the cut is involved), a frame, an audio range or a script rule,
  and one narrow change (`references/plan-format.md`).
- **Fixes wait for approval** and are made by the skill that owns them:
  the cut by `vibe-editing-cut`, a composition by the engine's skills.
- **Say what was not checked.**
  `qa_scan.py` prints the list of things no script checks; the report keeps it,
  marked as checked by a person or not checked.
- **Cite or label.**
  Limits come from `references/captions.md`, `references/audio.md` targets via the brief,
  and `references/versions.md` with its date; a judgement of taste is labelled as such.

## 1. Gather

- The file to review, the brief, the approved EDL (`edit/edl.json`), the captions file, the glossary, the script.
- `project.md`: the state, decisions that must not change, the asset list.
- `python3 scripts/toolchain_report.py --format markdown`: what this machine can measure.
- When something is missing (no brief, no EDL), review what exists and list the gap.

## 2. Scan

```bash
python3 scripts/qa_scan.py exports/final.mp4 --width 1080 --height 1920 --fps 30 \
  --edl edit/edl.json --captions exports/final.srt --glossary transcripts/glossary.txt \
  --loudness-target -14 --true-peak-max -1 --evidence-dir renders/verify
python3 scripts/media_probe.py exports/final.mp4
```

- Take the loudness target from the brief; there is no default (`references/audio.md`).
- Findings `QA001`–`QA013` and the caption rules `CAP001`–`CAP011` are listed in `CHECKS.md`
  in this skill's repository; each is a lead, read the frame or listen before reporting it.
- An intended black fade, a held frame or a deliberate pause is kept with a reason, not reported as a defect.

## 3. Compare the words

- Read the final words next to the approved script or `edl.py table`.
- At every join that removed words, compare with the source:
  a lost "not", a dropped condition or a half question changes the claim.
- Check every name and number on screen and in captions against the glossary and the sources of the facts.

## 4. Look and listen

- Frames either side of every join, the middle of every transition, every insert's first and last frame.
- Graphics never cover the face, the captions or the action; nothing private is on screen.
- One full viewing without stopping, with sound, on the device the viewers use; then once without sound.
- Ask the author to watch when no person in the loop has; an agent's look at frames is not a viewing.

## 5. Report

Write the review report from `references/plan-format.md`:
a verdict in two sentences, findings with high severity first, checks that passed, and what was not checked.
Group fixes by owner and by level (story, pace, text, picture, sound) so they can be applied in one pass each.

## 6. After the verdict

- **Broken render:** follow `references/troubleshooting.md`; reproduce on one scene before changing anything.
- **Handoff:** write the state into `project.md` — goal, approved EDL, last good render, commands, assets,
  open defects with output times, decisions that need the author, the next two steps (`references/project-memory.md`).
- **Series:** only after two or three videos came out the same way; separate design from inputs and test edge cases (`references/series.md`).

## Guardrails

- Do not fix while reviewing; report, then let the owner apply approved fixes.
- Do not report a measured value as a defect without the brief's target behind it.
- Do not call a video accepted without one full viewing with sound by a person, or say plainly that it had none.
- Do not upload the video to a service to check it without approval (`references/data-and-licences.md`).
- Do not print a key or personal data from the picture into the report.
