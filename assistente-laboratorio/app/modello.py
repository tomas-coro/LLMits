"""Collegamento a LM Studio: l'unico file che usa la rete."""

import os

import requests

from app.strumenti import SCHEMI


class ErroreModello(Exception):
    """Problema nel parlare col modello, con un messaggio gia' leggibile per l'utente."""


def chiama_modello(messages):
    """Invia la conversazione a LM Studio e restituisce il messaggio 'assistant' (pulito)."""
    # os.environ[...] da' KeyError se manca la variabile: errore visibile, non un default silenzioso.
    base_url = os.environ["LM_BASE_URL"]
    payload = {
        "model": os.environ["LM_MODEL"],
        "messages": messages,
        "tools": SCHEMI,
        "temperature": 0.3,
        "max_tokens": 300,
        "reasoning_effort": "none",  # senza, il modello puo' consumare i token ragionando e rispondere vuoto
        "stream": False,
    }
    try:
        risposta = requests.post(f"{base_url}/chat/completions", json=payload, timeout=120)
        risposta.raise_for_status()
        grezzo = risposta.json()["choices"][0]["message"]
    except requests.exceptions.Timeout:
        raise ErroreModello("Attesa scaduta: controllare server, carico e tempi.") from None
    except requests.exceptions.ConnectionError:
        raise ErroreModello("Connessione fallita: controllare server, URL e porta.") from None
    except requests.exceptions.HTTPError:
        raise ErroreModello(f"Errore HTTP: {risposta.status_code} {risposta.text}") from None

    # LM Studio manda anche campi vuoti (reasoning_content, tool_calls: []): teniamo solo il necessario.
    pulito = {"role": "assistant", "content": grezzo.get("content") or ""}
    if grezzo.get("tool_calls"):
        pulito["tool_calls"] = grezzo["tool_calls"]
    return pulito
