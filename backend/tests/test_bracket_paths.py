"""Tests de rutas oficiales del cuadro eliminatorio."""
from __future__ import annotations

from types import SimpleNamespace

from app.utils.bracket_paths import (
    knockout_slot_sort_key,
    pair_winners_qf_to_sf,
    pair_winners_r16_to_qf,
    pair_winners_r32_to_r16,
    pair_winners_sequential,
)


def _m(fifa_id: str, winner: str):
    return SimpleNamespace(fifa_id=fifa_id, classified_winner=lambda w=winner: w)


def test_r32_to_r16_official_pairings():
    """Octavos: Canadá-Marruecos, Francia-Paraguay, Brasil-Noruega, etc."""
    matches = [
        _m("KO-R32-1", "Canadá"),
        _m("KO-R32-2", "Paraguay"),
        _m("KO-R32-3", "Marruecos"),
        _m("KO-R32-4", "Brasil"),
        _m("KO-R32-5", "Francia"),
        _m("KO-R32-6", "Noruega"),
        _m("KO-R32-7", "México"),
        _m("KO-R32-8", "Inglaterra"),
        _m("KO-R32-9", "Estados Unidos"),
        _m("KO-R32-10", "Bélgica"),
        _m("KO-R32-11", "Portugal"),
        _m("KO-R32-12", "España"),
        _m("KO-R32-13", "Suiza"),
        _m("KO-R32-14", "Argentina"),
        _m("KO-R32-15", "Colombia"),
        _m("KO-R32-16", "Australia"),
    ]
    pairs = pair_winners_r32_to_r16(matches, lambda m: m.classified_winner())
    assert pairs[0] == ("Canadá", "Marruecos")
    assert pairs[1] == ("Paraguay", "Francia")
    assert pairs[2] == ("Brasil", "Noruega")
    assert pairs[3] == ("México", "Inglaterra")
    assert pairs[6] == ("Suiza", "Colombia")
    assert pairs[7] == ("Argentina", "Australia")


def test_qf_to_sf_fifa_pairing_france_spain():
    """Semis oficiales: Francia-España e Inglaterra-Argentina (QF 1vs3 y 2vs4)."""
    qf = [
        _m("KO-QF-1", "Francia"),  # venció a Marruecos
        _m("KO-QF-2", "Inglaterra"),  # venció a Noruega
        _m("KO-QF-3", "España"),  # venció a Bélgica
        _m("KO-QF-4", "Argentina"),  # venció a Suiza
    ]
    pairs = pair_winners_qf_to_sf(qf, lambda m: m.classified_winner())
    assert pairs == [("Francia", "España"), ("Inglaterra", "Argentina")]
    # El emparejamiento contiguo 1-2 / 3-4 es el incorrecto (bug original).
    wrong = pair_winners_sequential([m.classified_winner() for m in qf])
    assert wrong == [("Francia", "Inglaterra"), ("España", "Argentina")]


def test_sf_to_third_and_final():
    """Final: España-Argentina; 3er puesto: Francia-Inglaterra."""
    from app.utils.bracket_paths import pair_losers_sf_to_third, pair_winners_sf_to_final

    class _SF:
        def __init__(self, fifa_id, winner, loser):
            self.fifa_id = fifa_id
            self._w = winner
            self._l = loser

        def classified_winner(self):
            return self._w

        def classified_loser(self):
            return self._l

    sf = [
        _SF("KO-SF-1", "España", "Francia"),
        _SF("KO-SF-2", "Argentina", "Inglaterra"),
    ]
    assert pair_winners_sf_to_final(sf, lambda m: m.classified_winner()) == [
        ("España", "Argentina")
    ]
    assert pair_losers_sf_to_third(sf, lambda m: m.classified_loser()) == [
        ("Francia", "Inglaterra")
    ]


def test_r16_to_qf_contiguous():
    r16 = [
        _m("KO-R16-1", "Marruecos"),
        _m("KO-R16-2", "Francia"),
        _m("KO-R16-3", "Noruega"),
        _m("KO-R16-4", "Inglaterra"),
        _m("KO-R16-5", "Bélgica"),
        _m("KO-R16-6", "España"),
        _m("KO-R16-7", "Suiza"),
        _m("KO-R16-8", "Argentina"),
    ]
    pairs = pair_winners_r16_to_qf(r16, lambda m: m.classified_winner())
    assert pairs == [
        ("Marruecos", "Francia"),
        ("Noruega", "Inglaterra"),
        ("Bélgica", "España"),
        ("Suiza", "Argentina"),
    ]


def test_sequential_pairing():
    winners = ["A", "B", "C", "D"]
    assert pair_winners_sequential(winners) == [("A", "B"), ("C", "D")]


def test_knockout_slot_sort_key_numeric():
    ids = ["KO-R32-10", "KO-R32-2", "KO-R32-1", "KO-R32-16"]
    assert sorted(ids, key=knockout_slot_sort_key) == [
        "KO-R32-1",
        "KO-R32-2",
        "KO-R32-10",
        "KO-R32-16",
    ]
