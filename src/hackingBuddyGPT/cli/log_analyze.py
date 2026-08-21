"""
CLI: aggregate one or more per-run JSONL logs into a stats table.

    hackingbuddygpt-log-analyze logs/*.jsonl [--latex] [--model gpt-4o] [--min-duration 30]

Prints a Rich table by default; ``--latex`` emits a paper-ready ``tabular`` instead. Filters drop
runs below a duration or not matching a model substring before aggregating.
"""

import argparse
import datetime
import os
import statistics

from rich.console import Console
from rich.table import Table

from hackingBuddyGPT.analysis.log_model import RunSummary, load_run

COLUMNS = [
    "run",
    "model",
    "state",
    "duration_s",
    "llm_calls",
    "in_tokens",
    "out_tokens",
    "reason_tokens",
    "cost_usd",
    "tool_calls",
]


def _row(run: RunSummary) -> list[str]:
    return [
        os.path.basename(run.path),
        run.model,
        run.state,
        f"{run.duration_seconds:.1f}",
        str(run.llm_calls),
        str(run.input_tokens),
        str(run.output_tokens),
        str(run.reasoning_tokens),
        f"{run.cost:.4f}",
        str(run.total_tool_calls),
    ]


def _average_row(runs: list[RunSummary]) -> list[str]:
    def mean_std(values):
        if not values:
            return "0", "0"
        m = statistics.mean(values)
        s = statistics.stdev(values) if len(values) > 1 else 0.0
        return m, s

    dur_m, dur_s = mean_std([r.duration_seconds for r in runs])
    calls_m, calls_s = mean_std([r.llm_calls for r in runs])
    in_m, in_s = mean_std([r.input_tokens for r in runs])
    out_m, out_s = mean_std([r.output_tokens for r in runs])
    reason_m, reason_s = mean_std([r.reasoning_tokens for r in runs])
    cost_m, cost_s = mean_std([r.cost for r in runs])
    tools_m, tools_s = mean_std([r.total_tool_calls for r in runs])
    return [
        f"avg (n={len(runs)})",
        "",
        "",
        f"{dur_m:.1f}±{dur_s:.1f}",
        f"{calls_m:.1f}±{calls_s:.1f}",
        f"{in_m:.0f}±{in_s:.0f}",
        f"{out_m:.0f}±{out_s:.0f}",
        f"{reason_m:.0f}±{reason_s:.0f}",
        f"{cost_m:.4f}±{cost_s:.4f}",
        f"{tools_m:.1f}±{tools_s:.1f}",
    ]


def render_rich(runs: list[RunSummary], console: Console) -> None:
    table = Table(title="hackingBuddyGPT runs", show_lines=False)
    for col in COLUMNS:
        table.add_column(col)
    for run in runs:
        table.add_row(*_row(run))
    if len(runs) > 1:
        table.add_section()
        table.add_row(*_average_row(runs))
    console.print(table)


def render_latex(runs: list[RunSummary]) -> str:
    lines = [
        "\\begin{tabular}{l" + "r" * (len(COLUMNS) - 1) + "}",
        "\\toprule",
        " & ".join(c.replace("_", "\\_") for c in COLUMNS) + " \\\\",
        "\\midrule",
    ]
    for run in runs:
        lines.append(" & ".join(c.replace("_", "\\_") for c in _row(run)) + " \\\\")
    if len(runs) > 1:
        lines.append("\\midrule")
        avg = [c.replace("±", " $\\pm$ ").replace("_", "\\_") for c in _average_row(runs)]
        lines.append(" & ".join(avg) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate hackingBuddyGPT per-run JSONL logs.")
    parser.add_argument("inputs", nargs="+", help="paths to logs/log-<timestamp>.jsonl files")
    parser.add_argument("--latex", action="store_true", help="emit a LaTeX tabular instead of a Rich table")
    parser.add_argument("--model", default=None, help="only include runs whose model contains this substring")
    parser.add_argument("--min-duration", type=float, default=0.0, help="only include runs at least this many seconds")
    args = parser.parse_args()

    runs = [load_run(path) for path in args.inputs]
    if args.model:
        runs = [r for r in runs if args.model in r.model]
    if args.min_duration:
        runs = [r for r in runs if r.duration_seconds >= args.min_duration]
    runs.sort(key=lambda r: r.start or datetime.datetime.min)

    if args.latex:
        print(render_latex(runs))
    else:
        render_rich(runs, Console())


if __name__ == "__main__":
    main()
