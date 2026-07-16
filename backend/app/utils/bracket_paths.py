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

# Octavos → cuartos: emparejamiento contiguo en el orden KO-R16.
DEFAULT_R16_TO_QF: list[tuple[int, int]] = [(1, 2), (3, 4), (5, 6), (7, 8)]

# Cuartos → semis: FIFA empareja 1-3 y 2-4 (no 1-2 y 3-4).
DEFAULT_QF_TO_SF: list[tuple[int, int]] = [(1, 3), (2, 4)]

DEFAULT_SF_TO_FINAL: list[tuple[int, int]] = [(1, 2)]


def _load_paths() -> dict:
    path = resolve_path(PATHS_FILE)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pairs_from(key: str, default: list[tuple[int, int]]) -> list[tuple[int, int]]:
    data = _load_paths()
    raw = data.get(key, default)
    return [(int(a), int(b)) for a, b in raw]


def load_r32_to_r16_pairs() -> list[tuple[int, int]]:
    return _pairs_from("r32_to_r16", DEFAULT_R32_TO_R16)


def load_r16_to_qf_pairs() -> list[tuple[int, int]]:
    return _pairs_from("r16_to_qf", DEFAULT_R16_TO_QF)


def load_qf_to_sf_pairs() -> list[tuple[int, int]]:
    return _pairs_from("qf_to_sf", DEFAULT_QF_TO_SF)


def load_sf_to_final_pairs() -> list[tuple[int, int]]:
    return _pairs_from("sf_to_final", DEFAULT_SF_TO_FINAL)


def r32_match_number(fifa_id: str | None) -> int | None:
    if not fifa_id or not fifa_id.startswith("KO-R32-"):
        return None
    try:
        return int(fifa_id.rsplit("-", 1)[-1])
    except ValueError:
        return None


def knockout_slot_number(fifa_id: str | None, prefix: str) -> int | None:
    if not fifa_id or not fifa_id.startswith(prefix):
        return None
    try:
        return int(fifa_id[len(prefix) :])
    except ValueError:
        return None


def knockout_slot_sort_key(fifa_id: str | None) -> tuple[int, int, str]:
    """Orden numérico KO-R32-2 antes que KO-R32-10 (no alfabético)."""
    if not fifa_id:
        return (99, 9999, "")
    for rank, prefix in enumerate(
        ("KO-R32-", "KO-R16-", "KO-QF-", "KO-SF-", "KO-3RD-", "KO-F-")
    ):
        if fifa_id.startswith(prefix):
            try:
                return (rank, int(fifa_id[len(prefix) :]), fifa_id)
            except ValueError:
                break
    return (98, 9999, fifa_id)


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


def pair_winners_by_slot_pairs(
    matches: list,
    winner_fn,
    slot_prefix: str,
    slot_pairs: list[tuple[int, int]],
    label: str,
) -> list[tuple[str, str]]:
    """Empareja ganadores según índices 1-based de la ronda (KO-*-N)."""
    by_num: dict[int, str] = {}
    for m in matches:
        num = knockout_slot_number(getattr(m, "fifa_id", None), slot_prefix)
        if num is None:
            continue
        w = winner_fn(m)
        if w:
            by_num[num] = w

    pairs: list[tuple[str, str]] = []
    for a, b in slot_pairs:
        if a not in by_num or b not in by_num:
            raise ValueError(f"Faltan ganadores para el cruce {label}: {a} vs {b}")
        pairs.append((by_num[a], by_num[b]))
    return pairs


def pair_winners_r16_to_qf(matches: list, winner_fn) -> list[tuple[str, str]]:
    return pair_winners_by_slot_pairs(
        matches, winner_fn, "KO-R16-", load_r16_to_qf_pairs(), "R16→QF"
    )


def pair_winners_qf_to_sf(matches: list, winner_fn) -> list[tuple[str, str]]:
    return pair_winners_by_slot_pairs(
        matches, winner_fn, "KO-QF-", load_qf_to_sf_pairs(), "QF→SF"
    )


def pair_winners_sf_to_final(matches: list, winner_fn) -> list[tuple[str, str]]:
    return pair_winners_by_slot_pairs(
        matches, winner_fn, "KO-SF-", load_sf_to_final_pairs(), "SF→Final"
    )


def pair_losers_sf_to_third(matches: list, loser_fn) -> list[tuple[str, str]]:
    """Empareja perdedores de semis para el partido de tercer puesto (orden KO-SF)."""
    sorted_ms = sorted(
        matches, key=lambda m: knockout_slot_sort_key(getattr(m, "fifa_id", None))
    )
    losers: list[str] = []
    for m in sorted_ms:
        loser = loser_fn(m)
        if not loser:
            raise ValueError(
                f"Falta perdedor clasificado en {getattr(m, 'fifa_id', '?')}"
            )
        losers.append(loser)
    if len(losers) < 2:
        raise ValueError("Se necesitan 2 perdedores de semifinales para el tercer puesto")
    return [(losers[0], losers[1])]


def pair_winners_sequential(winners: list[str]) -> list[tuple[str, str]]:
    """Empareja ganadores en orden: 1-2, 3-4, … (legacy / tests)."""
    pairs: list[tuple[str, str]] = []
    for i in range(0, len(winners), 2):
        if i + 1 >= len(winners):
            break
        pairs.append((winners[i], winners[i + 1]))
    return pairs
