# Contributing

Thanks for helping keep these skills accurate.
Video tools move fast — FFmpeg, HyperFrames, Remotion and the recognisers ship every few weeks —
so the most valuable contributions are re-checks and new measurements.

## Good contributions

- **Re-checked versions.**
  Every row of `references/versions.md` says when it was checked and how to re-check it.
  Update the value and the date together.
- **Measurements.**
  A new probe in `scripts/probes/ffmpeg_probes.py` with its expectation in `expectations.json`
  and a section in `references/measured-behavior.md` turns a cited claim into a measured one.
  Probes make their own media with lavfi; never commit media files.
- **Script rules.**
  Add the rule to the script, a positive and a negative test,
  and a row in `CHECKS.md`; then run `python3 scripts/sync_skill_copies.py`.
- **False positives** found on real footage, with the `media_probe.py --format json` output
  (no media needed).
- **Evals** for behaviour the skills get wrong:
  a case in `skills/<skill>/evals/evals.json` with a text fixture and, if it needs media,
  a generator in `skills/<skill>/evals/media/`;
  or a query in `trigger-evals.json`.
  Requests that belong to the HyperFrames or Remotion skills make good negatives.

## Rules

- Guidance traces to official documentation, a published norm, a repository file pinned to a commit,
  or a probe. Label anything else as *inference*.
- Third-party code is linked, pinned to a commit, never copied.
- No third-party Python dependencies; the scripts run on the Python that ships with macOS.
- No model ids, local paths or keys in any file.

## Evaluating a change

The skills are developed with Anthropic's
[skill-creator](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator):
run each eval with and without the skills, grade the expectations,
and read the outputs before trusting a score.
Trigger accuracy is tuned with its `run_loop` against `trigger-evals.json`
(run it with one worker: parallel workers share one commands directory and report false negatives).
Keep workspaces outside the repository (`*-workspace/` is ignored).

`scripts/build_plugin_evals.py` stages the plugin without `evals/` (the expectations are the answer key)
and writes one `claude plugin eval` case per eval.
Each case's scaffold copies the text fixture and then runs its media generator,
which stays outside the workspace because it names the planted defects.
FFmpeg must be on the machine that runs the evals.

```bash
python3 scripts/build_plugin_evals.py "$TMPDIR/ve-plugin-eval"
claude plugin eval "$TMPDIR/ve-plugin-eval" --trust-plugin --scaffold \
  --allow-tools Bash Edit Write --model "$AGENT_MODEL" --judge-model "$JUDGE_MODEL" \
  --no-publish --max-cost-usd 10 --json "$TMPDIR/ve-plugin-eval.json"
```

Set `AGENT_MODEL` to the model under test and `JUDGE_MODEL` to the grader,
and keep both fixed across runs you compare.
`--no-publish` keeps the HTML report local.
The runner's `costUsd` leaves out the judge, so set `--max-cost-usd` to about two thirds of the real budget.
Use `--only <case>` for a pilot.
With the HyperFrames skills installed at user scope, both arms load them;
say so when you report a result.

## Checks

```bash
python3 scripts/sync_skill_copies.py --check
python3 -m unittest discover -s tests -v
python3 scripts/probes/ffmpeg_probes.py --check --format markdown
python3 scripts/toolchain_report.py --format markdown
```

## Releasing

1. Bump the version in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
   `.cursor-plugin/plugin.json` and `agents/openai.yaml` (the tests check they agree)
   and merge it to `main`.
2. Tag that commit and push the tag:

   ```bash
   git tag v1.0.0 && git push origin v1.0.0
   ```

The `Release` workflow refuses a tag that does not match the plugin version,
re-runs the tests, builds one `.skill` archive per skill with
`scripts/package_skills.py`, and publishes a GitHub release.
