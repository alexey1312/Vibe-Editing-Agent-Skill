# Versions, prices and counts

Everything here changes; every row says when it was checked and how to check it again.
SKILL.md files carry no version numbers; they point here.

## Tools and requirements

| Item | Value | Checked | Re-check |
| --- | --- | --- | --- |
| FFmpeg used for the measurements | 9.0.2 (Homebrew `ffmpeg` 9.0.2_1, macOS 27, Apple silicon) | 2026-10-15 | `ffmpeg -version` |
| Homebrew FFmpeg with libass and freetype | formula `ffmpeg-full` (47 dependencies; `ffmpeg` has 11) | 2026-10-15 | `brew info --json=v2 ffmpeg ffmpeg-full` |
| HyperFrames requirements | Node.js 22+, FFmpeg | 2026-10-15 | README § Manually with the CLI |
| HyperFrames revision read | `76222e4` | 2026-10-15 | `gh api repos/heygen-com/hyperframes/commits/HEAD --jq .sha` |
| HyperFrames audio on cut footage | sound stays on `<video>` with `data-has-audio="true"`; a separate `<audio>` for music, voice-over and J/L cuts (copies installed before this change use a muted `<video>` plus `<audio>`) | 2026-10-15 | upstream `skills/hyperframes-core/references/data-attributes.md` |
| Remotion release | v4.0.535 (2026-10-12) | 2026-10-15 | `gh api repos/remotion-dev/remotion/releases/latest --jq .tag_name` |
| Remotion `trimBefore` | current, frames, from 4.0.319 (renamed from `startFrom`) | 2026-10-15 | `/docs/offthreadvideo` |
| Remotion `durationInFrames` on a video | current, source frames; from 4.0.446 on `@remotion/media` `<Video>`, 4.0.530 on `<OffthreadVideo>` | 2026-10-15 | `/docs/media/video` |
| Remotion `trimAfter` | deprecated in favour of `durationInFrames` (PR #11685, merged 2026-09-26) | 2026-10-15 | `/docs/offthreadvideo` |
| Remotion licence | free for individuals, non-profits and companies of up to 3; company licence from 4 people or collaborations of 4+ | 2026-10-15 | `LICENSE.md`; <https://www.remotion.dev/docs/license/pricing> |
| Remotion skills | 12 skills named `remotion-*`, installed by `npx remotion skills add` from `remotion-dev/skills` | 2026-10-15 | `packages/cli/src/skills.ts` |
| video-use revision read | `43cfc56`; Python 3.10+ | 2026-10-15 | `pyproject.toml` |
| claude-video (`watch`) | 0.3.2; Python 3.10+ | 2026-10-15 | `skills/watch/SKILL.md` |
| WhisperX | v3.8.6 (2026-05-25) | 2026-10-15 | GitHub releases |
| pyannote.audio | 4.0.7 (2026-06-30) | 2026-10-15 | GitHub releases |
| MLX Audio | v0.5.9 (2026-10-13) | 2026-10-15 | GitHub releases |
| parakeet-mlx default model | `mlx-community/parakeet-tdt-0.6b-v3` | 2026-10-15 | README § Options |
| auto-editor | 31.7.2 (2026-10-03); website reference shows 31.6.1 | 2026-10-15 | GitHub releases |
| Netflix Russian line length | 42 characters (raised on 2025-12-19) | 2026-10-15 | Netflix Russian guide, change log |
| BBC Subtitle Guidelines | version shown as ".1.2.5", March 2026 | 2026-10-15 | page header |
| EBU R 128 | R 128-2023 (V5, November 2023) | 2026-10-15 | <https://tech.ebu.ch/docs/r/r128.pdf> |

## Repositories

Stars measure attention, not safety.

| Repository | Licence | Stars | Last push | Checked |
| --- | --- | --- | --- | --- |
| yt-dlp/yt-dlp | Unlicense | 197 996 | 2026-10-10 | 2026-10-15 |
| mrdoob/three.js | MIT | 116 449 | 2026-10-15 | 2026-10-15 |
| OpenCut-app/OpenCut | MIT | 94 655 | 2026-09-24 | 2026-10-15 |
| FFmpeg/FFmpeg | LGPL-2.1-or-later; GPL with `--enable-gpl` | 65 218 | 2026-10-15 | 2026-10-15 |
| remotion-dev/remotion | Remotion License | 64 326 | 2026-10-15 | 2026-10-15 |
| heygen-com/hyperframes | Apache-2.0 | 64 296 | 2026-10-15 | 2026-10-15 |
| ManimCommunity/manim | MIT | 41 553 | 2026-10-12 | 2026-10-15 |
| greensock/GSAP | Standard "no charge" GSAP License | 29 258 | 2026-04-13 | 2026-10-15 |
| browser-use/video-use | MIT | 29 004 | 2026-10-08 | 2026-10-15 |
| m-bain/whisperX | BSD-2-Clause | 24 570 | 2026-09-26 | 2026-10-15 |
| bradautomates/claude-video | MIT | 18 603 | 2026-09-25 | 2026-10-15 |
| wheresryan22/anatomy | MIT | 12 364 | 2026-10-15 | 2026-10-15 |
| pyannote/pyannote-audio | MIT | 10 652 | 2026-10-07 | 2026-10-15 |
| Blaizzy/mlx-audio | MIT | 8 049 | 2026-10-14 | 2026-10-15 |
| WyattBlue/auto-editor | Unlicense | 5 526 | 2026-10-14 | 2026-10-15 |
| getopenscreen/openscreen | MIT | 4 356 | 2026-10-15 | 2026-10-15 |
| Softcatala/whisper-ctranslate2 | MIT | 1 361 | 2026-10-05 | 2026-10-15 |
| academa-labs/manimgx | MIT | 1 348 | 2026-10-15 | 2026-10-15 |
| senstella/parakeet-mlx | Apache-2.0 | 987 | 2026-10-01 | 2026-10-15 |
| Bodila51/opus-sound-layer | MIT | 51 | 2026-10-10 | 2026-10-15 |

Re-check a row with
`gh api repos/OWNER/REPO --jq '{l:.license.spdx_id,s:.stargazers_count,p:.pushed_at,a:.archived}'`.
None of the twenty was archived on 2026-10-15.
