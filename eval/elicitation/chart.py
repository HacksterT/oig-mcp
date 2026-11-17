"""Draws docs/submission/images/elicitation-savings.png from the A/B runs.

uv run --with matplotlib python eval/elicitation/chart.py
"""

import json
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = "eval/results/2026-11-17-elicitation-ab/"
ba = json.load(open(D + "runs-before-after.json"))
nf = json.load(open(D + "runs-no_form.json"))
arms = [
    ("No form: the model asks in chat", nf["runs"]["no_form"], "#898781"),
    ("Form, before #114", ba["runs"]["before"], "#2a78d6"),
    ("Form, after #114", ba["runs"]["after"], "#2a78d6"),
]
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9"
plt.rcParams.update({"font.family": "Helvetica", "font.size": 12})
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), dpi=200, facecolor=SURF)
panels = [
    ("Model requests", "model_requests", "{:.0f}"),
    ("Calls to the server", "server_calls", "{:.0f}"),
    ("Tokens processed", "tokens", "{:,.0f}"),
]
labels = [a[0] for a in arms][::-1]
for ax, (title, key, fmt) in zip(axes, panels):
    vals = [st.median(r[key] for r in a[1]) for a in arms][::-1]
    cols = [a[2] for a in arms][::-1]
    ax.set_facecolor(SURF)
    bars = ax.barh(range(3), vals, color=cols, height=0.56)
    vmax = max(vals)
    for i, v in enumerate(vals):
        ax.text(
            v + vmax * 0.02,
            i,
            fmt.format(v),
            va="center",
            ha="left",
            color=INK,
            fontsize=12,
        )
    ax.set_xlim(0, vmax * 1.25)
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold", pad=10)
    ax.set_yticks(range(3))
    ax.set_yticklabels(labels if ax is axes[0] else [""] * 3, color=INK2)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors="#898781", labelsize=10)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if key != "tokens":
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    if key == "tokens":
        ax.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, _: f"{x / 1000:.0f}k")
        )
fig.suptitle(
    "The server's form halves the round trips for an ambiguous facility name, and cuts tokens 39%",
    x=0.012,
    y=0.995,
    ha="left",
    color=INK,
    fontsize=15,
    fontweight="bold",
)
fig.text(
    0.012,
    0.915,
    '"What has OIG found at the Columbia VA?" (three facilities match). Claude Opus 5.5, median of 5 runs per arm; every run in an arm gave the same counts.',
    ha="left",
    color=INK2,
    fontsize=11,
)
fig.text(
    0.012,
    0.015,
    "Every run opened only the facility the user chose. With no form, the user also has to answer in a second chat turn. Source: eval/results/2026-11-17-elicitation-ab",
    ha="left",
    color="#898781",
    fontsize=9.5,
)
fig.tight_layout(rect=(0, 0.05, 1, 0.9))
fig.savefig("docs/submission/images/elicitation-savings.png", facecolor=SURF)
