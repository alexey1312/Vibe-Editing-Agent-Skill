# Edit requests

An edit is only as good as the note that asks for it.
Turn a vague note into a checkable one before changing anything,
and check the same place again after the change.

## From vague to checkable

| Vague | Checkable |
| --- | --- |
| "Make it more dynamic." | "At 00:08 remove the 0.6 s pause before 'and then'." |
| "Make it look expensive." | "Use the brand font for captions; one accent colour; no drop shadows." |
| "The captions are off." | "Cue 14 (00:31.2) starts 0.3 s before the word 'export'." |
| "Fix the end." | "End on the result frame at 00:52.0; cut the last 1.4 s of silence." |

A checkable note names:

1. **the place** — scene or clip ID and output time;
2. **the defect** — what is seen or heard;
3. **the wanted result** — what should be there instead;
4. **what must not change** — duration, sound, neighbouring scenes.

When the author's note is vague, propose a checkable version and ask before applying it.

## One level per pass

Change one level at a time, in this order:
**story → pace → text → picture → sound**.
A design pass on a story that will still change is work thrown away:
approve the sequence of thoughts before adding graphics.

## The loop

```text
defect → note → change → preview of the same range (± 1 s of context) → accept or revert
```

- Keep the last approved version (EDL, composition, render).
  If one fix breaks two other places, go back to it and give a narrower note.
- Show the change on the same output time as the note, with one second before and after.
- For composition, a still frame with a mark is enough.
  For rhythm and sound, only a playable range shows the problem.
- After any change to the cut, retime captions and inserts (`edl.py retime`, `edl.py map`).
- After a manual change in an editor or a timeline UI, read the project again before the next edit.

## Notes about a reference video

Describe what to take from a reference in terms of structure, pace, type, motion and sound.
Say which observations the available video confirms and which are guesses.
Build the new piece from the author's own facts, words and material;
take the principle, not the frames.
