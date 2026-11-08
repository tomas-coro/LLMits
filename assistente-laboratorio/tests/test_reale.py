"""Prova REALE con LM Studio: si attiva solo con PROVA_REALE=1 (serve il server acceso)."""

import os
import re

import pytest
from dotenv import load_dotenv

from app.cli import SYSTEM_PROMPT
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
