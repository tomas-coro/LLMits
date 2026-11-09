import pytest
import requests

from app import modello
from app.modello import ErroreModello, chiama_modello


class RispostaFinta:
    def __init__(self, corpo, status=200):
        self._corpo, self.status_code, self.text = corpo, status, str(corpo)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError()

    def json(self):
        return self._corpo


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setenv("LM_BASE_URL", "http://finto/v1")
    monkeypatch.setenv("LM_MODEL", "modello-finto")


def corpo(messaggio):
    return {"choices": [{"message": messaggio}]}


def test_toglie_i_campi_vuoti_di_lm_studio(monkeypatch):
    grezzo = {"role": "assistant", "content": "Ciao", "reasoning_content": "", "tool_calls": []}
    monkeypatch.setattr(modello.requests, "post", lambda *a, **k: RispostaFinta(corpo(grezzo)))
    assert chiama_modello([]) == {"role": "assistant", "content": "Ciao"}


def test_tiene_le_richieste_di_tool(monkeypatch):
    chiamate = [{"id": "1", "type": "function", "function": {"name": "get_current_time", "arguments": "{}"}}]
    grezzo = {"role": "assistant", "content": "", "tool_calls": chiamate}
    monkeypatch.setattr(modello.requests, "post", lambda *a, **k: RispostaFinta(corpo(grezzo)))
    assert chiama_modello([])["tool_calls"] == chiamate


@pytest.mark.parametrize(
    "eccezione, atteso",
    [
        (requests.exceptions.Timeout(), "Attesa scaduta"),
        (requests.exceptions.ConnectionError(), "Connessione fallita"),
    ],
)
def test_errori_di_rete_diventano_messaggi_leggibili(monkeypatch, eccezione, atteso):
    def solleva(*a, **k):
        raise eccezione

    monkeypatch.setattr(modello.requests, "post", solleva)
    with pytest.raises(ErroreModello, match=atteso):
        chiama_modello([])


def test_errore_http_mostra_stato_e_testo(monkeypatch):
    monkeypatch.setattr(modello.requests, "post", lambda *a, **k: RispostaFinta({"error": "x"}, status=404))
    with pytest.raises(ErroreModello, match="Errore HTTP: 404"):
        chiama_modello([])


def test_il_payload_include_lo_schema_dell_orologio(monkeypatch):
    visto = {}

    def post_finto(url, json, timeout):
        visto["json"] = json
        return RispostaFinta(corpo({"role": "assistant", "content": "ok"}))

    monkeypatch.setattr(modello.requests, "post", post_finto)
    chiama_modello([])
    assert visto["json"]["tools"][0]["function"]["name"] == "get_current_time"


def test_il_payload_unisce_orologio_e_schemi_del_server(monkeypatch):
    visto = {}

    def post_finto(url, json, timeout):
        visto["json"] = json
        return RispostaFinta(corpo({"role": "assistant", "content": "ok"}))

    schema_mcp = {"type": "function", "function": {"name": "convert_units", "description": "", "parameters": {}}}
    monkeypatch.setattr(modello.requests, "post", post_finto)
    chiama_modello([], [schema_mcp])
    assert [t["function"]["name"] for t in visto["json"]["tools"]] == ["get_current_time", "convert_units"]
    chiama_modello([])  # senza server MCP: solo l'orologio, e SCHEMI non viene modificato
    assert [t["function"]["name"] for t in visto["json"]["tools"]] == ["get_current_time"]
