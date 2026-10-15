# Notes from today (2026-10-15)

- The author approved edit/edl_v2.json at 14:10 (the price sentence moved after the demo).
- renders/draft_v3.mp4 is rendered from edl_v2 and is the last good render; draft_v2 is outdated.
- Preview: `npx hyperframes preview` in `composition/`.
- Draft render: `python3 scripts/edl.py render edit/edl_v2.json -o renders/draft_v4.mp4 --size 640x360 --preset veryfast`.
- QA: `python3 scripts/qa_scan.py renders/draft_v3.mp4 --width 1080 --height 1920 --fps 30 --edl edit/edl_v2.json`.
- Open defect: at 00:18.6 in draft_v3 the caption covers the Export button.
- Open defect: the music is too loud under the voice from 00:31 to 00:36.
- Not decided: whether the price is shown on screen or only said — the author must decide.
- Next: fix the caption position, then duck the music.
