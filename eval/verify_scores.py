"""Check the saved scores: recompute every code check from the saved answers.

Needs no API key, no server, and no network. For each results folder written
by the harness, it scores each saved answer again with the same code checks
(facts, report lists, tool choice, citations, data date) against the gold set
in this repository, keeps the saved judge verdict, and reports whether each
question's pass or fail matches what was saved.

    uv run --group eval python eval/verify_scores.py                 # every run
    uv run --group eval python eval/verify_scores.py eval/results/2026-11-17-opus-5-5-s22-branch

The Orchestrate runs (eval/orchestrate/score_runs.py) keep one harness-format
records.json per run, and each is checked the same way. A folder in any other
format is listed as skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "phoenix"))
from scoring import load_gold, load_index, question_passed, score_code  # noqa: E402

RESULTS = Path(__file__).parent / "results"
CODE_FIELDS = (
    "checks",
    "exact_pass",
    "report_list",
    "tools_pass",
    "tools_called",
    "unknown_numbers",
    "unknown_urls",
    "citation_present",
    "data_date_stated",
)


def verify(folder: Path, gold: dict, numbers: set[str], urls: set[str]) -> str:
    path = folder / "records.json"
    try:
        records = json.loads(path.read_text())
        if not all(
            "run" in r and "score" in r and "judge" in r["score"] for r in records
        ):
            raise KeyError
    except (OSError, ValueError, KeyError, TypeError):
        return f"{folder.name}: skipped (not in the harness format)"
    differing = []
    passed = 0
    for record in records:
        question = gold.get(record["id"])
        if question is None:
            differing.append(f"{record['id']} (not in the gold set)")
            continue
        saved = record["score"]
        score = {**score_code(question, record["run"], numbers, urls)}
        score["judge"] = saved["judge"]
        same_code = all(score.get(k) == saved.get(k) for k in CODE_FIELDS)
        same_pass = question_passed(score) == record["metrics"]["passed"]
        passed += question_passed(score)
        if not (same_code and same_pass):
            differing.append(record["id"])
    verdict = "all match" if not differing else "DIFFER: " + ", ".join(differing)
    name = (
        f"{folder.parent.name}/{folder.name}"
        if folder.name.startswith("run-")
        else folder.name
    )
    return f"{name}: {passed} of {len(records)} pass on recomputation; {verdict}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folders", nargs="*", type=Path)
    args = parser.parse_args()
    folders = []
    for folder in args.folders or sorted(p for p in RESULTS.iterdir() if p.is_dir()):
        runs = sorted(folder.glob("run-*/records.json"))  # Orchestrate: one per run
        folders += [r.parent for r in runs] or [folder]
    gold = {q["id"]: q for q in load_gold("all")["questions"]}
    numbers, urls = load_index()
    lines = [verify(folder, gold, numbers, urls) for folder in folders]
    print("\n".join(lines))
    return 1 if any("DIFFER" in line for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
