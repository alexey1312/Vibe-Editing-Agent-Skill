# Screen recordings

A screencast proves that something works.
Every edit must keep the link between an action and its result visible.

## Recording

- Use a clean interface with test data.
  Turn notifications off.
- Show one action from start to end, with a short pause before and after it.
- Set the interface scale so the text is legible at the final video size, not at the monitor's size.
- Record a few seconds longer than needed at both ends; the start of a recording varies.

## Cutting

- Remove waits for loading; keep the click and its result in the same clip
  or in clips that follow each other directly.
- Let the viewer see the target before the click.
- Zoom only on details that are not legible at the delivery size.
- Do not move the zoom while the viewer reads; move, hold, then read.
- The first frame must be clear without sound: it may become the thumbnail.

```markdown
| Clip | Source in–out | Action | Result visible at | Zoom |
| --- | --- | --- | --- | --- |
| c02 | 01:02.0–01:10.8 | clicks Export | 01:09.4 | 150 % on the dialog, 01:03.0–01:06.0 |
```

## What usually goes wrong

| Defect | Fix |
| --- | --- |
| The cursor jumps between positions | keep the frames of the move, or cut on a still cursor |
| The zoom moves while text is on screen | hold the zoom still during reading |
| A cut hides which action caused the result | keep the click and the result adjacent |
| Real customer data or messages in the frame | re-record with test data, or blur and say so in the handoff |
| A recreated interface shown as a real recording | label it as a mock-up where the viewer relies on it being real |

## Tools

- **OpenScreen** records a window or the screen, adds automatic or manual zooms,
  cuts by deleting text in its transcript,
  and connects to a coding agent through its `openscreen-demo` skill and MCP server (`sources.md`).
  Its built-in assistant is off until the user adds their own provider key.
- **This skill** cuts any recording with an EDL;
  the zooms and callouts are then built in HyperFrames or Remotion,
  timed with `edl.py map`.
- When an agent draws an interface in code instead of recording it,
  check it against the real product, and label it where accuracy matters to the viewer.
