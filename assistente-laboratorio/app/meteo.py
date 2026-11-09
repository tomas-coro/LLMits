"""Meteo attuale da Open-Meteo (geocoding + current forecast). Senza chiave API.

Logica separata dal server MCP, cosi' si prova con risposte HTTP simulate. Nessun fallback
silenzioso: ogni problema diventa un ErroreMeteo con un messaggio che dice cosa e' andato storto.
"""

from datetime import datetime, timedelta, timezone

import requests

URL_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
URL_PREVISIONE = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = (5, 10)  # secondi: (connessione, lettura), per ognuna delle due richieste
MAX_RISULTATI = 5

# Codici meteo WMO usati da Open-Meteo (weather_code). Un codice non in tabella non si inventa.
CONDIZIONI = {
    0: "cielo sereno", 1: "prevalentemente sereno", 2: "parzialmente nuvoloso", 3: "coperto",
    45: "nebbia", 48: "nebbia con brina",
    51: "pioviggine leggera", 53: "pioviggine moderata", 55: "pioviggine intensa",
    56: "pioviggine gelata leggera", 57: "pioviggine gelata intensa",
    61: "pioggia debole", 63: "pioggia moderata", 65: "pioggia forte",
    66: "pioggia gelata leggera", 67: "pioggia gelata forte",
    71: "neve debole", 73: "neve moderata", 75: "neve forte", 77: "granelli di neve",
    80: "rovesci deboli", 81: "rovesci moderati", 82: "rovesci violenti",
    85: "rovesci di neve deboli", 86: "rovesci di neve forti",
    95: "temporale", 96: "temporale con grandine leggera", 99: "temporale con grandine forte",
}


class ErroreMeteo(Exception):
    """Il meteo non e' ottenibile; il messaggio e' gia' leggibile e distingue la causa."""


def _chiedi_json(url, params, cosa):
    """GET con timeout. Distingue timeout, rete irraggiungibile, status HTTP e JSON non valido."""
    try:
        risposta = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.Timeout:
        raise ErroreMeteo(f"{cosa}: tempo massimo superato, riprovare.") from None
    except requests.RequestException as errore:
        raise ErroreMeteo(f"{cosa}: servizio irraggiungibile ({type(errore).__name__}).") from None
    if risposta.status_code != 200:
        raise ErroreMeteo(f"{cosa}: risposta HTTP {risposta.status_code}.")
    try:
        dati = risposta.json()
    except ValueError:
        raise ErroreMeteo(f"{cosa}: la risposta non e' JSON valido.") from None
    if not isinstance(dati, dict):
        raise ErroreMeteo(f"{cosa}: risposta inattesa (non e' un oggetto JSON).")
    return dati


def _numero(valore):
    # bool e' un sottotipo di int: non e' una temperatura.
    return isinstance(valore, (int, float)) and not isinstance(valore, bool)


def _nome_localita(luogo):
    # Nome, regione e paese quando ci sono, senza ripetizioni (es. "Roma" admin1 "Roma").
    pezzi = []
    for chiave in ("name", "admin1", "country"):
        valore = luogo.get(chiave)
        if isinstance(valore, str) and valore and valore not in pezzi:
            pezzi.append(valore)
    return ", ".join(pezzi)


def _cerca_localita(citta):
    dati = _chiedi_json(
        URL_GEOCODING,
        {"name": citta, "count": MAX_RISULTATI, "language": "it", "format": "json"},
        "Geocodifica",
    )
    if "results" not in dati:  # Open-Meteo omette il campo quando non trova nulla
        raise ErroreMeteo(f"Localita' non trovata: '{citta}'.")
    risultati = dati["results"]
    if not isinstance(risultati, list) or not risultati:
        raise ErroreMeteo("Geocodifica: risposta inattesa (elenco dei risultati non valido).")
    prima = risultati[0]
    if not (isinstance(prima, dict) and _numero(prima.get("latitude")) and _numero(prima.get("longitude"))
            and _nome_localita(prima)):
        raise ErroreMeteo("Geocodifica: risposta inattesa (localita' senza nome o coordinate).")
    return prima, [r for r in risultati[1:] if isinstance(r, dict) and _nome_localita(r)]


def ottieni_meteo(citta):
    """Meteo attuale della citta'. Restituisce un dizionario; solleva ErroreMeteo.

    Se piu' localita' coincidono sceglie la prima (quella che Open-Meteo ordina per rilevanza)
    e lo dichiara nel campo `note`: la scelta non e' mai silenziosa.
    """
    if not isinstance(citta, str) or not citta.strip():
        raise ErroreMeteo("citta' mancante: serve il nome di una citta'.")
    scelta, altre = _cerca_localita(citta.strip())

    dati = _chiedi_json(
        URL_PREVISIONE,
        {"latitude": scelta["latitude"], "longitude": scelta["longitude"],
         "current": "temperature_2m,weather_code", "timezone": "auto"},
        "Previsione",
    )
    corrente, scarto = dati.get("current"), dati.get("utc_offset_seconds")
    if not (isinstance(corrente, dict) and _numero(corrente.get("temperature_2m"))
            and _numero(corrente.get("weather_code")) and _numero(scarto)):
        raise ErroreMeteo("Previsione: risposta inattesa (mancano temperatura, condizioni o fuso).")
    try:
        # `time` e' l'ora locale della localita' senza fuso: il fuso si ricava da utc_offset_seconds.
        istante = datetime.fromisoformat(corrente["time"]).replace(tzinfo=timezone(timedelta(seconds=scarto)))
    except (KeyError, TypeError, ValueError):
        raise ErroreMeteo("Previsione: risposta inattesa (istante di riferimento non valido).") from None

    codice = int(corrente["weather_code"])
    esito = {
        "location": _nome_localita(scelta),
        "temperature_c": corrente["temperature_2m"],
        "conditions": CONDIZIONI.get(codice, f"condizioni non descritte (codice WMO {codice})"),
        "time": istante.isoformat(timespec="seconds"),
    }
    if altre:
        elenco = "; ".join(_nome_localita(r) for r in altre)
        esito["note"] = f"Piu' localita' con questo nome: scelta la prima ({esito['location']}). Altre: {elenco}."
    return esito
