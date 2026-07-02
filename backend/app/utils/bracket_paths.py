"""Rutas oficiales del cuadro eliminatorio FIFA 2026."""
from __future__ import annotations

import json

from app.core.config import resolve_path

PATHS_FILE = "data/knockout_bracket_paths.json"

# Cruces oficiales dieciseisavos → octavos (números de partido KO-R32-N).
DEFAULT_R32_TO_R16: list[tuple[int, int]] = [
    (1, 3),
    (2, 5),
    (4, 6),
    (7, 8),
    (9, 10),
    (11, 12),
    (13, 15),
    (14, 16),
]


def load_r32_to_r16_pairs() -> list[tuple[int, int]]:
    path = resolve_path(PATHS_FILE)
    if not path.exists():
        return DEFAULT_R32_TO_R16
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("r32_to_r16", DEFAULT_R32_TO_R16)
    return [(int(a), int(b)) for a, b in raw]


def r32_match_number(fifa_id: str | None) -> int | None:
    if not fifa_id or not fifa_id.startswith("KO-R32-"):
        return None
    try:
        return int(fifa_id.rsplit("-", 1)[-1])
    except ValueError:
        return None


def pair_winners_r32_to_r16(
    matches: list, winner_fn,
) -> list[tuple[str, str]]:
    """Empareja ganadores de dieciseisavos según el cuadro FIFA."""
    by_num: dict[int, str] = {}
    for m in matches:
        num = r32_match_number(getattr(m, "fifa_id", None))
        if num is None:
            continue
        w = winner_fn(m)
        if w:
            by_num[num] = w

    pairs: list[tuple[str, str]] = []
    for a, b in load_r32_to_r16_pairs():
        if a not in by_num or b not in by_num:
            raise ValueError(f"Faltan ganadores para el cruce R32-{a} vs R32-{b}")
        pairs.append((by_num[a], by_num[b]))
    return pairs


def pair_winners_sequential(winners: list[str]) -> list[tuple[str, str]]:
    """Empareja ganadores en orden de bracket: 1-2, 3-4, … (octavos → final)."""
    pairs: list[tuple[str, str]] = []
    for i in range(0, len(winners), 2):
        if i + 1 >= len(winners):
            break
        pairs.append((winners[i], winners[i + 1]))
    return pairs
