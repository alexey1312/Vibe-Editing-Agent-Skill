# Inserts, layouts and formats

An insert must explain the thought or show the proof.
An effect for its own sake makes the video harder to follow.

## Kinds of insert

| Insert | Carries |
| --- | --- |
| Lower third or plate | a name, a term, one number, a short quote |
| Diagram | how things connect, or a sequence of steps |
| Screen | a real action in the product |
| B-roll | a picture that supports the spoken thought |

For each insert, write down:
output in and out (`edl.py map` from the source words it belongs to),
its role, how it enters and leaves, and what it needs behind it.

## Zones

Fix three zones per layout before designing anything: **face, captions, graphics**.
Graphics never cover the face or the captions,
and the face does not move when a side panel appears.
Check the number of objects on a phone-sized screen.

## Order of work

1. Mark the inserts in the **final** transcript (output time), not in the source.
2. Show a still key frame of each insert for approval.
3. Add the motion: one step at a time, in time with the words.
4. Check the first and last frame of the insert's range and the clips next to it.

For a large accent on a key phrase, keep the normal captions for the rest of the speech,
show the accent for about a second, then return to the calm style.
Start with one accent per block of thought.

## Building

- **One composition:** the cut video as a layer, the graphics on top,
  in HyperFrames or Remotion (`edl.py hyperframes`, `edl.py remotion`; the engine's skills own the details).
- **Separate render, then composite:** render the insert alone and lay it over the cut.
  A plain H.264 MP4 has no transparency;
  for an overlay with alpha, pick a format the target editor reads with alpha,
  and test one file there before the series.
  For a delivered MP4, composite the graphics onto the picture first.
- Animations must give the same picture for the same frame:
  no random values, no clock time, local assets, fonts loaded before the first frame.
  Check the first and last frame of every scene, and render the hardest transitions as a short range.

## From 16:9 to 9:16

A vertical version is a new layout, not a centre crop:
a horizontal screen with small interface text rarely survives a crop.

| 16:9 | 9:16 |
| --- | --- |
| speaker and screen side by side | one main object at a time |
| room for a diagram | larger key details |
| longer caption lines | short captions |

- Keep the sequence of thoughts and the sound; rebuild the layout scene by scene.
- Never crop away the action being demonstrated:
  the button and its result stay in frame together.
- Leave free the zones that the platform's interface covers, and check on a real phone.
  The only official numbers found are for ads:
  Meta asks to keep 14 % at the top, 35 % at the bottom and 6 % at each side of a Reels ad free of text and logos,
  and Google Ads draws a vertical safe zone of 288 px top, 672 px bottom, 192 px right and 48 px left on 1080×1920
  (the edge of each number is read from the drawing).
  No platform publishes numbers for ordinary posts (`sources.md`); treat the ad zones as a cautious default.
- A square version needs its own check of face, captions and screen edges.
- Keep separate compositions, or explicit layout parameters, so one format can change without the other.
- Show a contact sheet of a key frame from every scene before rendering.

## Another language

A translation changes the length of every phrase.
Prepare new text, a new voice and new timings, then place the captions again.
Check numbers, names and units separately.
A text box sized for one language does not fit every language.

## An explainer without footage

1. State the thesis in one sentence.
2. Choose the visual model: a process, a comparison, a structure, or a change of quantity.
3. Check the facts and the logic of the diagram before any design.
4. For each scene, write the voice text, the object on screen, and what the motion means.
5. Show one main object at a time; give it time to stand still so the viewer can read it.
6. Do not repeat the voice as long on-screen text; keep terms, numbers and links.
7. Lock the voice recording first, then time the scenes to it.
   A new take of a synthetic voice shifts the whole timeline.
   Use a voice you are allowed to use, and check the pronunciation of names and numbers.
