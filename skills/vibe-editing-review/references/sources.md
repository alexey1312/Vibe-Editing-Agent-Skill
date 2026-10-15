# Sources

Cite the page, the repository file, or the measurement a recommendation rests on;
`measured-behavior.md` for what this repository measured;
`versions.md` for anything with a version, a price, a size or a star count.
Everything was read on 2026-10-15 at the revisions below.
Quotes are one sentence at most; everything else is paraphrased.

## Documentation and norms

| Source | URL | Backs |
| --- | --- | --- |
| FFmpeg filters | <https://ffmpeg.org/ffmpeg-filters.html> | `silencedetect`, `blackdetect`, `freezedetect` defaults (−60 dB / 2 s; d 2.0, pic_th 0.98, pix_th 0.10); `ebur128` true peak; `loudnorm` defaults I −24, LRA 7, TP −2 and two-pass `measured_*`; `afade`, `acrossfade`, `sidechaincompress`; concat needs the same parameters; `subtitles` needs libass; `drawtext` needs libfreetype and libharfbuzz |
| FFmpeg tool | <https://ffmpeg.org/ffmpeg.html> | `-ss` on input seeks to the seek point before the position; the extra part is kept with stream copy and decoded and discarded when transcoding (`-accurate_seek`, on by default) |
| FFmpeg formats | <https://ffmpeg.org/ffmpeg-formats.html> | concat demuxer: `inpoint` works best with intra-frame codecs; same streams in all files |
| FFmpeg legal | <https://ffmpeg.org/legal.html> and `LICENSE.md` | LGPL 2.1 or later; GPL with `--enable-gpl`; `--enable-nonfree` makes a binary unredistributable |
| Netflix Russian Timed Text Style Guide (updated 2025-12-19) | <https://partnerhelp.netflixstudios.com/hc/en-us/articles/215346638-Russian-Timed-Text-Style-Guide> | 42 characters per line; two lines; 17 cps adult, 13 children, SDH 20 and 17; bottom-heavy line pairs; keep bound phrases together |
| Netflix General Requirements | <https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements> | 5/6 s minimum and 7 s maximum per event; one line unless too long; break after punctuation, before conjunctions and prepositions |
| Netflix Subtitle Timing Guidelines | <https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines> | at least 2 frames between events |
| BBC Subtitle Guidelines (March 2026) | <https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/> | 37 characters broadcast; about 25 characters and up to three lines for 9:16; 160–180 words per minute; break at linguistic boundaries |
| EBU R 128-2023 | <https://tech.ebu.ch/docs/r/r128.pdf> | −23 LUFS target; true peak ≤ −1 dBTP |
| Apple Podcasts audio requirements | <https://podcasters.apple.com/support/893-audio-requirements> | −16 LKFS ± 1 dB; true peak ≤ −1 dBFS |
| Spotify for Artists: loudness normalization | <https://support.spotify.com/us/artists/article/loudness-normalization/> | −14 LUFS; true peak below −1 dB, or −2 dB for masters louder than −14 |
| YouTube Help 1722171, 14106294, 16619284 | <https://support.google.com/youtube/answer/14106294> | no published loudness target; "stable volume" on the viewer side only |
| Meta Ads Guide: Instagram Reels | <https://www.facebook.com/business/ads-guide/update/video/instagram-reels> | ads: keep 14 % top, 35 % bottom, 6 % each side free of text and logos |
| Google Ads: About video ad specs | <https://support.google.com/google-ads/answer/13547298> | ads: vertical safe zone drawn as 288 / 672 / 192 / 48 px on 1080×1920 (edges read from the drawing) |
| TikTok Ads: In-Feed Ads | <https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads> | safe zones only as downloadable files; no numbers in text |
| HyperFrames: captions and recuts | <https://hyperframes.heygen.com/guides/captions-and-recuts> | `embedded-captions` adds words, `talking-head-recut` adds graphics; neither changes the footage; pauses and reordering go to General Video |
| Remotion: coding agents | <https://www.remotion.dev/docs/ai/coding-agents> | `npx create-video --yes --blank`, `npx remotion skills add`; works with Claude Code and Codex |
| Remotion: `<Video>` (`@remotion/media`), `<OffthreadVideo>` | <https://www.remotion.dev/docs/media/video>, <https://www.remotion.dev/docs/offthreadvideo> | `trimBefore` and `durationInFrames` in frames; `trimAfter`, `startFrom`, `endAt` deprecated |
| Remotion: `useCurrentFrame`, `renderMedia` | <https://www.remotion.dev/docs/use-current-frame>, <https://www.remotion.dev/docs/renderer/render-media> | time as a frame number; `frameRange` renders a part |
| GSAP Standard License (modified 2025-05-30) | <https://gsap.com/community/standard-license/> | AI-generated code is not a prohibited use; the restriction is on no-code visual builders that compete with Webflow |

## Repositories

Linked, pinned and never copied.

