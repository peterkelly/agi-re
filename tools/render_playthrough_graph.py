#!/usr/bin/env python3
"""Validate and render a clean-room playthrough state graph."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


COLORS = {
    "state": ("#e8eef7", "ellipse"),
    "precondition": ("#fff4cc", "box"),
    "score_action": ("#dff3df", "box"),
    "random_retry": ("#f6dfef", "diamond"),
    "terminal": ("#dce8ff", "doublecircle"),
}


def load_graph(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    ids = [node["id"] for node in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate node id")
    known = set(ids)
    for edge in data.get("edges", []):
        if edge["from"] not in known or edge["to"] not in known:
            raise ValueError(f"edge references unknown node: {edge}")
    score_nodes = {node["id"]: node for node in nodes if node["kind"] == "score_action"}
    route = data.get("score_route", [])
    if set(route) != set(score_nodes) or len(route) != len(score_nodes):
        raise ValueError("score_route must list every score node exactly once")
    total = sum(score_nodes[node_id]["score_delta"] for node_id in route)
    if total != data["game"]["maximum_score"]:
        raise ValueError(f"score route totals {total}, expected {data['game']['maximum_score']}")
    return data


def quote(value: object) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def to_dot(data: dict) -> str:
    by_phase: dict[str, list[dict]] = {}
    for node in data["nodes"]:
        by_phase.setdefault(node.get("phase", "Other"), []).append(node)
    lines = [
        "digraph playthrough {",
        "  graph [rankdir=TB, compound=true, fontname=Helvetica, fontsize=10];",
        "  node [fontname=Helvetica, fontsize=8, style=filled];",
        "  edge [fontname=Helvetica, fontsize=7, color=\"#555555\"];",
    ]
    for index, (phase, nodes) in enumerate(by_phase.items()):
        lines.extend([f"  subgraph cluster_{index} {{", f"    label={quote(phase)};", "    color=\"#aaaaaa\";"])
        for node in nodes:
            fill, shape = COLORS.get(node["kind"], ("#eeeeee", "box"))
            label = node["label"]
            if node["kind"] == "score_action":
                label += f" (+{node['score_delta']})"
            lines.append(f"    {quote(node['id'])} [label={quote(label)}, shape={shape}, fillcolor={quote(fill)}];")
        lines.append("  }")
    for edge in data["edges"]:
        style = "dashed" if edge["kind"] in {"random_failure", "random_wait"} else "solid"
        label = edge["instruction"]
        if len(label) > 96:
            label = label[:93] + "..."
        lines.append(f"  {quote(edge['from'])} -> {quote(edge['to'])} [label={quote(label)}, style={style}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("dot", "svg", "png", "pdf"), default="svg")
    args = parser.parse_args()
    data = load_graph(args.json_path)
    dot = to_dot(data)
    output = args.output or args.json_path.with_suffix("." + args.format)
    if args.format == "dot":
        output.write_text(dot, encoding="utf-8")
    else:
        subprocess.run(["dot", f"-T{args.format}", "-o", str(output)], input=dot, text=True, check=True)
    print(output)


if __name__ == "__main__":
    main()
