# Data, licences and money

Decide where the media goes, which licences apply, and what each step costs
before the first upload, install or paid call.
Each of these is a Phase 2 action: it waits for the author's approval.

## Where the material can go

| Step | What can leave the machine | Decide before |
| --- | --- | --- |
| Cloud speech recognition | The audio track; some services take the whole file | provider, retention, price per minute, language support |
| video-use transcription | A mono 16 kHz WAV of one audio track, to ElevenLabs Speech-to-Text; there is no local path | a key, the cost, and that this audio may leave |
| claude-video (`watch`) with a Gemini key | The whole video file, through Google's Files API, deleted after the answer | `--engine local` when the file must stay; it never switches engines by itself |
| A cloud coding agent | Extracted frames, transcript text, file names and code | which folders the agent may read |
| An online editor or a video API | The media and the project | who in the workspace can see it; the service's terms |
| A local HTML or React render | Assets the composition loads by URL | keep assets local; check the network if the render must stay offline |

Sources for each row: `references/sources.md`.
Extracting frames locally does not make the whole process local:
a cloud agent still receives the frames and the text it reads.

- Use a short, anonymised clip to test a pipeline.
- Keep keys in the environment or in a file Git ignores, with owner-only permissions.
  Never print a key in the chat, a log or a report;
  `toolchain_report.py` lists key *names* only.
- A free tier can allow the provider to use the data; read the terms for the exact tier.

## Before installing a tool or a skill

1. Open the owner's repository from the official documentation; check the exact name and URL.
2. Read the licence, recent commits, open issues and the security policy.
3. Read the install script, the dependencies, any post-install step, and every network call.
4. Pin a release or a commit and the lock file; record the versions in `project.md`.
5. Run it first in a separate folder, on test media, with limited access.
6. Report to the author: commands it runs, files it reads, where media goes,
   keys it needs, and what it charges for.

Stars measure attention, and a recent push measures activity.
Neither proves the code is safe.
A new version of a skill can change the provider, the commands, the output layout or the access it needs:
test it again after every update.

## Three layers of licences

1. **Software:** the editor, the engine, the libraries.
   Remotion has its own licence (free up to three people, a company licence from four);
   HyperFrames is Apache-2.0;
   an FFmpeg binary is LGPL or GPL depending on how it was built
   (`toolchain_report.py` says whether this build has `--enable-gpl`).
   A licence the GitHub API cannot name (`NOASSERTION`, `null`) still has terms: read the file.
2. **Models and APIs:** access, allowed uses, how the provider treats the data.
3. **Material:** music, sound effects, fonts, images, voices, other people's footage.
   CC0 on a sound library's README does not prove the origin of each recording.
   A tool that downloads media (yt-dlp) does not grant the right to use it.

Record every asset with its source, author, licence and proof in `project.md`.

## Money and time

The cost of a delivered video is
agent + speech recognition + generated media + render + the author's review time,
including the attempts that failed.
Compare routes by the cost of an accepted video, not of one call.

- Transcribe each source once and keep the result in `transcripts/`.
- Approve the text and the cut before any graphics.
- Render only the range that has the problem, and draft at a lower size (`edl.py render --size`).
- Render the full-quality export after acceptance.
- Keep a log in `project.md`: task, version, time, paid calls, defects, decision.
