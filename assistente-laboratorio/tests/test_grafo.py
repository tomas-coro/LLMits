from datetime import datetime, timezone

from app.grafo import MAX_PASSAGGI, costruisci_grafo


class ModelloFinto:
    """Sostituisce il modello vero: risponde con messaggi preparati e ricorda cosa ha ricevuto."""

    def __init__(self, risposte):
        self.risposte = list(risposte)
        self.chiamate = []

    def __call__(self, messages):
        self.chiamate.append(list(messages))
        return self.risposte.pop(0)


def risposta(testo):
    return {"role": "assistant", "content": testo}


def avvia(grafo, messages):
    return grafo.invoke({"messages": messages, "passaggi": 0})


def test_percorso_fisso_senza_tool():
    grafo = costruisci_grafo(ModelloFinto([risposta("Ciao!")]))
    out = avvia(grafo, [{"role": "user", "content": "Ciao"}])
    assert out["messages"][-1] == risposta("Ciao!")
    assert out["passaggi"] == 1


def richiesta_tool(id_chiamata, argomenti='{"timezone": "Asia/Tokyo"}', nome="get_current_time"):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": id_chiamata, "type": "function", "function": {"name": nome, "arguments": argomenti}}],
    }


def ora_fissa():
    return datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)


def test_cronologia_tra_due_turni():
    modello = ModelloFinto([risposta("Piacere Tomas"), risposta("Ti chiami Tomas")])
    grafo = costruisci_grafo(modello)
    turno1 = avvia(grafo, [{"role": "user", "content": "Mi chiamo Tomas"}])
    turno2 = avvia(grafo, turno1["messages"] + [{"role": "user", "content": "Come mi chiamo?"}])
    contenuti = [m["content"] for m in modello.chiamate[1]]
    assert "Mi chiamo Tomas" in contenuti and "Piacere Tomas" in contenuti
    assert turno2["messages"][-1]["content"] == "Ti chiami Tomas"


def test_bivio_passa_da_tools_e_torna_al_modello():
    modello = ModelloFinto([richiesta_tool("id-1"), risposta("A Tokyo sono le 21:00")])
    grafo = costruisci_grafo(modello, adesso_fn=ora_fissa)
    out = avvia(grafo, [{"role": "user", "content": "Che ore sono a Tokyo?"}])
    ruoli = [m["role"] for m in out["messages"]]
    assert ruoli == ["user", "assistant", "tool", "assistant"]
    assert out["messages"][2]["tool_call_id"] == "id-1"  # risultato legato alla richiesta giusta
    assert out["messages"][2]["content"] == "2026-11-08T21:00:00+09:00"  # 12:00 UTC = 21:00 a Tokyo
    assert len(modello.chiamate) == 2


def test_fuso_sconosciuto_da_errore_chiaro_non_ora_inventata():
    modello = ModelloFinto([richiesta_tool("id-2", '{"timezone": "Marte/Olympus"}'), risposta("Fuso non valido")])
    grafo = costruisci_grafo(modello, adesso_fn=ora_fissa)
    out = avvia(grafo, [{"role": "user", "content": "Che ore sono su Marte?"}])
    assert out["messages"][2]["content"].startswith("Errore: fuso orario sconosciuto")


def test_fuso_mancante_da_errore_chiaro():
    modello = ModelloFinto([richiesta_tool("id-3", "{}"), risposta("Serve un fuso")])
    grafo = costruisci_grafo(modello, adesso_fn=ora_fissa)
    out = avvia(grafo, [{"role": "user", "content": "Che ora e'?"}])
    assert "obbligatorio" in out["messages"][2]["content"]


def test_strumento_sconosciuto_e_argomenti_rotti_danno_errore():
    modello = ModelloFinto(
        [richiesta_tool("id-4", "{}", nome="vola_su_marte"), richiesta_tool("id-5", "non json"), risposta("ok")]
    )
    grafo = costruisci_grafo(modello, adesso_fn=ora_fissa)
    out = avvia(grafo, [{"role": "user", "content": "x"}])
    tool = [m["content"] for m in out["messages"] if m["role"] == "tool"]
    assert tool[0].startswith("Errore: strumento sconosciuto")
    assert tool[1].startswith("Errore: argomenti non validi")


def test_limite_passaggi_ferma_il_giro():
    modello = ModelloFinto([richiesta_tool(f"id-{i}") for i in range(MAX_PASSAGGI + 3)])
    grafo = costruisci_grafo(modello, adesso_fn=ora_fissa)
    out = avvia(grafo, [{"role": "user", "content": "Che ore sono?"}])
    assert len(modello.chiamate) == MAX_PASSAGGI
    assert "limite" in out["messages"][-1]["content"]
    # ogni richiesta ha il suo risultato: la cronologia resta valida per il turno dopo
    ids_richiesti = [c["id"] for m in out["messages"] if m.get("tool_calls") for c in m["tool_calls"]]
    ids_risposti = [m["tool_call_id"] for m in out["messages"] if m["role"] == "tool"]
    assert ids_richiesti == ids_risposti


def test_chiamata_allo_strumento_e_visibile_nei_log(caplog):
    # Richiesta, esecuzione e risultato devono lasciare traccia (requisito della Lezione 4).
    caplog.set_level("INFO", logger="assistente")
    modello = ModelloFinto([richiesta_tool("id-1"), risposta("A Tokyo sono le 21:00")])
    avvia(costruisci_grafo(modello, adesso_fn=ora_fissa), [{"role": "user", "content": "Che ore sono a Tokyo?"}])
    testo = caplog.text
    assert "nodo llm: inizio chiamata 1" in testo and "nodo llm: fine chiamata 1" in testo
    assert 'strumento richiesto: get_current_time {"timezone": "Asia/Tokyo"}' in testo
    assert "strumento risultato: 2026-11-08T21:00:00+09:00" in testo
