"""Meteo con HTTP simulato: niente rete, niente modello. Le risposte finte hanno la forma vera di Open-Meteo."""

import pytest
import requests

from app import meteo


class RispostaFinta:
    def __init__(self, dati=None, status=200, json_valido=True):
        self._dati, self.status_code, self._json_valido = dati, status, json_valido

    def json(self):
        if not self._json_valido:
            raise ValueError("non e' JSON")
        return self._dati


ROMA = {
    "name": "Roma", "latitude": 41.89193, "longitude": 12.51133,
    "country": "Italia", "admin1": "Lazio", "timezone": "Europe/Rome",
}
ROMANIA = {"name": "Romania", "latitude": 46.0, "longitude": 25.0, "country": "Romania"}
PREVISIONE = {
    "utc_offset_seconds": 3600, "timezone": "Europe/Rome",
    "current": {"time": "2026-11-09T14:45", "interval": 900, "temperature_2m": 17.1, "weather_code": 3},
}


def simula(monkeypatch, geocoding, previsione=None):
    """Sostituisce requests.get: la prima chiamata e' il geocoding, la seconda la previsione.

    Se un elemento e' un'eccezione la solleva, altrimenti lo restituisce. Registra le chiamate.
    """
    risposte = [geocoding] + ([previsione] if previsione is not None else [])
    chiamate = []

    def finta(url, **kwargs):
        chiamate.append((url, kwargs))
        r = risposte[len(chiamate) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(meteo.requests, "get", finta)
    return chiamate


def test_citta_unica(monkeypatch):
    chiamate = simula(monkeypatch, RispostaFinta({"results": [ROMA]}), RispostaFinta(PREVISIONE))
    out = meteo.ottieni_meteo("Roma")
    assert out["location"] == "Roma, Lazio, Italia"
    assert out["temperature_c"] == 17.1
    assert out["conditions"] == "coperto"  # codice WMO 3
    assert out["time"] == "2026-11-09T14:45:00+01:00"  # istante con fuso esplicito
    assert "note" not in out  # nessuna ambiguita': niente nota
    # timeout espliciti su entrambe le richieste, coordinate della localita' scelta nella seconda
    assert all(k["timeout"] for _, k in chiamate) and len(chiamate) == 2
    assert chiamate[1][1]["params"]["latitude"] == ROMA["latitude"]


def test_citta_ambigua_dichiara_la_scelta(monkeypatch):
    simula(monkeypatch, RispostaFinta({"results": [ROMA, ROMANIA]}), RispostaFinta(PREVISIONE))
    out = meteo.ottieni_meteo("Roma")
    assert out["location"] == "Roma, Lazio, Italia"
    assert "Romania" in out["note"] and "prima" in out["note"]


def test_citta_assente(monkeypatch):
    simula(monkeypatch, RispostaFinta({"generationtime_ms": 0.05}))  # senza "results", come fa Open-Meteo
    with pytest.raises(meteo.ErroreMeteo, match="non trovata"):
        meteo.ottieni_meteo("Qwxzyzzy")


@pytest.mark.parametrize("citta", ["", "   ", None, 42])
def test_citta_non_valida_non_fa_rete(monkeypatch, citta):
    chiamate = simula(monkeypatch, RispostaFinta({"results": [ROMA]}))
    with pytest.raises(meteo.ErroreMeteo, match="citta"):
        meteo.ottieni_meteo(citta)
    assert chiamate == []


@pytest.mark.parametrize("fase", [0, 1])
def test_timeout(monkeypatch, fase):
    risposte = [RispostaFinta({"results": [ROMA]}), RispostaFinta(PREVISIONE)]
    risposte[fase] = requests.Timeout("lento")
    simula(monkeypatch, *risposte)
    with pytest.raises(meteo.ErroreMeteo, match="tempo massimo"):
        meteo.ottieni_meteo("Roma")


def test_servizio_irraggiungibile(monkeypatch):
    simula(monkeypatch, requests.ConnectionError("rete giu'"))
    with pytest.raises(meteo.ErroreMeteo, match="irraggiungibile"):
        meteo.ottieni_meteo("Roma")


@pytest.mark.parametrize("fase", [0, 1])
def test_status_http_non_valido(monkeypatch, fase):
    risposte = [RispostaFinta({"results": [ROMA]}), RispostaFinta(PREVISIONE)]
    risposte[fase] = RispostaFinta({}, status=503)
    simula(monkeypatch, *risposte)
    with pytest.raises(meteo.ErroreMeteo, match="HTTP 503"):
        meteo.ottieni_meteo("Roma")


@pytest.mark.parametrize("fase", [0, 1])
def test_json_non_valido(monkeypatch, fase):
    risposte = [RispostaFinta({"results": [ROMA]}), RispostaFinta(PREVISIONE)]
    risposte[fase] = RispostaFinta(json_valido=False)
    simula(monkeypatch, *risposte)
    with pytest.raises(meteo.ErroreMeteo, match="JSON"):
        meteo.ottieni_meteo("Roma")


@pytest.mark.parametrize(
    "geocoding, previsione",
    [
        ([], None),  # il JSON e' valido ma non e' un oggetto
        ({"results": "boh"}, None),
        ({"results": [{"name": "Roma"}]}, None),  # senza coordinate
        ({"results": [ROMA]}, {"current": {}}),  # previsione senza i campi attesi
        ({"results": [ROMA]}, {"current": {"time": "2026-11-09T14:45", "temperature_2m": "caldo", "weather_code": 3},
                               "utc_offset_seconds": 3600}),
        ({"results": [ROMA]}, {"current": {"time": "ieri", "temperature_2m": 17.1, "weather_code": 3},
                               "utc_offset_seconds": 3600}),
    ],
)
def test_payload_inatteso(monkeypatch, geocoding, previsione):
    simula(monkeypatch, RispostaFinta(geocoding), None if previsione is None else RispostaFinta(previsione))
    with pytest.raises(meteo.ErroreMeteo, match="inattesa"):
        meteo.ottieni_meteo("Roma")


def test_codice_meteo_sconosciuto_non_e_inventato(monkeypatch):
    prev = {**PREVISIONE, "current": {**PREVISIONE["current"], "weather_code": 999}}
    simula(monkeypatch, RispostaFinta({"results": [ROMA]}), RispostaFinta(prev))
    assert "999" in meteo.ottieni_meteo("Roma")["conditions"]
