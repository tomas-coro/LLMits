import math

import pytest

from app.convertitore import UNITA_SUPPORTATE, converti


@pytest.mark.parametrize(
    "valore, da, a, atteso",
    [
        (1, "km", "m", 1000.0),
        (2500, "m", "km", 2.5),
        (100, "C", "F", 212.0),
        (32, "F", "C", 0.0),
        (-40, "C", "F", -40.0),
        (37, "C", "F", 98.6),  # senza arrotondamento verrebbe 98.60000000000001
        (5, "m", "m", 5.0),  # stessa unita': valido, il valore non cambia
    ],
)
def test_conversioni_valide(valore, da, a, atteso):
    assert converti(valore, da, a) == {"value": atteso, "unit": a}


def test_unita_supportate_sono_quelle_della_specifica():
    assert set(UNITA_SUPPORTATE) == {"m", "km", "C", "F"}


@pytest.mark.parametrize("valore", [math.nan, math.inf, -math.inf])
def test_numero_non_finito_rifiutato(valore):
    with pytest.raises(ValueError, match="finito"):
        converti(valore, "m", "km")


@pytest.mark.parametrize("valore", ["10", None, True])
def test_valore_non_numerico_rifiutato(valore):
    with pytest.raises(ValueError, match="numero"):
        converti(valore, "m", "km")


def test_unita_sconosciuta_rifiutata_e_elenca_quelle_ammesse():
    with pytest.raises(ValueError, match="sconosciuta 'miglia'") as e:
        converti(1, "miglia", "km")
    assert "m, km, C, F" in str(e.value)
    with pytest.raises(ValueError, match="sconosciuta 'K'"):
        converti(1, "C", "K")


def test_grandezze_diverse_rifiutate():
    with pytest.raises(ValueError, match="grandezze diverse"):
        converti(1, "km", "C")
