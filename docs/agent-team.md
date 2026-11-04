# Agent team: how the dataset-benchmarking analysis is improved between meetings

A scheduled job runs every 6 hours. Each run takes **one** item from [`agent-backlog.md`](agent-backlog.md), carries it through three roles, and opens **one pull request**. Nothing is merged without a maintainer (Jordi Laguarta).

## Inputs the job needs
- The private EO-Arena project (claude.ai): `claude/agent-team/brief.md` (goal, frozen decisions, known pitfalls), `claude/agent-team/review-log.md`, the lab's scoring note `GeoFM_benchmark_score.pdf`, and the compact workbook archive `claude/workbook/workbook_v4_csv.tar.xz.b64`.
- The workbook is unpublished and the note is internal: **never commit either, or any individual score from the workbook, to this repository.** Code, summary statistics and values transcribed from published papers are fine. Rebuild the workbook outside the repo with `scripts/workbook_from_archive.py`.

## Base branch
`dataset-latent-analysis` (until it is merged into `main`; then `main`). Work branch per item: `agent/<item-id>-<short-slug>`.

## Claiming an item
Backlog statuses only change when a PR merges, so claims are made with branches. An item is **taken** if a remote branch `agent/<item-id>-*` exists. A run picks the first `open` item in the base branch's backlog with no such branch, and claims it by pushing an empty branch `agent/<item-id>-<slug>` from the base before doing any work. If the push is rejected, another run took it: pick the next item. When a maintainer closes a PR without merging, they delete its branch (GitHub offers this on the closed PR) so the item can be retried, or mark the item `blocked:` in the backlog.

## Roles (each a separate agent; the reviewer and verifier never see the implementer's reasoning, only the diff)
1. **Implementer.** Does the item on its own branch, in the smallest change that completes it. Rebuilds `data/dataset_analysis.json` and `docs/dataset-analysis.md` if the analysis or report is touched. Adds or updates tests in `tests/`.
2. **Spec reviewer.** Reads the brief and the scoring note, then the diff. Checks fidelity to the note's letter and spirit, the dataset-not-model goal, the frozen decisions and the known pitfalls, statistical soundness, and that every sentence in the report is stated at the evidential level it has. Returns blockers / majors / minors. Blockers go back to the implementer (at most two rounds); if still blocked, the PR is opened as a draft with the blockers listed.
3. **Verifier.** Reruns `python3 scripts/build_dataset_analysis.py <workbook dir>` and `python3 scripts/dataset_report.py` from a clean checkout of the branch, runs the tests, and runs `scripts/compare_headlines.py <base json> <branch json>`. Confirms the committed outputs equal the rerun and pastes the headline table into the PR.

## Guardrails
- **One item per run, one PR per item.** Label every PR `agent-team`.
- **Frozen decisions** (listed in the brief: inclusion rules, scale, model, K criterion, no reliability score without measured seed noise, no similarity without recoverability, no model ranking) are not changed by agents. An item that needs one changed becomes a PR labelled `needs-decision` that states the proposal and evidence, with no implementation.
- **Results.** If `compare_headlines.py` exits 3, label the PR `changes-results` and explain each changed headline. Never tune choices to move a headline; a change is justified only by the item's stated reason.
- **Back-pressure.** If three or more remote `agent/*` branches are not merged into the base branch, do not start a new item: refresh the oldest open PR (rebase on the base branch, rerun the verifier, answer review comments) or, if none needs work, stop and report.
- **Never** push to `main` or the base branch, force-push someone else's branch, merge a PR, delete branches you did not create, or touch the site's public pages outside an item that names them.
- If `gh` cannot create the PR, push the branch anyway and put the compare link (`https://github.com/thampatron/EO_Arena/compare/<base>...<branch>?expand=1`) and the PR text in the summary; the next run that has `gh` opens the PR.
- Each run ends with a short summary: item, PR link, headline changes, reviewer verdict, anything that needs Jordi.

## Backlog upkeep
The implementer marks the item `in PR #n` in `agent-backlog.md` within its own PR. New issues found during a run are appended to the backlog's *Proposed* section in the same PR; they are not worked on until a maintainer moves them up.
