"""Prova REALE con LM Studio: si attiva solo con PROVA_REALE=1 (serve il server acceso)."""

import json
import os
import re

import pytest
from dotenv import load_dotenv

from app.cli import SYSTEM_PROMPT
from app.client_mcp import ClientMcp
from app.grafo import costruisci_grafo
from app.modello import chiama_modello

pytestmark = pytest.mark.skipif(
    os.environ.get("PROVA_REALE") != "1",
    reason="Prova reale: attivare con PROVA_REALE=1 (serve LM Studio acceso)",
)


def test_il_modello_chiama_davvero_l_orologio():
    load_dotenv()
    grafo = costruisci_grafo(chiama_modello)
    messaggi = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Che ore sono a Tokyo? Usa lo strumento."},
    ]
    out = grafo.invoke({"messages": messaggi, "passaggi": 0})
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    assert tool, "Il modello non ha chiamato nessuno strumento: registrare il blocco, non dichiarare completato."
    assert re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+09:00$", tool[0]["content"])
    assert out["messages"][-1]["role"] == "assistant" and out["messages"][-1]["content"]


def test_il_modello_sceglie_davvero_convert_units():
    """Il server MCP e' vero (stdio) e il modello e' LM Studio: verifica la scelta dello strumento, non solo il calcolo."""
    load_dotenv()
    messaggi = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Quanti gradi Fahrenheit sono 100 gradi Celsius? Usa lo strumento."},
    ]
    with ClientMcp() as client:
        grafo = costruisci_grafo(lambda m: chiama_modello(m, client.schemi), client_mcp=client)
        out = grafo.invoke({"messages": messaggi, "passaggi": 0})
    richieste = [c for m in out["messages"] if m.get("tool_calls") for c in m["tool_calls"]]
    assert [c["function"]["name"] for c in richieste][:1] == ["convert_units"], (
        "Il modello non ha scelto convert_units: registrare il blocco, non dichiarare completato."
    )
    argomenti = json.loads(richieste[0]["function"]["arguments"])
    assert (argomenti["value"], argomenti["from_unit"], argomenti["to_unit"]) == (100, "C", "F")
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    assert json.loads(tool[0]["content"]) == {"value": 212.0, "unit": "F"}  # eseguito davvero dal server MCP
    assert tool[0]["tool_call_id"] == richieste[0]["id"]
    finale = out["messages"][-1]
    assert finale["role"] == "assistant" and "212" in finale["content"]  # il risultato entra nella risposta


def test_il_modello_sceglie_davvero_get_weather():
    """LM Studio vero + server MCP vero + Open-Meteo vero (serve la rete): il meteo e' davvero consultato."""
    load_dotenv()
    messaggi = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Che tempo fa adesso a Roma? Usa lo strumento."},
    ]
    with ClientMcp() as client:
        grafo = costruisci_grafo(lambda m: chiama_modello(m, client.schemi), client_mcp=client)
        out = grafo.invoke({"messages": messaggi, "passaggi": 0})
    richieste = [c for m in out["messages"] if m.get("tool_calls") for c in m["tool_calls"]]
    assert [c["function"]["name"] for c in richieste][:1] == ["get_weather"], (
        "Il modello non ha scelto get_weather: registrare il blocco, non dichiarare completato."
    )
    assert "roma" in json.loads(richieste[0]["function"]["arguments"])["city"].lower()
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    dati = json.loads(tool[0]["content"])  # se Open-Meteo fallisce qui c'e' "Errore: ...", non un JSON
    assert tool[0]["tool_call_id"] == richieste[0]["id"]
    assert "Roma" in dati["location"] and isinstance(dati["temperature_c"], (int, float))
    finale = out["messages"][-1]
    assert finale["role"] == "assistant" and finale["content"]
