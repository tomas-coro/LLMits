from app import cli


def test_cronologia_cresce_tra_i_turni_e_il_turno_fallito_non_si_salva(monkeypatch, capsys):
    ricevuti = []

    def modello_finto(messages):
        ricevuti.append([m["content"] for m in messages])
        if len(ricevuti) == 2:
            raise cli.ErroreModello("Connessione fallita: prova")
        return {"role": "assistant", "content": f"risposta{len(ricevuti)}"}

    monkeypatch.setenv("LM_BASE_URL", "x")
    monkeypatch.setenv("LM_MODEL", "y")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "chiama_modello", modello_finto)
    domande = iter(["uno", "due", "tre", "esci"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(domande))

    assert cli.main() == 0
    # turno 1 ok; turno 2 fallisce (non salvato); turno 3 vede solo il turno 1
    assert ricevuti[2][1:] == ["uno", "risposta1", "tre"]
    assert "Connessione fallita: prova" in capsys.readouterr().out


def test_variabili_mancanti_danno_errore_chiaro(monkeypatch, capsys):
    monkeypatch.delenv("LM_BASE_URL", raising=False)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    assert cli.main() == 1
    assert "LM_BASE_URL mancante" in capsys.readouterr().out
