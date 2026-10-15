# Plan and report format

Nothing is cut, rendered, uploaded or installed until the author approves it by ID.
Both skills use the same shape:
`vibe-editing-cut` writes an **edit plan** with `CUT-NN` items,
`vibe-editing-review` writes a **review report** with `QA-NN` findings.

## Edit plan item

```markdown
### CUT-03 · Use take 2 for the opening; drop the false start in take 1

- **Source:** `take_01` 00:00.0–00:06.8 (false start), `take_02` 00:14.2–00:20.4
- **Output:** 00:00.0–00:06.2 (clip `c01`)
- **Why:** take 1 restarts the sentence twice; take 2 says the problem in one breath.
- **Evidence:** transcript lines 3–9; `edl.py candidates` repeat at 00:01.2; frames at 00:14.2 and 00:20.4.
- **Risk:** take 2's light is warmer; the join to `c02` may show it.
- **Verify:** listen to the join `c01`→`c02` on headphones; look at both frames.
- **Status:** proposed
```

Every item that changes the cut names its clips;
the approved EDL (`edit/edl.json`, described in the EDL format reference of `vibe-editing-cut`)
is the sum of the approved items.

## Review finding

```markdown
### QA-02 · The caption covers the button the speaker clicks

- **Where:** output 00:18.0–00:19.4 (clip `c04`, source `screen_01` 01:31.2)
- **Seen:** frame at 00:18.6 — the second caption line sits on the "Export" button.
- **Evidence:** `renders/verify/frame_00018.600.png`; `qa_scan.py` has no rule for this, found by eye.
- **Fix:** move the caption above the button for this cue only, shorten it to five words; keep the timing.
- **Severity:** high — the viewer cannot see the action the sentence describes.
- **Status:** open
```

## Rules

- **IDs are stable** in a session: `CUT-01`, `CUT-02`, … and `QA-01`, `QA-02`, ….
  A script finding keeps its rule ID in the *Evidence* line (`QA004`, `CAP003`, `MED001`).
- **Two clocks.** Give output time for anything a viewer sees, source time for anything in a take,
  and both when an item crosses the cut (`edl.py map`).
- **Evidence for every claim.** A frame, an audio interval, a transcript line, or a script finding.
  If a finding rests on a judgement, say so: *taste*, *inference*, or *not checked*.
- **One level per pass.** Story, then pace, then text, then picture, then sound (`edit-requests.md`).
  A plan that mixes levels gets split.
- **Say what was not verified.** A frame-by-frame check misses rhythm and intonation;
  a script misses meaning; nothing replaces one full viewing with sound.
- **Status values:** `proposed`, `approved`, `applied`, `verified`, `declined`, `kept` (left as is, with the reason),
  `blocked` (with the reason); review findings use `open`, `fixed`, `verified`, `won't fix`.
- **Batch approval is fine** when the author names it ("apply CUT-01 to CUT-05").
  "Make it shorter" before a plan exists means: write the plan.

## Edit plan skeleton

```markdown
# Edit plan — <project>, <date>

Brief: <duration, size, fps, language, audience, the one thing the viewer should take away>
Machine: <toolchain_report.py summary> · Sources: <n files, total length> · Transcript: <tool, where the audio went>

## Summary
<The story in three to five beats, the target length, what is cut and why.>

## Sources and conversions
## Story and selects (EDL v1)
## Removed intervals
## Doubtful cuts (EDL B)
## Captions, sound and inserts
## Data, money and licences
## Not verified
```

## Review report skeleton

```markdown
# Review — <file>, <date>

Against: <brief>, <EDL version>, <script or transcript>
Scans: qa_scan <version>, captions <version> · Viewed in full: <yes, on which device, with sound | no>

## Verdict
<Ready / ready after the high findings / not ready — and why, in two sentences.>

## Findings (high first)
## Checks that passed
## Not checked
```
