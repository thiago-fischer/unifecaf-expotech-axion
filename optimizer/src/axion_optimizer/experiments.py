"""Reproducible measurements; run with python -m axion_optimizer.experiments."""

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from statistics import mean
from time import monotonic

import ortools

from axion_optimizer import __version__
from axion_optimizer.domain import Item, Machine, Snapshot, Step
from axion_optimizer.planner import plan


def make_snapshot(routes: list[list[tuple[int, int]]], quantities: list[int]) -> Snapshot:
    return Snapshot(
        tuple(
            Item(
                100 + i * 7,
                "Personalizado",
                quantities[i],
                tuple(Step(j, m, d) for j, (m, d) in enumerate(route, 1)),
            )
            for i, route in enumerate(routes)
        ),
        tuple(Machine(m, f"Máquina {m}") for m in sorted({m for r in routes for m, _ in r})),
    )


def peak_memory_bytes() -> int:
    """Peak resident memory of this process, including native solver allocations."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    historical = [[(7, 10), (99, 15)], [(42, 15), (99, 20)], [(7, 10), (42, 15), (99, 20)]]
    cases = {
        "historical_65": make_snapshot(historical, [1, 1, 1]),
        "historical_175": make_snapshot(historical, [3, 2, 4]),
        "heterogeneous_revisits": make_snapshot(
            [
                [(7, 13), (99, 7), (7, 11)],
                [(99, 17)],
                [(42, 5), (7, 19), (42, 3), (99, 2)],
                [(99, 3), (42, 7)],
            ],
            [3, 4, 2, 3],
        ),
        "boundary_units_operations_machines": make_snapshot(
            [
                [(7 + 3 * ((i * 10 + j) % 50), 1 + ((i * 7 + j * 13) % 23)) for j in range(10)]
                for i in range(10)
            ],
            [10] * 10,
        ),
        "boundary_horizon": make_snapshot([[(7, 1_000_000_000)]], [1]),
        "boundary_revisits": make_snapshot(
            [[(7 + 3 * (j % 5), 1 + j % 7) for j in range(10)]], [100]
        ),
    }
    report = dict(
        planner_version=__version__,
        ortools_version=ortools.__version__,
        python=platform.python_version(),
        platform=platform.platform(),
        processor=platform.processor(),
        logical_cpu_count=os.cpu_count(),
        seeds=list(range(5)),
        budgets=dict(ga_seconds=3, certification_seconds=7),
        memory_measurement="cumulative peak process RSS; includes native allocations",
        cases={},
    )
    started = monotonic()
    for name, snapshot in cases.items():
        runs = []
        for seed in range(5):
            result = plan(snapshot, 1, seed)
            search = result["search"]
            runs.append(
                dict(
                    seed=seed,
                    **result["metrics"],
                    selected_source=result["selected_source"],
                    optimality_proven=result["optimality_proven"],
                    ga=search["ga"],
                    certification=search["certification"],
                    baseline_results=search["baseline_results"],
                    total_seconds=search["total_planning_seconds"],
                    peak_process_rss_bytes=peak_memory_bytes(),
                )
            )

        def summary(values: list[float]) -> dict[str, float]:
            return dict(best=min(values), mean=mean(values), worst=max(values))

        report["cases"][name] = dict(
            runs=runs,
            makespan=summary([r["makespan_seconds"] for r in runs]),
            ga_makespan=summary([r["ga"]["best_makespan_seconds"] for r in runs]),
            gain_percent=summary([r["improvement_percent"] for r in runs]),
            gap_percent=summary([r["relative_gap_percent"] for r in runs]),
            computation_seconds=summary([r["total_seconds"] for r in runs]),
            proof_frequency=mean([r["optimality_proven"] for r in runs]),
            evolutionary_gain_runs=sum(
                r["ga"]["best_makespan_seconds"] < r["ga"]["initial_best_makespan_seconds"]
                for r in runs
            ),
            cp_improvement_runs=sum(r["selected_source"] == "cp_sat" for r in runs),
        )
        print(f"{name}: {report['cases'][name]['makespan']}", flush=True)
    report["elapsed_seconds"] = monotonic() - started
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
