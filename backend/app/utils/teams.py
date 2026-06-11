"""Normalización de nombres de selecciones (español/inglés) a un código país.

Permite emparejar los partidos de una API externa (nombres en inglés) con los
partidos del torneo almacenados en español, sin duplicar registros.
"""
from __future__ import annotations

import unicodedata


def _norm(value: str) -> str:
    base = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return "".join(ch for ch in base.lower() if ch.isalnum())


# code (ISO-ish) -> lista de alias normalizados (español + inglés)
_TEAM_ALIASES: dict[str, list[str]] = {
    "mx": ["mexico"],
    "za": ["sudafrica", "southafrica"],
    "kr": ["repdecorea", "corea", "coreadelsur", "southkorea", "korearepublic",
           "republicofkorea", "korea"],
    "cz": ["repcheca", "republicacheca", "chequia", "czechrepublic", "czechia"],
    "ca": ["canada"],
    "ba": ["bosniaherzegovina", "bosniayherzegovina", "bosniaandherzegovina", "bosnia"],
    "qa": ["qatar"],
    "ch": ["suiza", "switzerland"],
    "br": ["brasil", "brazil"],
    "ma": ["marruecos", "morocco"],
    "ht": ["haiti"],
    "gb-sct": ["escocia", "scotland"],
    "us": ["estadosunidos", "unitedstates", "usa", "unitedstatesofamerica"],
    "py": ["paraguay"],
    "au": ["australia"],
    "tr": ["turquia", "turkey", "turkiye"],
    "de": ["alemania", "germany"],
    "cw": ["curazao", "curacao"],
    "ci": ["costademarfil", "cotedivoire", "ivorycoast", "costadivoire"],
    "ec": ["ecuador"],
    "nl": ["paisesbajos", "holanda", "netherlands"],
    "jp": ["japon", "japan"],
    "se": ["suecia", "sweden"],
    "tn": ["tunez", "tunisia"],
    "be": ["belgica", "belgium"],
    "eg": ["egipto", "egypt"],
    "ir": ["rideiran", "iran", "iririran", "islamicrepublicofiran"],
    "nz": ["nuevazelanda", "newzealand"],
    "es": ["espana", "spain"],
    "cv": ["caboverde", "capeverde", "caboverdeislands"],
    "sa": ["arabiasaudi", "arabiasaudita", "saudiarabia"],
    "uy": ["uruguay"],
    "fr": ["francia", "france"],
    "sn": ["senegal"],
    "iq": ["irak", "iraq"],
    "no": ["noruega", "norway"],
    "ar": ["argentina"],
    "dz": ["argelia", "algeria"],
    "at": ["austria"],
    "jo": ["jordania", "jordan"],
    "pt": ["portugal"],
    "cd": ["rdcongo", "congo", "drcongo", "democraticrepublicofcongo", "congodr",
           "congodrc"],
    "uz": ["uzbekistan"],
    "co": ["colombia"],
    "gb-eng": ["inglaterra", "england"],
    "hr": ["croacia", "croatia"],
    "gh": ["ghana"],
    "pa": ["panama"],
}

# alias normalizado -> code
_ALIAS_TO_CODE: dict[str, str] = {}
for _code, _aliases in _TEAM_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_TO_CODE[_alias] = _code


def team_code(name: str | None) -> str | None:
    """Devuelve el código de país del equipo, o None si no se reconoce."""
    if not name:
        return None
    return _ALIAS_TO_CODE.get(_norm(name))
