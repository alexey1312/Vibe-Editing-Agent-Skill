# Benchmark — 2026-10-15

Nine cases, run with `claude plugin eval` on plugin version **1.0.0** (commit `6e5ca5f`),
Claude Code 2.1.300.
Each case ran three times with the skills and three times without them (`--ablation with-without`),
four runs in parallel, three judge votes per criterion.
One agent model and one judge model, both fixed for the whole run.
1006 s, **$33.70** — $22.33 for the agents and $11.36 for the judge —
after a one-run pilot that cost $11.46.

```bash
python3 scripts/build_plugin_evals.py "$TMPDIR/ve-plugin-eval"
claude plugin eval "$TMPDIR/ve-plugin-eval" --trust-plugin --scaffold \
  --allow-tools Bash Edit Write --model "$AGENT_MODEL" --judge-model "$JUDGE_MODEL" \
  --runs 3 -j 4 --no-publish --max-cost-usd 30
```

`full.json` and `pilot.json` are the runner's results reduced by `scripts/strip_eval_result.py`:
scores, every judge vote, turns and cost per run — no transcripts, local paths or model ids.

| Case | Without the skills | With the skills | Δ |
| --- | --- | --- | --- |
| `review--youtube-loudness` | 0.53 (0/3) | **0.93** (2/3) | **+0.40** |
| `cut--plan-cut-from-two-takes` | 0.67 (0/3) | **1.00** (3/3) | **+0.33** |
| `cut--captions-only-route` | 0.73 (0/3) | **1.00** (3/3) | **+0.27** |
| `review--review-before-publish` | 0.88 (0/3) | **1.00** (3/3) | **+0.12** |
| `cut--retime-captions-after-cut` | 0.89 (0/3) | **1.00** (3/3) | **+0.11** |
| `cut--podcast-clips` | 0.83 (1/3) | **0.89** (1/3) | **+0.06** |
| `cut--stream-copy-extra-second` | 1.00 (3/3) | 1.00 (3/3) | 0 |
| `review--captions-drift-diagnosis` | 1.00 (3/3) | 1.00 (3/3) | 0 |
| `review--handoff-to-another-agent` | **1.00** (3/3) | 0.96 (2/3) | −0.04 |
| **Mean** | 0.837 | **0.976** | **+0.14** |
| **Runs passing every criterion** | 10 of 27 | **23 of 27** | |

Scores are the mean share of criteria passed; the count is runs that passed every criterion.

## Where the skills made the difference

- **YouTube loudness.** Without the skills, no run said that YouTube publishes no loudness target
  (the one pilot answer read in full called −14 LUFS the "typical YouTube target").
  With the skills, every run said so and offered −14 or −16 LUFS as references the author chooses.
- **Planning a cut from two takes.** Without the skills, no run passed:
  they missed the loading wait in the screen recording, did not lay out what the cut drops for approval,
  or (two of three) did not find the variable frame rate and the rotated take from the media itself.
- **Captions only.** Without the skills, no run asked where the audio goes for speech recognition.
- **Review before publishing.** Without the skills, all three reviews found the planted defects
  but none listed what a scan cannot check, or asked for a full viewing with sound.
- **Retiming captions.** Without the skills, the captions came out right,
  but no run checked the result against the cut.

## Read the failures before citing these numbers

- **Three cases do not discriminate.**
  `stream-copy-extra-second`, `captions-drift-diagnosis` and `handoff-to-another-agent`
  scored 1.00 without the skills; the base model already knows these.
  They stay as checks that the skills do no harm.
- **The handoff miss is a fixture defect, and the agent was right.**
  The generated `draft_v2.mp4` and `draft_v3.mp4` were byte-identical and 2 s long,
  while the notes put defects at 00:18.6 and 00:31.
  One run with the skills noticed, kept `draft_v3` as "last render per the notes" with a warning,
  and the judge failed it for not calling `draft_v3` the last good render.
  The fixture is fixed after this run (`media/Launch.sh` now makes two different, longer drafts).
- **One loudness miss is a judge error.**
  The run proposed a plain +12.2 dB gain with the target and the resulting true peak stated;
  the criterion asked for explicit targets "for example two-pass loudnorm",
  and the judge read the example as a requirement.
  The criterion is reworded after this run.
- **The podcast criterion e01 is strict for both arms.**
  It wants the source times, the point and the risk for *each* clip;
  runs that discussed the risks in prose rather than per clip failed it, with the skills and without.
- **The base model is strong.**
  It found most planted defects and kept the brief's caveats without the skills;
  the gains are in what it does not know (published norms, what a scan cannot see)
  and in process (approval, data leaving the machine, checking its own output).

## What the pilot changed

The pilot (one run per arm, `pilot.json`) scored 0.954 with and 0.824 without.
Reading its failures changed the cases, not the skills (commit `6e5ca5f`):

- The synthetic takes had a constant tone while the transcripts had pauses,
  and the agent rightly doubted the material;
  the tone now sounds only on the transcript's words, and the briefs say the media are stand-ins.
- The plan case was graded on the final message while the agent put the plan in `plan.md`;
  the prompt now asks for the plan in the reply.
- Two criteria accepted only one way to solve the case; they now accept every correct one.

## Not measured

- **Skill loading in the full run.** Traces were not kept.
  In the pilot, the skills loaded in seven of nine runs with them:
  not in `captions-only-route`, where the work belongs to a captions workflow,
  and not in `handoff-to-another-agent`, which scored 1.00 anyway.
- **Next to the HyperFrames skills.** Neither arm had them:
  the eval sandbox loaded only built-in skills.
  How the descriptions compete with the HyperFrames router is not measured.
- **Trigger accuracy.** `trigger-evals.json` was not run.
