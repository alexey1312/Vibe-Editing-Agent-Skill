# Cutting speech

The cut decides what the viewer understands.
Approve the sequence of thoughts before any caption, music or graphic:
otherwise every change of meaning forces a rebuild of the design.

## 1. Inventory before any cut

Run `python3 scripts/media_probe.py originals/ --format markdown`, then listen.
For every source, collect:

- file, duration, displayed size, frame rate, audio streams (`media_probe.py`);
- its role: main speech, screen, B-roll, music;
- defects: noise, focus, rotation, missing sound, variable frame rate, HDR;
- language, and the names, brands and numbers that recognition gets wrong — the glossary;
- repeats, good phrasings and useful actions.

Then write a table without cutting anything:

| Source | In–out | Verbatim phrase | Sound | What is visible | Possible role |
| --- | --- | --- | --- | --- | --- |

Mark words the recogniser was unsure of.
Propose three openings, each with what the viewer understands in the first seconds,
and keep the source time of every proposal.

## 2. Working copies

Fix the file before cutting the story.

- Variable frame rate (`MED001`, *Measured* M6): make a constant-frame-rate copy at the delivery rate.
- Rotation metadata (`MED002`, *Measured* M5): plan on the displayed size.
- HDR sources next to SDR screen recordings (`MED010`): decide the delivery, then tone-map once.
- Mixed frame rates or audio formats (`MED004`, `MED005`): convert every copy once, to the brief.

Record each conversion in `project.md`; the EDL points at the copies.

## 3. Choosing takes

- Prefer a whole sentence from one take.
  Halves from two takes change the intonation and the position of the face.
- With several takes of the opening, offer three and let the author choose.
- When the proof the story needs is missing from every take, say so:
  the author records it, nobody invents it.

## 4. Joins

- Start and end a thought with its condition or caveat intact.
  Cutting "only if" or "not" changes the claim.
- Cut in the silence between words, never inside a word.
  Leave a little air around the words; video-use works with 30–200 ms of padding (`sources.md`).
- Keep natural breathing and the stress of the sentence.
- Listen to a join before looking at it.
- A visible jump in the picture can be covered with B-roll, a screen insert or a reframe;
  a jump in meaning cannot.
- Do not remove every pause with one silence threshold.
  Some pauses carry the emphasis; a fully gapless delivery sounds breathless.

## 5. Candidates, not cuts

```bash
python3 scripts/edl.py candidates --words transcripts/take_02.json --min-gap 0.4 --language ru
```

It lists pauses between words, phrases said twice (usually keep the later, complete attempt)
and common filler words.
These are candidates for the plan.
The author approves each removal; some fillers and pauses carry meaning.
The video-use figure labels silences of 400 ms or more as safe cut candidates,
and its skill text says they are "usually the cleanest" — a starting point, not a rule.

## 6. Versions A and B

Keep version A conservative.
Put every doubtful cut into `edl_b.json` and render both;
the author decides by listening, not by reading the table.

## 7. Transitions

A straight cut is the default.
Use a transition only when it says something:

| Transition | Use | Check |
| --- | --- | --- |
| Cut | a new action or thought | the sound at the join |
| Dissolve | time passes, or two ideas merge | the middle frame: two layers of text are unreadable |
| Wipe | movement in a direction the story has | the direction matches the logic |
| Match cut | a shape or position links two shots | the match holds on the frames either side |

Show the middle frame of any transition for approval.
Sound that leads or trails the picture (J and L cuts) is built in the engine,
with the audio placed separately from the video.

## 8. Clips from a long recording

For each candidate clip of 30–60 s, give:
source in–out, the thesis, the context the viewer misses, and the risk of losing meaning.

- Reject a clip that opens with a pronoun with nothing before it,
  that cuts a question in half, or that drops a caveat.
- A title must not promise more than the clip says.
- Build openings only from words that were said.
- Show the selection table before any render; each approved clip gets its own EDL.

## 9. A worked shape

An eight-minute explanation with two takes of the intro and a screen recording,
cut to 55 seconds (an example of structure, not a measured project):

| Output | Beat |
| --- | --- |
| 00–04 s | the viewer's problem, in one sentence |
| 04–12 s | the starting situation |
| 12–30 s | two actions on screen |
| 30–45 s | the result and a short diagram |
| 45–55 s | one caveat and the next step |

Ready means: a person who has not seen the material can retell the benefit and the next step.
The number of effects does not matter for that.
