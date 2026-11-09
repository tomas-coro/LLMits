"""Server MCP e client: processo vero via stdio, ma senza modello e senza rete."""

import asyncio
import json
import sys

import pytest

from app.client_mcp import ClientMcp, ErroreMcp


@pytest.fixture(scope="module")
def client():
    with ClientMcp() as c:  # un solo server per tutti i test del modulo
        yield c


def test_discovery_pubblica_nome_descrizione_e_schema(client):
    schemi = client.schemi
    assert sorted(s["function"]["name"] for s in schemi) == ["calculate", "convert_units", "get_weather"]
    funzione = next(s["function"] for s in schemi if s["function"]["name"] == "convert_units")
    assert all(s["type"] == "function" for s in schemi)
    # le unita' supportate devono essere documentate nel catalogo
    for unita in ("m", "km", "C", "F"):
        assert unita in funzione["description"]
    parametri = funzione["parameters"]
    assert set(parametri["properties"]) == {"value", "from_unit", "to_unit"}
    assert parametri["properties"]["value"]["type"] == "number"
    assert set(parametri["required"]) == {"value", "from_unit", "to_unit"}
    assert client.ha_tool("convert_units") and not client.ha_tool("get_current_time")


def test_discovery_meteo(client):
    funzione = next(s["function"] for s in client.schemi if s["function"]["name"] == "get_weather")
    assert "Open-Meteo" in funzione["description"] and "°C" in funzione["description"]
    parametri = funzione["parameters"]
    assert set(parametri["properties"]) == {"city"}
    assert parametri["properties"]["city"]["type"] == "string"
    assert parametri["required"] == ["city"]
    assert client.ha_tool("get_weather")


def test_discovery_calcolatrice(client):
    funzione = next(s["function"] for s in client.schemi if s["function"]["name"] == "calculate")
    for operatore in ("+", "-", "*", "/", "**", "%"):  # gli operatori ammessi vanno documentati
        assert operatore in funzione["description"]
    parametri = funzione["parameters"]
    assert set(parametri["properties"]) == {"expression"}
    assert parametri["properties"]["expression"]["type"] == "string"
    assert parametri["required"] == ["expression"]
    assert client.ha_tool("calculate")


def test_calcolatrice_chiamata_diretta_valida(client):
    testo = client.chiama("calculate", {"expression": "(12 + 8) * 7 - 5"})
    assert json.loads(testo) == {"value": 135.0, "expression": "(12 + 8) * 7 - 5"}


@pytest.mark.parametrize(
    "espressione, atteso",
    [("1 / 0", "divisione per zero"), ("9 ** 9 ** 9", "esponente"), ("__import__('os')", "non ammesso")],
)
def test_calcolatrice_errore_non_e_un_successo(client, espressione, atteso):
    testo = client.chiama("calculate", {"expression": espressione})
    assert testo.startswith("Errore") and atteso in testo


def test_meteo_chiamata_diretta_senza_citta_e_un_errore_senza_rete(client):
    # La validazione avviene prima di qualsiasi richiesta HTTP: la prova non usa la rete.
    testo = client.chiama("get_weather", {"city": "  "})
    assert testo.startswith("Errore") and "citta" in testo
    assert client.chiama("get_weather", {}).startswith("Errore")  # argomento mancante: lo schema lo rifiuta


def _chiama_in_processo(argomenti):
    """Chiama get_weather nello stesso processo (cosi' requests e' simulabile) passando dal protocollo MCP."""
    from fastmcp import Client

    from app.mcp_server import mcp

    async def corpo():
        async with Client(mcp) as c:
            return await c.call_tool("get_weather", argomenti, raise_on_error=False)

    return asyncio.run(corpo())


def test_meteo_tool_con_http_simulato_restituisce_json(monkeypatch):
    from tests.test_meteo import PREVISIONE, ROMA, RispostaFinta, simula

    simula(monkeypatch, RispostaFinta({"results": [ROMA]}), RispostaFinta(PREVISIONE))
    risultato = _chiama_in_processo({"city": "Roma"})
    assert not risultato.is_error
    dati = json.loads(risultato.content[0].text)
    assert dati["location"] == "Roma, Lazio, Italia" and dati["temperature_c"] == 17.1


def test_meteo_tool_con_errore_http_non_e_un_successo(monkeypatch):
    from tests.test_meteo import RispostaFinta, simula

    simula(monkeypatch, RispostaFinta({}, status=503))
    risultato = _chiama_in_processo({"city": "Roma"})
    assert risultato.is_error and "HTTP 503" in risultato.content[0].text


def test_chiamata_diretta_valida(client):
    testo = client.chiama("convert_units", {"value": 100, "from_unit": "C", "to_unit": "F"})
    assert json.loads(testo) == {"value": 212.0, "unit": "F"}


@pytest.mark.parametrize(
    "argomenti, atteso",
    [
        ({"value": 1, "from_unit": "km", "to_unit": "C"}, "grandezze diverse"),
        ({"value": 1, "from_unit": "miglia", "to_unit": "km"}, "sconosciuta 'miglia'"),
        ({"value": "abc", "from_unit": "km", "to_unit": "m"}, "valid number"),  # rifiutato dallo schema
        ({"value": 1}, "from_unit"),  # argomenti mancanti
    ],
)
def test_errori_del_tool_restano_errori(client, argomenti, atteso):
    testo = client.chiama("convert_units", argomenti)
    assert testo.startswith("Errore")
    assert atteso in testo


def test_tool_inesistente_e_un_errore(client):
    assert client.chiama("non_esiste", {}).startswith("Errore")


def test_dopo_la_chiusura_non_si_chiama_un_client_disconnesso():
    c = ClientMcp()
    c.avvia()
    c.chiudi()
    c.chiudi()  # idempotente
    assert c.chiama("convert_units", {"value": 1, "from_unit": "m", "to_unit": "km"}) == (
        "Errore: server MCP non disponibile."
    )


def test_chiamata_prima_dell_avvio_e_un_errore():
    assert ClientMcp().chiama("convert_units", {}).startswith("Errore")


def test_server_che_non_parte_da_errore_leggibile():
    c = ClientMcp(comando=sys.executable, args=("-c", "import sys; sys.exit(3)"), timeout=10)
    with pytest.raises(ErroreMcp, match="Server MCP non avviato"):
        c.avvia()