| Repository | Revision | Licence | Backs |
| --- | --- | --- | --- |
| [browser-use/video-use](https://github.com/browser-use/video-use/tree/43cfc566833548093455c9d4a46bd69913b7e552) | `43cfc56` | MIT | transcribe → pack → plan → EDL → render → self-check; approval before cutting; ElevenLabs Speech-to-Text is the only recogniser (mono 16 kHz WAV, `ELEVENLABS_API_KEY`); `timeline_view` filmstrip with waveform and words; silences ≥ 400 ms as cut candidates (figure) and "usually the cleanest" (`SKILL.md`); 30–200 ms padding; 30 ms fades; cuts not snapped to frames; `SKILL.md` must stay next to `helpers/` |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes/tree/76222e41d7760f94426484ceb9f76d0007813fcc) | `76222e4` | Apache-2.0 | Node.js 22+ and FFmpeg; `init` / `preview` / `render`; plugin `hyperframes@hyperframes`; security reports through a private advisory; clip timing `data-start`, `data-duration`, `data-media-start`; sound on the `<video>` with `data-has-audio` |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion/blob/dba10e61a8971220c6dc83ebef379e0d3bf87525/LICENSE.md) | `dba10e6` | Remotion License (custom) | free for individuals, non-profits and companies of up to three; a company licence from four |
| [remotion-dev/skills](https://github.com/remotion-dev/skills/tree/7ba4dcf8ebe1626b00baa41e1f2478113719b60b) | `7ba4dcf` | none detected | the twelve `remotion-*` skill names |
| [bradautomates/claude-video](https://github.com/bradautomates/claude-video/tree/03ceb42f7fa2c4439aca01752118044baabffb8f) | `03ceb42` | MIT | skill `watch`: understands video, does not edit it; `auto` uses Gemini when `GEMINI_API_KEY` resolves and uploads the whole file to the Files API; `--engine local`; never switches engines by itself |
| [getopenscreen/openscreen](https://github.com/getopenscreen/openscreen/tree/1b7ed86dddde03f5aa5c9e58d8791973091ee888) | `1b7ed86` | MIT | screen recording with zooms; cut by deleting transcript text; on-device captions; assistant off until a user key is added; `openscreen-demo` skill over MCP |
| [m-bain/whisperX](https://github.com/m-bain/whisperX/tree/771b4a14a9486f8fd5aef18ef49e35d639523dd3) | `771b4a1` | BSD-2-Clause | word times by forced alignment; Russian default alignment model; diarization with a token and a gated CC-BY-4.0 model; overlapping speech handled poorly; numbers without word times |
| [pyannote/pyannote-audio](https://github.com/pyannote/pyannote-audio/tree/b749285c5cdd4636b2edc7f766f1352c8dde9369) | `b749285` | MIT (model CC-BY-4.0) | speaker labels `speaker_0`…; gated model; telemetry on by default (`metrics_enabled: true`) |
| [Softcatala/whisper-ctranslate2](https://github.com/Softcatala/whisper-ctranslate2/tree/78ae8efaca4b8de6fd41ef0f47b789fcdd0e2555) | `78ae8ef` | MIT | `--word_timestamps True`, `--vad_filter True`, srt and json output |
| [senstella/parakeet-mlx](https://github.com/senstella/parakeet-mlx/tree/2d9748c04aca31405274a13c20ef9b62f1a73351) | `2d9748c` | Apache-2.0 (model CC-BY-4.0) | default model `parakeet-tdt-0.6b-v3`, whose NVIDIA card lists Russian; local attention and chunking for memory |
| [Blaizzy/mlx-audio](https://github.com/Blaizzy/mlx-audio/tree/dad2087f790dfe96b07d5aac1405db4b578b411f) | `dad2087` | MIT | speech recognition, synthesis and speech-to-speech on Apple silicon; a forced aligner |
| [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor/tree/44bf4ec3dfffdd1bb5410b06dc9f0365d8f6bbbc) | `44bf4ec` | Unlicense | cuts by loudness, motion, black frames, subtitle text or words; `--margin` default 0.2 s; exports to Premiere, Resolve, Final Cut Pro, Shotcut, Kdenlive, no EDL |
| [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | `8973412` | Unlicense | downloads media; rights are a separate question |

## Background reading

Not cited as evidence; useful for context.

- *Вайб-монтаж с AI-агентами. Большой практический гайд* — Telegram channel «Точки над ИИ», 2026-10-15, 79 pages.
  The survey of routes, prompts and tools that this repository started from.
  It is not open-licensed: nothing is copied from it,
  and each claim taken from it was checked against the primary sources above.
- Jonny Burger (Remotion), a public post on editing a video with Claude Code:
  <https://www.linkedin.com/posts/jonny-burger-4115109b_this-is-vibe-editing-i-used-only-claude-activity-7440428270405345280-eBbx>.
- A practitioner on the limits of AI editing (r/ClaudeAI):
  <https://www.reddit.com/r/ClaudeAI/comments/1wu1i58/video_editing_and_creating_effective_systems_for/>.
- A screen recording edited with Claude Code and HyperFrames, with a second pass (r/SideProject):
  <https://www.reddit.com/r/SideProject/comments/1wob9n9/claude_code_hyperframes_turned_a_raw_screen/>.
- The Remotion prompt gallery: <https://www.remotion.dev/prompts/>;
  HyperFrames showcase: <https://hyperframes.heygen.com/showcase>.
