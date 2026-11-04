"""Narrative and charts share the exact persisted numerical results."""
from __future__ import annotations

import html
import json
import os
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def number(value, digits=4):
    return "N/A" if value is None else f"{value:.{digits}f}"


def render(metrics, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    models = metrics["test"]
    base, graph = models["static_hgb"], models["graph_hgb"]
    interval = metrics["uncertainty"]
    low, high = interval["ap_difference_lower_95"], interval["ap_difference_upper_95"]
    supported = low is not None and low > 0 and graph["positive_reviews"] >= base["positive_reviews"]
    decision = ("Treat the graph candidate as worth a representative offline pilot, not deployment approval."
                if supported else "Keep the static comparator as the operating reference while testing the graph candidate further.")
    card_link = os.path.relpath(PROJECT / "DATA_CARD.md", output.resolve()).replace(os.sep, "/")
    rows = "\n".join(f"| {name} | {number(v['average_precision'])} | {v['positive_reviews']}/{v['reviewed']} | "
                     f"{number(v['precision_at_capacity'])} | {number(v['recall_at_capacity'])} |"
                     for name, v in models.items())
    slices = "\n".join(f"| {name} | {values['static_hgb']['positive_reviews']} | {values['graph_hgb']['positive_reviews']} | "
                       f"{values['graph_hgb']['reviewed']} | {values['graph_hgb']['positive_outcomes']} |"
                       for name, values in metrics["test_slices"].items())
    gains = {name: values["graph_hgb"]["positive_reviews"] - values["static_hgb"]["positive_reviews"]
             for name, values in metrics["test_slices"].items()}
    concentration = (f"The additional reviewed positives are concentrated before the declared shift: "
                     f"{gains['original']:+d} in the original segment versus {gains['shifted']:+d} after the change. "
                     "I would not treat the full-period gain as evidence of stable performance under a changed mechanism."
                     if "original" in gains and "shifted" in gains else
                     "This output does not contain both declared segments; the full-stream shift comparison is unavailable.")
    story = f"""# Shared devices need context before they become a review decision

**Decision: {decision}**

This is a new independent portfolio experiment by Vedant Thaker, created in November 2026. It uses original fictional events. It does not reproduce CSAA systems, validate historical employer metrics, or establish real fraud effectiveness.

## Start with the topic: identity relationships in fraud investigation

The narrow question is whether prior customer-device connections add useful ranking information when analysts can inspect only 5% of each day's events. A shared device is an observation; it is not a fraud label. Families and public terminals can create legitimate shared connections too.

## The usual approach hides two different issues

A transaction-only model can consider amount, country changes, channel and time of day while missing coordinated reuse of infrastructure. The tempting alternative is a graph built from the entire dataset. That graph may contain connections that did not exist at the decision time.

I separated those issues. Both trained comparators use the **same histogram gradient-boosting estimator and fixed parameters**. The graph candidate receives additional time-respecting structural features. Neither receives customer IDs, device IDs, ring membership, outcome labels, future edges or label-derived neighbor statistics as features.

## My framework: observe, connect, rank, explain

1. **Observe:** define one row as one fictional transaction and record when its label becomes available.
2. **Connect:** build the bipartite customer-device context from `[t-7days, t)`. All events at a tied timestamp are scored before any of their edges enter the graph.
3. **Rank:** compare a fixed rule, static-feature HGB and the same HGB with graph features at exactly the same daily capacity.
4. **Explain:** provide a review card containing observed connections and the decision-time window, without inserting the eventual outcome or calling an account fraudulent.

The train, validation and test cohorts are separated in time **and** customer/device identity. The final model is refitted using only mature train and validation labels available by day 50, then frozen before the day-50-to-70 test cohort. The test audit uses labels available by day 75. The validation results are visible in the metrics; no hyperparameter or seed search follows them.

## What the executed experiment found

The full stream contains **{metrics['dataset']['rows']:,} events**. The test cohort has **{graph['transactions']:,} events** and **{graph['positive_outcomes']} positive synthetic outcomes**.

| Model | Average precision | Positive outcomes / reviewed | Precision at capacity | Recall at capacity |
|---|---:|---:|---:|---:|
{rows}

The graph-minus-static AP difference has a descriptive 95% day-block bootstrap interval of **[{number(low)}, {number(high)}]** over fixed test predictions. It does not fully capture cross-day customer/ring dependence or estimate variation across synthetic generators, training seeds or future customer populations.

![Measured synthetic review queues](review-capacity.svg)

## Where the result changes under a different mechanism

The generator deliberately changes coordinated-device reuse and label risk from day 60 onward. This is a declared synthetic shift, not evidence that a real adversary behaved this way.

| Test segment | Static positive reviews | Graph positive reviews | Reviews per model | Positive outcomes |
|---|---:|---:|---:|---:|
{slices}

{concentration}

## What impact means here

The practical quantity is the number of additional positive synthetic outcomes inspected at an unchanged review capacity: **{graph['positive_reviews'] - base['positive_reviews']:+d}** in this run. It is neither a customer-loss estimate nor a production capture lift. The synthetic mechanism was designed to include coordinated reuse, so the result establishes that this implementation can inspect that constructed signal, not that graph features will generalize to field data.

The analyst cards make the context inspectable. They expose a shared-device count, prior links and observation window. They are evidence summaries, not causal feature attributions or calibrated fraud probabilities. The implementation never blocks payments or changes account state.

![Observed context for the highest-ranked review card](investigation-network.svg)

## The tradeoff I would take into the next review

The static model is cheaper to reason about and does not need a graph state. The candidate adds state correctness, identity quality, retention and late-data requirements. This offline replay assumes each event is available at its timestamp; it does not solve out-of-order arrival. A production system would need an arrival-time contract, late-event handling and representative labels before its outcomes could be interpreted.

My next checkpoint would use an independently sourced, authorized dataset; observed label delays; benign shared-infrastructure slices; multiple predeclared seeds and time windows; and measured end-to-end state latency. I would keep the review budget fixed and reject the candidate if the extra state fails to improve the relevant queue reliably.

## Reproduce and challenge the conclusion

The numerical source is [metrics.json](metrics.json); [predictions.csv](predictions.csv) includes every held-out score and queue assignment. [investigation-cards.json](investigation-cards.json) contains the ten highest-ranked review cards without outcome fields. The packaged [synthetic events](data/transactions.csv.gz) and [data manifest](data/manifest.json) belong to this exact run. The [project data card]({card_link}) explains the mechanism and scope.

The graph-feature design is informed by primary work on time-respecting graph evaluation, including [Khaleghpour and McKinney, 2026](https://arxiv.org/abs/2603.06632) and [Maganti, 2026](https://arxiv.org/abs/2604.19514). Those papers' code, datasets and benchmark numbers are not copied or used as this project's evidence. This project implements structural features and boosted trees, not a graph neural network.
"""
    (output / "case-study.md").write_bytes(story.encode("utf-8"))
    labels = {"simple_rule": "Fixed rule", "static_hgb": "Static HGB", "graph_hgb": "Graph HGB"}
    max_value = max(1, *(v["positive_reviews"] for v in models.values()))
    elements = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="390" viewBox="0 0 920 390">',
                '<rect width="920" height="390" fill="#fff"/>',
                '<g font-family="Arial,sans-serif" fill="#162b3c">',
                '<text x="28" y="34" font-size="21" font-weight="bold">Same review capacity; count the outcomes actually inspected</text>',
                f'<text x="28" y="62" font-size="14">Synthetic holdout: {graph["transactions"]:,} events, {graph["positive_outcomes"]} positive outcomes; {graph["reviewed"]} reviews per model</text>']
    for i, (name, values) in enumerate(models.items()):
        y = 106 + i * 66
        width = values["positive_reviews"] / max_value * 560
        color = "#127d75" if name == "graph_hgb" else "#386ba5" if name == "static_hgb" else "#8194a2"
        elements.extend([f'<text x="28" y="{y + 23}" font-size="15">{html.escape(labels[name])}</text>',
                         f'<rect x="170" y="{y}" width="{width:.2f}" height="34" rx="3" fill="{color}"/>',
                         f'<text x="{180 + width:.2f}" y="{y + 23}" font-size="15">{values["positive_reviews"]}</text>'])
    elements.extend(['<text x="170" y="334" font-size="14">Positive synthetic outcomes among the reviewed events (zero-based bars)</text>',
                     '<text x="28" y="371" font-size="13">One synthetic stream. This chart does not establish field accuracy, customer impact or financial savings.</text>',
                     '</g></svg>'])
    (output / "review-capacity.svg").write_bytes("\n".join(elements).encode())
    card_path = output / "investigation-cards.json"
    if card_path.exists():
        render_network(json.loads(card_path.read_text(encoding="utf-8")), output)


