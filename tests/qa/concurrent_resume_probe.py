"""Probe multiprocesso para disputa de retomada do mesmo run_id."""

from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

from asep.execution.state import StateManager


def worker(state_path: str, ready, start, results) -> None:
    manager = StateManager()
    path = Path(state_path)
    state = manager.load(path, expected_run_id=path.parent.name)
    ready.put("loaded")
    start.wait(10)
    try:
        manager.prepare_resume(state)
        manager.save(state, path)
        results.put({"outcome": "saved", "history": len(state.transition_history)})
    except Exception as exc:  # evidence probe records the actual competing outcome
        results.put(
            {"outcome": "error", "type": type(exc).__name__, "message": str(exc)}
        )


def main() -> int:
    state_path = Path(sys.argv[1]).resolve()
    context = multiprocessing.get_context("spawn")
    ready = context.Queue()
    results = context.Queue()
    start = context.Event()
    processes = [
        context.Process(target=worker, args=(str(state_path), ready, start, results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    ready.get(timeout=20)
    ready.get(timeout=20)
    start.set()
    observed = [results.get(timeout=20), results.get(timeout=20)]
    for process in processes:
        process.join(timeout=20)
    final = StateManager().load(state_path, expected_run_id=state_path.parent.name)
    print(
        json.dumps(
            {
                "workers": observed,
                "process_exit_codes": [process.exitcode for process in processes],
                "persisted_status": final.execution_status,
                "persisted_history": len(final.transition_history),
                "resumed_at": final.resumed_at.isoformat() if final.resumed_at else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
