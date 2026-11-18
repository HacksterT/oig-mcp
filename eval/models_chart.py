"""Draws docs/submission/images/models-spread.png: the same server, five models.

Figures are the final-server results on the 24 main questions, from
eval/results/ (summary.md in each run folder). DeepSeek is left out: it ran
18 of the questions and was judged against the gold, not scored by the code checks.

    uv run --with matplotlib python eval/models_chart.py
"""

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

SURF, INK, INK2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#898781"
BLUE, GRAY = "#2a78d6", "#c3c2b7"
rows = [  # label, questions passing every check (of 24), with the server?
    ("Claude Opus 5.5", 23, True),
    ("Claude Sonnet 5.5", 22, True),
    ("GPT-OSS 120B, in watsonx Orchestrate", 12, True),
    ("Llama 3.3 70B, on watsonx.ai", 9, True),
    ("Claude Opus 5.5, no server", 3, False),
    ("Llama 3.3 70B, no server", 2, False),
][::-1]
plt.rcParams.update({"font.family": "Helvetica", "font.size": 12})
fig, ax = plt.subplots(figsize=(12, 4.6), dpi=200, facecolor=SURF)
ax.set_facecolor(SURF)
ax.barh(
    range(len(rows)),
    [r[1] for r in rows],
    color=[BLUE if r[2] else GRAY for r in rows],
    height=0.6,
)
for i, (_, value, _) in enumerate(rows):
    ax.text(value + 0.3, i, f"{value} of 24", va="center", color=INK, fontsize=12)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows], color=INK2)
ax.set_xlim(0, 27)
ax.set_xticks([0, 6, 12, 18, 24])
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", colors=MUTED, labelsize=10)
for side in ["top", "right", "left"]:
    ax.spines[side].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.xaxis.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
fig.suptitle(
    "Same server, different models: 9 to 23 of 24 questions",
    x=0.012,
    y=0.98,
    ha="left",
    color=INK,
    fontsize=16,
    fontweight="bold",
)
fig.text(
    0.012,
    0.875,
    "Questions passing every check, scored against answers computed from the data. "
    "Blue: with the server. Gray: the same model with no server.",
    ha="left",
    color=INK2,
    fontsize=11,
)
fig.text(
    0.012,
    0.02,
    "GPT-OSS 120B: both runs scored 12. DeepSeek V4 Pro ran 18 of the questions and was "
    "judged differently (all 18 agreed with the gold), so it is not shown. Source: eval/results",
    ha="left",
    color=MUTED,
    fontsize=9.5,
)
fig.tight_layout(rect=(0, 0.05, 1, 0.85))
fig.savefig("docs/submission/images/models-spread.png", facecolor=SURF)