def render_network(cards, output: Path):
    if not cards:
        return
    card = cards[0]
    prior = [customer for customer in card["evidence"]["observed_device_customers"]
             if customer != card["customer_id"]][:6]
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="530" viewBox="0 0 920 530">',
              '<rect width="920" height="530" fill="white"/>',
              '<g font-family="Arial,sans-serif" fill="#162b3c">',
              '<text x="28" y="32" font-size="20" font-weight="bold">Observed neighbors before the highest-ranked review event</text>',
              f'<text x="28" y="58" font-size="13">Event {html.escape(card["event_id"])}; exclusive observation cutoff {card["decision_time"]}; fictional identities</text>',
              '<line x1="460" y1="110" x2="460" y2="260" stroke="#127d75" stroke-width="2" stroke-dasharray="6,5"/>']
    for i, customer in enumerate(prior):
        angle = (i + 0.5) / max(1, len(prior)) * 2 * math.pi
        x, y = 460 + 290 * math.cos(angle), 280 + 120 * math.sin(angle)
        pieces.extend([f'<line x1="460" y1="280" x2="{x:.1f}" y2="{y:.1f}" stroke="#8194a2" stroke-width="2"/>',
                       f'<circle cx="{x:.1f}" cy="{y:.1f}" r="29" fill="#dbe7f2" stroke="#386ba5"/>',
                       f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11">{html.escape(customer[-6:])}</text>'])
    pieces.extend(['<rect x="420" y="250" width="80" height="60" rx="8" fill="#386ba5"/>',
                   '<text x="460" y="284" text-anchor="middle" font-size="13" fill="white">device</text>',
                   '<circle cx="460" cy="110" r="31" fill="#dcf0ea" stroke="#127d75"/>',
                   '<text x="460" y="114" text-anchor="middle" font-size="11">requester</text>',
                   f'<text x="28" y="455" font-size="14">Solid edges: prior observed connections. Dashed edge: current review request, not inserted as future evidence.</text>',
                   f'<text x="28" y="480" font-size="13">Displayed prior customers: {len(prior)} (capped at 6). Full device-user count: {card["observations"]["device_users_7d"]}.</text>',
                   '<text x="28" y="508" font-size="13">A shared device is context for human review, not a misconduct finding. No outcome label is shown.</text>',
                   '</g></svg>'])
    (output / "investigation-network.svg").write_bytes("\n".join(pieces).encode())


def from_file(output: Path):
    render(json.loads((output / "metrics.json").read_text(encoding="utf-8")), output)
