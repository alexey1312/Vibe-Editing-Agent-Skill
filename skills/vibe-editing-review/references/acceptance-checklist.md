# Acceptance checklist

A video is accepted when someone has watched it all the way through, with sound,
on the device its viewers use — and every line below is either checked or listed as not checked.
Scripts find black frames and loud peaks; they do not find a changed meaning.

## How to check

1. **Scan.** `qa_scan.py` against the brief, the EDL and the captions (machine checks below).
2. **Compare the words.** Read the final transcript next to the approved script or EDL table,
   and next to the sources for every cut that removed words.
3. **Look at the joins.** Frames either side of every join (`edl.py table` gives the output times),
   and the middle frame of every transition.
4. **Watch it once, without stopping,** with sound, on a phone if the viewers use phones.
   Then once more without sound, as many feeds play it.
5. **Write the report** (`plan-format.md`): findings with output time, evidence and a fix;
   what passed; what was not checked.

Ask for evidence for every serious finding — a frame, an audio range, a source time.
An agent can misread small text or fast motion in a frame; say how sure each finding is.

## Content and perception

| Check | How |
| --- | --- |
| The opening says why to keep watching | first 3 s, without sound |
| The cut did not change the meaning of what was said | final words against the sources at every join |
| Names, numbers and claims are correct | against the glossary and the sources of the facts |
| Each scene carries one thought | watch scene by scene |
| What happens is clear in the first seconds without sound | mute and watch |
| Transitions do not get in the way of reading or of the action | middle frames |
| The voice is clear on an ordinary phone speaker | listen on the phone |
| Graphics never cover the face, the captions or the action | frames at every insert |
| A recreated interface is labelled where accuracy matters | inserts list |

## Technical and handoff

| Check | How |
| --- | --- |
| Size, frame rate and duration match the brief | `qa_scan.py --width --height --fps --duration` (`QA001`) |
| The file lasts as long as the approved EDL | `qa_scan.py --edl` (`QA009`) |
| No unplanned black or frozen picture | `QA002`, `QA003` |
| No dropped sound or unplanned long silence | `QA004` |
| Loudness and true peak meet the target | `QA005`, `QA006` with `--loudness-target` |
| Constant frame rate, picture and sound the same length | `QA010`, `QA011` |
| Pixel format plays everywhere | `QA013` |
| The web file can start playing before it has downloaded | `QA007` |
| Captions follow the final timeline and the limits | `qa_scan.py --captions` (`QA008` with the `CAP` rule) |
| The file opens in an ordinary player | open it |
| No personal data, notifications or test labels in the picture | by eye, every scene |
| Every font, track, image and voice has a known source and licence | `project.md` asset table |
| The project, versions, assets and render command are saved | `project.md` |
| Delivered: the video, the captions file, a log of significant changes | `exports/` |

## What a scan cannot tell

- whether a join keeps the sense and the breath of the sentence;
- whether the pace fits the audience;
- whether the picture and the words tell the same story;
- whether the text is legible at the real size on the real device.

Write each of these into the report as checked by a person, or as not checked.

## After acceptance

- Keep the accepted version and its project together; deliver the editable project with the video,
  so a number, a logo or a format can change without starting again.
- Turn repeated work into a template only after the second or third video turned out the same way (`series.md`).
