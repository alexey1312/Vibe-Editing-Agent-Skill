# Transcripts

The agent edits speech through text:
it reads the words and their times, and decides where to cut.
Frames show what the text cannot — a gesture, a covered face, the interface —
and the waveform shows pauses, breaths and clicks.

## What the edit needs

- **Word timestamps**, not only sentence timestamps: cuts happen between words.
- **One file per source**, kept in `transcripts/`, made once and reused.
- **A glossary** (`transcripts/glossary.txt`): names, brands, terms and numbers as they must appear.
- **Speakers** when there are several voices; diarization labels them as speaker 0, 1, …,
  not by name, and it makes mistakes when people talk over each other.

`edl.py` reads word lists from WhisperX and Whisper-style JSON (`segments[].words[]`),
ElevenLabs Speech-to-Text JSON (`words[]` with `type`; spacing and audio events are skipped),
or a plain list of `{"word", "start", "end"}`.

## Choosing a recogniser

Choose by language, privacy and machine, and test on two minutes of the real material first:
accuracy on the speaker's language, accent and noise decides more than any feature list.

| Tool | Runs | Word times | Notes |
| --- | --- | --- | --- |
| ElevenLabs Speech-to-Text | cloud, paid | yes, with speaker labels and audio events | the only recogniser video-use supports; it uploads a mono 16 kHz WAV of one audio track |
| WhisperX | local (CPU on macOS) | yes, by forced alignment | Russian has a default alignment model; diarization needs a Hugging Face token and accepting a gated model's terms |
| whisper-ctranslate2 | local | `--word_timestamps True` (experimental) | `--vad_filter True` skips non-speech; outputs srt and json |
| parakeet-mlx | local, Apple silicon | yes | its default model's card lists Russian; model weights are CC-BY-4.0 |
| MLX Audio | local, Apple silicon | yes (a forced aligner is included) | also speech synthesis |
| auto-editor `whisper` | local (whisper.cpp) | text, srt or json | auto-editor itself cuts by loudness or motion, not by meaning |

Sources and the revisions read: `sources.md`; versions: `versions.md`.

- WhisperX gives no word time to tokens its alignment model cannot spell,
  such as "2014." or "£13.60";
  check numbers by ear around such words.
- Local recognition keeps the audio on the machine;
  a cloud agent still sees the text it reads (`data-and-licences.md`).
- Installing a recogniser, downloading a model or sending audio to a service waits for approval.
  `toolchain_report.py` says what is already on the machine and which key names are set.

## Checking the transcript

1. Read it against the recording at the start, the end and around every number and name.
2. Mark words the recogniser was unsure of; listen to each before planning a cut there.
3. Apply the glossary; keep a list of what was corrected.
4. Keep the corrected file as the source of truth for captions.

## Seeing the material

- Get the metadata (`media_probe.py`), the transcript with word times,
  a few overview frames per source, and detailed frames around every planned join.
- Sparse frame sampling can miss a flash or a short transition;
  for those, watch the range itself or sample more densely.
- Pick frames by exact time with a decode, not with a stream copy (*Measured* M2):
  `ffmpeg -ss <time> -i work/take_02.mp4 -frames:v 1 renders/verify/take_02_<time>.png`.
- Show the author a strip of frames, the waveform and the words around a doubtful join
  before deciding where it goes.
