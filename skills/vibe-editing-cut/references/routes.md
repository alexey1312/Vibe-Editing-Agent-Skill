# Routes

Pick the route from the source material and the deliverable, not from the newest tool.
This table is a starting point for a pilot, not a quality ranking.
Check the plan and the version of a paid service before you depend on a feature.

## By material and goal

| Material and goal | Start with | Owner | Check above all |
| --- | --- | --- | --- |
| Raw speech in one or more takes → a short video | Transcript → EDL → render (this skill) | `vibe-editing-cut` | meaning at every join; names and numbers; where the audio goes for recognition |
| The same, in a project that already runs video-use | video-use's own process | `video-use` | its transcription is ElevenLabs only; its cuts are not frame-snapped (`sources.md`) |
| Plain captions on footage that stays as it is | HyperFrames `embedded-captions` | HyperFrames skills | caption text and timing |
| Designed overlays (titles, lower thirds, picture-in-picture) on footage that stays as it is | HyperFrames `talking-head-recut` — it adds graphics and cuts nothing | HyperFrames skills | face, caption and graphics zones |
| Cut first, then captions and overlays | This skill for the EDL, then the engine for the graphics | `vibe-editing-cut`, then HyperFrames or Remotion skills | captions and inserts on the **output** timeline |
| Product demo, title sequence, explainer with no footage | HyperFrames or Remotion | HyperFrames skills, Remotion's `remotion-*` skills | script, accuracy of any recreated interface |
| Screen recording with zooms | OpenScreen (`openscreen-demo` skill), or this skill plus an engine | OpenScreen, or `vibe-editing-cut` (`screen-recordings.md`) | cursor, legibility, zoom path, private data |
| Long talk or podcast → short clips | `edl.py candidates` and a selection table, one EDL per clip | `vibe-editing-cut` | each clip makes sense without the full episode |
| Editing inside a ready-made editor with an assistant | Descript (Underlord) | the service | removed words, export, plan limits |
| Multi-camera, colour grading, complex sound | Agent prepares selects and the EDL; a person finishes in a desktop editor | `vibe-editing-cut` + an NLE | sync, colour, the final mix |
| Understand an existing video, not edit it | claude-video (`watch`) | `watch` | the Gemini engine uploads the whole file (`data-and-licences.md`) |

## Which engine for graphics

- **Use the engine the project already has.**
  Two engines in one video double the checks.
- **HyperFrames** renders HTML, CSS and seekable animation to video;
  it needs Node.js and FFmpeg (`versions.md`) and is Apache-2.0 with no commercial-use threshold.
  Its skills own composition structure; this skill only hands it the EDL (`edl.py hyperframes`).
- **Remotion** renders React components frame by frame;
  its licence is free for individuals and companies of up to three people,
  and a company licence is required from four (`versions.md`).
  Its `remotion-*` skills own the code; this skill hands it the EDL (`edl.py remotion`).
- **Manim** suits formulas and geometry; **three.js** suits 3D scenes inside either engine.
  Each is a component of a scene, not a way to finish a video.

## Signs the route is wrong

- The request is "add captions" and the footage must not change: route to `embedded-captions`.
- The request is "remove the pauses" or "use the second take of the intro":
  `talking-head-recut` and `embedded-captions` cannot do it; this skill or `general-video` can.
- The request is a motion graphic with no recorded speech: the engine's skills own it from the start.
- Nobody can say what the viewer should understand at the end: write the brief first (`project-memory.md`).
