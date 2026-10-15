# Troubleshooting

These are hypotheses, not diagnoses.
Confirm the cause with the error log and the smallest example that reproduces it,
fix it, check the same range again, then check the scenes next to it.
Keep the working version, the log and the defective file until the fix is accepted.

| Symptom | Likely cause | Next step |
| --- | --- | --- |
| A black frame or an empty asset | wrong path, no access to the file, an unsupported codec, a slow load | test one file in one scene; check the path from the project folder |
| The first second of a clip shows what was cut | a stream-copy cut started at an earlier keyframe (*Measured* M2) | re-encode the cut; `edl.py render` never stream-copies |
| Captions drift after the cut | captions still on source time | `edl.py retime`; check with `captions.py check --video` (`CAP007`) |
| Cyrillic text changes font or shows boxes | the font has no Cyrillic glyphs or did not load | use a local font with the glyphs; check the exported file, not the preview |
| The preview and the MP4 differ | animation tied to clock time, network assets, assets not loaded before the frame | make each frame depend only on its number; keep assets local; wait for fonts |
| A click at a join | no fade at the join (*Measured* M3) | 10 ms fades (`audio_fade_ms`); listen again |
| A join of clips plays garbled or at the wrong size | clips of different size joined with the concat demuxer (*Measured* M4) | scale and pad every clip before the join (`edl.py render`) |
| A phone clip shows sideways, or a layout is planned on the wrong size | rotation metadata (*Measured* M5, `MED002`) | plan on the displayed size; keep ffmpeg's autorotation |
| Picture and sound slowly drift apart | variable frame rate source (*Measured* M6, `MED001`) | cut a constant-frame-rate working copy |
| Washed-out or too dark shots next to screen recordings | HDR source mixed with SDR (`MED010`) | choose the delivery; tone-map the HDR copies once |
| "No such filter: subtitles" | an FFmpeg build without libass (*Measured* M7) | burn captions in the engine, or install a libass build after approval |
| It got worse after an edit | the note was too broad | go back to the last approved version; give a narrower note (`edit-requests.md`) |
| The render takes too long | 3D, blur, large frames, too much parallel work | simplify the scene; render a short range; draft at a lower size |
| The story does not hang together | striking phrases chosen without their context | go back to the thesis and the EDL; restore the context before the phrase |

## A narrow repair request

Name the scene with the defect.
Find the cause, fix it, and check the same range again with one second of context on each side.
Then check the scene before and the scene after.
