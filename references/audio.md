# Sound

Viewers forgive a soft picture sooner than bad sound.
Build the speech first, then music, then effects.

## Three layers

| Layer | Job | Check |
| --- | --- | --- |
| Speech | clear, even in perceived loudness, no clipped consonants | every join; headphones and a phone speaker |
| Music | keeps the pace and leaves room for the voice | it drops under speech and returns in pauses |
| Effects | mark an action: a click, an appearance, a scene change | only on actions that mean something |

## Joins

- Every join gets a short fade out and in; `edl.py render` uses 10 ms by default
  (*Measured* M3: without fades the join makes a step 14 times steeper than the tone itself).
- A long crossfade can lay two words on top of each other; choose its length by ear.
- Listen to the start and end of every track: a cut breath, a click, a tail of room noise.
- Never synthesise a missing word into the speech without the author's separate decision.

## Music under speech (ducking)

The music fades down before the voice starts, stays down while it speaks,
and comes back up smoothly in the pauses.
Too fast a movement is audible; set the speed on the real material, with the voice.

- In HyperFrames, the `hyperframes-audio` skill owns ducking ("voiceover carve") and automation.
- In FFmpeg, `sidechaincompress` lowers one input by the level of another;
  its defaults (`threshold` 0.125, `ratio` 2, `attack` 20 ms, `release` 250 ms) are a starting point, not a mix.
- Check one full phrase: the start of the first word, the end of the last, and the music returning.

## Loudness

Measure the final mix, then normalise to the target the brief names.

| Target | Integrated | True peak | Source |
| --- | --- | --- | --- |
| Broadcast (EBU R 128) | −23 LUFS | ≤ −1 dBTP | EBU R 128-2023 |
| Apple Podcasts | −16 LKFS ± 1 dB | ≤ −1 dBFS | Apple Podcasts audio requirements |
| Spotify (music) | −14 LUFS | below −1 dBTP; below −2 dBTP if the master is louder than −14 | Spotify for Artists |
| YouTube | no published target | — | YouTube Help documents only a viewer-side "stable volume" |

- FFmpeg's `ebur128` documentation notes that online material may prefer −16 LUFS.
  With no target in the brief, ask; do not assume a number for YouTube.
- `loudnorm` defaults to −24 LUFS, LRA 7 and −2 dBTP — not any of the targets above.
  Always set `I`, `TP` and `LRA` explicitly, and use two passes for a file:
  measure first, then pass the `measured_*` values to the second run.
- Measure with `qa_scan.py --loudness-target <LUFS> --true-peak-max <dBTP>`;
  lossy encoding can push true peaks up, so measure the delivered file, not the mix.

## Synthetic voice

- Use a voice you are allowed to use; record the provider and the terms in `project.md`.
- Check stress, names and numbers by ear in the target language.
- Lock the approved voice file before timing scenes to it;
  a new generation changes every duration after it.
- A free tier can let the provider use the text; choose test text accordingly.

## Licences

Code under MIT and sounds under CC0 are different licences for different things.
For every music track and sound effect, record where it came from, who made it, and the terms (`data-and-licences.md`).
