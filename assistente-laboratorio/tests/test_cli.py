import pytest

from app import cli


class ClientFinto:
    """Sostituisce ClientMcp: niente processo vero, ricorda se e' stato avviato e chiuso."""

    def __init__(self, errore_avvio=None):
        self.errore_avvio, self.avviato, self.chiuso = errore_avvio, False, False
        self.schemi = [{"type": "function", "function": {"name": "convert_units"}}]

    def avvia(self):
        if self.errore_avvio:
            raise self.errore_avvio
        self.avviato = True

    def chiudi(self):
        self.chiuso = True

    def ha_tool(self, nome):
        return nome == "convert_units"


def test_cronologia_cresce_tra_i_turni_e_il_turno_fallito_non_si_salva(monkeypatch, capsys):
    ricevuti = []

    def modello_finto(messages, schemi_extra=()):
        ricevuti.append([m["content"] for m in messages])
        if len(ricevuti) == 2:
            raise cli.ErroreModello("Connessione fallita: prova")
        return {"role": "assistant", "content": f"risposta{len(ricevuti)}"}

    monkeypatch.setenv("LM_BASE_URL", "x")
    monkeypatch.setenv("LM_MODEL", "y")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "chiama_modello", modello_finto)
    client = ClientFinto()
    monkeypatch.setattr(cli, "ClientMcp", lambda: client)
    domande = iter(["uno", "due", "tre", "esci"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(domande))

    assert cli.main() == 0
    # turno 1 ok; turno 2 fallisce (non salvato); turno 3 vede solo il turno 1
    assert ricevuti[2][1:] == ["uno", "risposta1", "tre"]
    assert "Connessione fallita: prova" in capsys.readouterr().out
    assert client.avviato and client.chiuso  # il server MCP si apre all'avvio e si chiude all'uscita


def test_variabili_mancanti_danno_errore_chiaro(monkeypatch, capsys):
    monkeypatch.delenv("LM_BASE_URL", raising=False)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    assert cli.main() == 1
    assert "LM_BASE_URL mancante" in capsys.readouterr().out


def test_il_server_mcp_viene_chiuso_anche_se_la_sessione_va_in_errore(monkeypatch):
    client = ClientFinto()
    monkeypatch.setenv("LM_BASE_URL", "x")
    monkeypatch.setenv("LM_MODEL", "y")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ClientMcp", lambda: client)
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        cli.main()
    except KeyboardInterrupt:
        pass
    assert client.chiuso


def test_avvio_mcp_fallito_da_messaggio_chiaro_e_non_parte_la_sessione(monkeypatch, capsys):
    client = ClientFinto(errore_avvio=cli.ErroreMcp("Server MCP non avviato: prova"))
    monkeypatch.setenv("LM_BASE_URL", "x")
    monkeypatch.setenv("LM_MODEL", "y")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ClientMcp", lambda: client)
    monkeypatch.setattr("builtins.input", lambda prompt="": pytest.fail("la sessione non doveva partire"))
    assert cli.main() == 1
    assert "Server MCP non avviato: prova" in capsys.readouterr().out
