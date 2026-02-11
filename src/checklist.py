from __future__ import annotations

from typing import Dict, List


def evaluate_checklist(memory: Dict[str, any]) -> Dict[str, any]:
    # placeholder simple checklist based on flags collected in memory
    hits = memory.get("checklist_hits", [])
    hit_set = sorted(set(hits))
    count = len(hit_set)
    verdict = "전문가 의뢰 필요" if count >= 2 else "경과 관찰"
    return {
        "hits": hit_set,
        "count": count,
        "verdict": verdict,
    }
