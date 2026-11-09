"""Strumenti che il modello puo' chiedere al programma (qui: solo l'orologio).

Il modello NON conosce l'ora: chiede lo strumento, e' questo codice a leggere
davvero l'orologio e a restituire il risultato.
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def adesso():
    """Istante corrente in UTC. Nei test si passa al suo posto una funzione con ora fissa."""
    return datetime.now(timezone.utc)


# Descrizione dello strumento che mandiamo al modello: nome, a cosa serve, parametri.
SCHEMI = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Restituisce data e ora attuali in un fuso orario IANA (es. Europe/Rome).",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Nome IANA del fuso orario, es. Europe/Rome o Asia/Tokyo.",
                    }
                },
                "required": ["timezone"],
            },
        },
    }
]


def get_current_time(fuso, adesso_fn=adesso):
    """Ora attuale nel fuso richiesto, in formato ISO. Errore chiaro se il fuso manca o non esiste."""
    if not fuso or not isinstance(fuso, str):
        return "Errore: il parametro 'timezone' e' obbligatorio (es. Europe/Rome)."
    try:
        zona = ZoneInfo(fuso)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return f"Errore: fuso orario sconosciuto '{fuso}'. Usa un nome IANA, es. Europe/Rome."
    return adesso_fn().astimezone(zona).isoformat(timespec="seconds")


def leggi_argomenti(argomenti):
    """Legge la stringa JSON inviata dal modello. Restituisce (dizionario, None) oppure (None, testo di errore)."""
    try:
        args = json.loads(argomenti) if argomenti else {}
    except json.JSONDecodeError:
        return None, "Errore: argomenti non validi (JSON non leggibile)."
    if not isinstance(args, dict):
        return None, "Errore: argomenti non validi (atteso un oggetto JSON)."
    return args, None


def esegui_tool(nome, argomenti, adesso_fn=adesso):
    """Esegue lo strumento richiesto dal modello. `argomenti` e' la stringa JSON inviata dal modello.

    Restituisce sempre un testo: in caso di problema e' un errore leggibile, mai un successo finto.
    """
    if nome != "get_current_time":
        return f"Errore: strumento sconosciuto '{nome}'."
    args, errore = leggi_argomenti(argomenti)
    if errore:
        return errore
    return get_current_time(args.get("timezone"), adesso_fn)
