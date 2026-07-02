"""Tests de rutas oficiales del cuadro eliminatorio."""
from __future__ import annotations

from types import SimpleNamespace

from app.utils.bracket_paths import pair_winners_r32_to_r16, pair_winners_sequential


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


def test_sequential_pairing():
    winners = ["A", "B", "C", "D"]
    assert pair_winners_sequential(winners) == [("A", "B"), ("C", "D")]
