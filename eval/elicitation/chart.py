"""Draws docs/submission/images/elicitation-savings.png from the A/B runs.

Before elicitation: the model asks in chat which facility (the no_form arm).
After elicitation: the server's pick-list asks (the current server with a form).

    uv run --with matplotlib python eval/elicitation/chart.py
"""

import json
import statistics as st

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

matplotlib.use("Agg")

D = "eval/results/2026-11-17-elicitation-ab/"
before = json.load(open(D + "runs-no_form.json"))["runs"]["no_form"]
after = json.load(open(D + "runs-before-after.json"))["runs"]["after"]
arms = [
    ("After elicitation:\nthe server's pick-list", after, "#2a78d6"),
    ("Before elicitation:\nClaude asks in chat", before, "#898781"),
]
SURF, INK, INK2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#898781"
plt.rcParams.update({"font.family": "Helvetica", "font.size": 12})
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), dpi=200, facecolor=SURF)
panels = [
    ("Lookups by Claude", lambda r: r["server_calls"], "{:.0f}"),
    ("Turns for the user", lambda r: r.get("user_turns", 1), "{:.0f}"),
    ("Tokens used", lambda r: r["tokens"], "{:,.0f}"),
]
for ax, (title, get, fmt) in zip(axes, panels, strict=True):
    vals = [st.median(get(r) for r in a[1]) for a in arms]
    ax.set_facecolor(SURF)
    ax.barh(range(2), vals, color=[a[2] for a in arms], height=0.55)
    vmax = max(vals)
    for i, v in enumerate(vals):
        ax.text(v + vmax * 0.02, i, fmt.format(v), va="center", color=INK, fontsize=13)
    ax.set_xlim(0, vmax * 1.3)
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold", pad=10)
    ax.set_yticks(range(2))
    ax.set_yticklabels([a[0] for a in arms] if ax is axes[0] else ["", ""], color=INK2)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors=MUTED, labelsize=10)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if title == "Tokens used":
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:.0f}k"))
    else:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
fig.suptitle(
    "Elicitation: half the back-and-forth, 39% fewer tokens",
    x=0.012,
    y=0.99,
    ha="left",
    color=INK,
    fontsize=16,
    fontweight="bold",
)
fig.text(
    0.012,
    0.885,
    '"What has OIG found at the Columbia VA?" matches three facilities. '
    "Claude Opus 5.5, 5 runs each way; every run gave the same counts.",
    ha="left",
    color=INK2,
    fontsize=11,
)
fig.text(
    0.012,
    0.02,
    "Both ways answered for the facility the user chose. "
    "Source: eval/results/2026-11-17-elicitation-ab",
    ha="left",
    color=MUTED,
    fontsize=9.5,
)
fig.tight_layout(rect=(0, 0.06, 1, 0.86))
fig.savefig("docs/submission/images/elicitation-savings.png", facecolor=SURF)
