#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import multiprocessing as mp
from typing import Callable, Iterable, List, Any, Tuple

_SENTINEL = ("__STOP__", None)

def _worker(task_q: mp.Queue, result_q: mp.Queue, fn: Callable):
    while True:
        item = task_q.get()
        if item == _SENTINEL:
            break
        idx, payload = item
        try:
            res = fn(payload)
            result_q.put((idx, res, None))
        except Exception as e:
            result_q.put((idx, None, repr(e)))

def start_cluster(n_workers: int, fn: Callable) -> Tuple[List[mp.Process], mp.Queue, mp.Queue]:
    assert n_workers >= 1
    ctx = mp.get_context("spawn")
    task_q: mp.Queue = ctx.Queue(maxsize=n_workers * 4)
    result_q: mp.Queue = ctx.Queue()
    workers: List[mp.Process] = []
    for _ in range(n_workers):
        p = ctx.Process(target=_worker, args=(task_q, result_q, fn), daemon=True)
        p.start()
        workers.append(p)
    return workers, task_q, result_q

def stop_cluster(workers: List[mp.Process], task_q: mp.Queue):
    for _ in workers:
        task_q.put(_SENTINEL)
    for p in workers:
        p.join(timeout=10)

def map_distributed(fn: Callable, items: Iterable[Any], workers: int = 4, chunk: int = 1) -> List[Any]:
    """
    Distribuert map: sender (idx, item) til workers og henter sortert resultat.
    """
    procs, tq, rq = start_cluster(max(1, int(workers)), fn)
    try:
        # feed
        idx = 0
        for x in items:
            tq.put((idx, x))
            idx += 1
        total = idx

        # flush sentinels
        stop_cluster(procs, tq)

        # collect
        out: List[Tuple[int, Any]] = []
        got = 0
        while got < total:
            i, val, err = rq.get()
            got += 1
            if err is not None:
                raise RuntimeError(f"worker error at {i}: {err}")
            out.append((i, val))
        out.sort(key=lambda t: t[0])
        return [v for _, v in out]
    finally:
        # best-effort cleanup
        try:
            while not rq.empty():
                rq.get_nowait()
        except Exception:
            pass