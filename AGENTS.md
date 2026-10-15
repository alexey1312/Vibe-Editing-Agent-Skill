# Agent guidance

This repository contains Agent Skills that cut recorded footage by conversation
and review the rendered video before it ships.
They work next to the HyperFrames and Remotion skills, not instead of them:
those own composition code; these own the editorial decisions, the timeline maths and the checks.

- **Phase 1 stays read-only.**
  `toolchain_report.py`, `media_probe.py`, `qa_scan.py`, `edl.py check|table|cuts|map|candidates`
  and `captions.py check` never write to a project;
  `test_read_only_scripts_never_open_files_for_writing` and the toolchain report's command allowlist guard them.
  Rendering, retiming, uploading media, cloud transcription and installs are Phase 2 changes that need approval.
- **Originals are never written.**
  `edl.py render` and `edl.py retime` refuse to write over a source or an existing file without `--force`.
- **Every rule cites a source.**
  A rule in `CHECKS.md` names a documentation page, a norm (Netflix, BBC, EBU),
  a measured section (`measured-behavior.md` M<n>), or says *inference*.
- **Only the probes measure.**
  A statement is *Measured* only if `scripts/probes/ffmpeg_probes.py` (or, for M7, the toolchain report)
  produced it and `references/measured-behavior.md` records it under `Status: measured`;
  a test enforces it, and CI re-runs the probes every week.
- **Shared files have one source.**
  Edit `references/*.md` and the five scripts at the root,
  then run `python3 scripts/sync_skill_copies.py`; never edit the copies inside `skills/`.
- **Versions live in one place.**
  Every version, price, licence threshold and star count goes in `references/versions.md`
  with the date it was checked and how to re-check it.
  SKILL.md bodies and eval expectations carry no version numbers (a test checks both).
- **The engines' skills own the engines.**
  Route composition code to the HyperFrames skills (`hyperframes`, `general-video`, `hyperframes-core`)
  or Remotion's (`remotion-best-practices`), and captions or overlays on unchanged footage
  to `embedded-captions` or `talking-head-recut`, by name.
  A test checks that every skill named in a description exists.
- **Licences.**
  Paraphrase documentation; quote at most one attributed sentence.
  The guide this repository started from is not open-licensed: nothing is copied from it,
  and it is listed only under *Background reading*.
  Do not copy third-party code; link it pinned to a commit.
- **No model ids, no local paths, no keys** in any file.
  Commands name models through `$AGENT_MODEL` and `$JUDGE_MODEL`; a test enforces it.
- **Script changes need tests** for a positive and a negative case, and a row in `CHECKS.md`.
- **Behaviour changes need evals.**
  Each skill keeps skill-creator evals in `skills/<skill>/evals/`
  (`evals.json`, fixtures under `files/`, media generators under `media/`, and `trigger-evals.json`).
  Fixtures hold text only; `media/*.sh` makes the media with FFmpeg when a case is staged.
  `scripts/package_skills.py` leaves `evals/` out of release archives.
- **Keep SKILL.md descriptions between 200 and 1024 characters**,
  starting with "Use this skill when" and naming what the skill is not for;
  `name` equals the directory name.
- **Write English in Simplified Technical English**, and Markdown with semantic line breaks:
  one sentence per line, breaks at clause boundaries, never inside code, tables or frontmatter.
- Keep the plugin version identical in `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`, `.cursor-plugin/plugin.json` and `agents/openai.yaml`.
  A GitHub release is cut by pushing a matching `vX.Y.Z` tag.
- Run before completing a change:

  ```bash
  python3 scripts/sync_skill_copies.py --check
  python3 -m unittest discover -s tests -v
  python3 scripts/probes/ffmpeg_probes.py --check --format markdown
  ```
