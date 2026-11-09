import pytest

from app.calcolatrice import MAX_ESPONENTE, MAX_LUNGHEZZA, calcola


@pytest.mark.parametrize(
    "espressione, atteso",
    [
        ("2 + 3", 5.0),
        ("2 + 3 * 4", 14.0),  # precedenza
        ("(2 + 3) * 4", 20.0),  # parentesi
        ("-5 + 2", -3.0),  # meno unario
        ("--3", 3.0),
        ("2 ** 10", 1024.0),
        ("-2 ** 2", -4.0),  # come in Python: -(2 ** 2)
        ("2 ** -1", 0.5),
        ("10 % 3", 1.0),
        ("7 / 2", 3.5),
        ("0.1 + 0.2", 0.3),  # senza arrotondamento verrebbe 0.30000000000000004
    ],
)
def test_espressioni_valide(espressione, atteso):
    assert calcola(espressione) == {"value": atteso, "expression": espressione}


@pytest.mark.parametrize(
    "espressione, messaggio",
    [
        ("", "vuota"),
        ("   ", "vuota"),
        ("2 +", "non valida"),
        ("abc", "non ammesso"),  # nomi
        ("__import__('os')", "non ammesso"),  # chiamate
        ("'a' * 3", "non ammesso"),  # stringhe
        ("1 < 2", "non ammesso"),  # confronti
        ("True + 1", "non ammesso"),  # bool non e' un numero
        ("1j", "non ammesso"),  # numeri complessi
        ("1 / 0", "divisione per zero"),
        ("5 % 0", "divisione per zero"),
        ("9 ** 9 ** 9", "esponente"),
        (f"2 ** {MAX_ESPONENTE + 1}", "esponente"),
        ("10 ** 308 * 10", "non finito"),
        ("(-8) ** 0.5", "non reale"),
        ("9" * (MAX_LUNGHEZZA + 1), "troppo lunga"),
    ],
)
def test_errori_chiari(espressione, messaggio):
    with pytest.raises(ValueError, match=messaggio):
        calcola(espressione)


def test_argomento_non_testo():
    with pytest.raises(ValueError, match="testo"):
        calcola(5)


def test_limite_esponente_e_incluso():
    assert calcola(f"1 ** {MAX_ESPONENTE}")["value"] == 1.0
