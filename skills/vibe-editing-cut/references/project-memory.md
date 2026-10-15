# Project folder and project.md

A video project outlives one chat.
The folder and `project.md` let another session, another agent or a person
continue without reading the conversation.

## Folder

```text
my-video/
├── originals/     sources as received; never changed, never re-encoded in place
├── work/          working copies: constant frame rate, rotated, SDR, renamed
├── assets/        brand files, fonts, music, sound effects — each with its licence
├── transcripts/   word timestamps per source (JSON) and a glossary
├── edit/          edl.json, edl_b.json, words.out.json, notes
├── renders/       drafts and proxies; verify/ holds evidence frames
├── exports/       what is delivered: video, SRT, project archive
└── project.md     decisions and state
```

- Use stable, plain file names: `take_01.mp4`, `screen_02.mov`, `music_bed.wav` (`MED007`).
- A skill or engine may make its own folders (video-use writes into `edit/`; HyperFrames makes a project).
  Keep its layout and record where it is.
- Keep keys out of the folder or in a file Git ignores (`data-and-licences.md`).

## Brief

Write the brief before the first cut.
Ask for what is missing; do not guess the audience or the length.

- **Viewer and takeaway:** who watches, and the one thing they should understand or do at the end.
- **Delivery:** duration, width × height, frame rate, language, captions burned in or as a file, loudness target.
- **Must stay:** facts, phrases, disclaimers and names that cannot be cut or reworded.
- **Must not happen:** things that cannot be cut, reordered or shown (faces, client data, unreleased features).
- **References:** one or two videos with the wanted pace, and what exactly to take from each.
- **Cloud:** which material may leave the machine, to which service, and the budget.
- **Handoff:** the files and the editable project to deliver.

## project.md

Keep it current; a long chat history does not replace a clear list of decisions.

```markdown
# <Project>

## Goal
Viewer, takeaway, delivery (duration, size, fps, language, loudness).

## State
Approved EDL: edit/edl_v2.json (2026-10-15) · Last good render: renders/draft_v3.mp4
Next two steps: …

## Decisions (do not change without the author)
- Opening uses take 2 (CUT-03).
- The price is said, never shown on screen.

## Sources and conversions
| Source | Working copy | Conversion | Why |
| --- | --- | --- | --- |

## Design rules
Fonts (with licence), colours, caption style, safe zones.

## Tools
Versions from toolchain_report.py, transcription tool and settings, engine and its version.

## Commands that work
Preview, draft render, final render, QA scan.

## Assets and licences
| Asset | Source | Author | Licence | Proof |
| --- | --- | --- | --- | --- |

## Open questions and known defects
```

## Handing over to another agent

Write the handoff into `project.md`, not into the chat:
the goal, the approved EDL and its version, the last good render,
preview and render commands, the asset list, the tools and models used,
open defects with output times,
the decisions that need the author,
and the next two actions.
Keep the source-to-output table (`edl.py table`) with it.
