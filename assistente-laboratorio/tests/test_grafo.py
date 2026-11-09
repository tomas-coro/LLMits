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


# --- strumenti MCP (incremento 1: convertitore) ----------------------------------------------


class ClientFinto:
    """Sostituisce il client MCP: ricorda le chiamate e risponde con testi preparati."""

    def __init__(self, risposte=None):
        self.risposte = risposte or {}
        self.chiamate = []

    def ha_tool(self, nome):
        return nome in ("convert_units", "get_weather")

    def chiama(self, nome, argomenti):
        self.chiamate.append((nome, argomenti))
        return self.risposte.get(nome, '{"value": 212.0, "unit": "F"}')


def richieste_multiple(*chiamate):
    """Un solo messaggio 'assistant' con piu' tool_calls: (id, nome, argomenti)."""
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": i, "type": "function", "function": {"name": n, "arguments": a}} for i, n, a in chiamate
        ],
    }


CONVERSIONE = '{"value": 100, "from_unit": "C", "to_unit": "F"}'


def test_tool_mcp_inoltrato_al_client_con_risultato_correlato():
    client = ClientFinto()
    modello = ModelloFinto([richiesta_tool("mcp-1", CONVERSIONE, nome="convert_units"), risposta("100 C sono 212 F")])
    out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "100 C in F?"}])
    assert client.chiamate == [("convert_units", {"value": 100, "from_unit": "C", "to_unit": "F"})]
    assert [m["role"] for m in out["messages"]] == ["user", "assistant", "tool", "assistant"]
    assert out["messages"][2] == {"role": "tool", "tool_call_id": "mcp-1", "content": '{"value": 212.0, "unit": "F"}'}
    assert modello.chiamate[1][-1]["tool_call_id"] == "mcp-1"  # il modello rivede il risultato


def test_orologio_e_convertitore_nello_stesso_turno():
    client = ClientFinto()
    modello = ModelloFinto(
        [
            richieste_multiple(
                ("a", "get_current_time", '{"timezone": "Asia/Tokyo"}'), ("b", "convert_units", CONVERSIONE)
            ),
            risposta("A Tokyo sono le 21:00 e 100 C sono 212 F"),
        ]
    )
    out = avvia(
        costruisci_grafo(modello, adesso_fn=ora_fissa, client_mcp=client), [{"role": "user", "content": "x"}]
    )
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    assert [(m["tool_call_id"], m["content"]) for m in tool] == [
        ("a", "2026-11-08T21:00:00+09:00"),  # l'orologio resta locale
        ("b", '{"value": 212.0, "unit": "F"}'),  # il convertitore va al client MCP
    ]
    assert [c[0] for c in client.chiamate] == ["convert_units"]  # l'orologio non passa dal client


def test_errore_del_tool_mcp_non_diventa_successo():
    client = ClientFinto({"convert_units": "Errore: conversione tra grandezze diverse non possibile."})
    modello = ModelloFinto([richiesta_tool("m", CONVERSIONE, nome="convert_units"), risposta("Non si puo'")])
    out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "x"}])
    assert out["messages"][2]["content"].startswith("Errore:")
    assert out["messages"][-1]["content"] == "Non si puo'"  # il turno prosegue: la sessione non si ferma


def test_argomenti_rotti_per_tool_mcp_non_arrivano_al_client():
    client = ClientFinto()
    modello = ModelloFinto(
        [richiesta_tool("m1", "non json", nome="convert_units"), richiesta_tool("m2", "[1]", nome="convert_units"), risposta("ok")]
    )
    out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "x"}])
    tool = [m["content"] for m in out["messages"] if m["role"] == "tool"]
    assert all(t.startswith("Errore: argomenti non validi") for t in tool)
    assert client.chiamate == []


def test_tool_sconosciuto_con_client_attivo_resta_errore():
    client = ClientFinto()
    modello = ModelloFinto([richiesta_tool("x", "{}", nome="vola_su_marte"), risposta("ok")])
    out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "x"}])
    assert out["messages"][2]["content"].startswith("Errore: strumento sconosciuto")
    assert client.chiamate == []


def test_limite_passaggi_vale_anche_per_tool_mcp():
    client = ClientFinto()
    modello = ModelloFinto([richiesta_tool(f"i{i}", CONVERSIONE, nome="convert_units") for i in range(MAX_PASSAGGI + 3)])
    out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "x"}])
    assert len(modello.chiamate) == MAX_PASSAGGI
    assert "limite" in out["messages"][-1]["content"]
    ids_richiesti = [c["id"] for m in out["messages"] if m.get("tool_calls") for c in m["tool_calls"]]
    ids_risposti = [m["tool_call_id"] for m in out["messages"] if m["role"] == "tool"]
    assert ids_richiesti == ids_risposti


def test_log_di_richiesta_e_esito_per_tool_mcp(caplog):
    caplog.set_level("INFO", logger="assistente")
    modello = ModelloFinto([richiesta_tool("m", CONVERSIONE, nome="convert_units"), risposta("ok")])
    avvia(costruisci_grafo(modello, client_mcp=ClientFinto()), [{"role": "user", "content": "x"}])
    assert f"strumento richiesto: convert_units {CONVERSIONE}" in caplog.text
    assert 'strumento risultato: {"value": 212.0, "unit": "F"}' in caplog.text


def test_grafo_con_server_mcp_vero_e_modello_finto():
    from app.client_mcp import ClientMcp

    modello = ModelloFinto([richiesta_tool("v", CONVERSIONE, nome="convert_units"), risposta("212 F")])
    with ClientMcp() as client:
        out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "100 C in F?"}])
    assert out["messages"][2]["tool_call_id"] == "v"
    assert out["messages"][2]["content"] == '{"value":212.0,"unit":"F"}'


METEO = '{"location": "Roma, Lazio, Italia", "temperature_c": 17.1, "conditions": "coperto", "time": "2026-11-09T14:45:00+01:00"}'


def test_meteo_orologio_e_convertitore_nello_stesso_turno():
    client = ClientFinto({"get_weather": METEO})
    modello = ModelloFinto(
        [
            richieste_multiple(
                ("a", "get_current_time", '{"timezone": "Asia/Tokyo"}'),
                ("b", "get_weather", '{"city": "Roma"}'),
                ("c", "convert_units", CONVERSIONE),
            ),
            risposta("ok"),
        ]
    )
    out = avvia(costruisci_grafo(modello, adesso_fn=ora_fissa, client_mcp=client), [{"role": "user", "content": "x"}])
    tool = [(m["tool_call_id"], m["content"]) for m in out["messages"] if m["role"] == "tool"]
    assert tool == [("a", "2026-11-08T21:00:00+09:00"), ("b", METEO), ("c", '{"value": 212.0, "unit": "F"}')]
    assert client.chiamate == [("get_weather", {"city": "Roma"}), ("convert_units", {"value": 100, "from_unit": "C", "to_unit": "F"})]


def test_errore_del_meteo_non_diventa_successo_e_il_turno_prosegue():
    client = ClientFinto({"get_weather": "Errore: Localita' non trovata: 'Xyz'."})
    modello = ModelloFinto([richiesta_tool("w", '{"city": "Xyz"}', nome="get_weather"), risposta("Citta' non trovata")])
    out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "x"}])
    assert out["messages"][2] == {"role": "tool", "tool_call_id": "w", "content": "Errore: Localita' non trovata: 'Xyz'."}
    assert out["messages"][-1]["content"] == "Citta' non trovata"


def test_meteo_con_server_mcp_vero_errore_correlato_senza_rete():
    from app.client_mcp import ClientMcp

    modello = ModelloFinto([richiesta_tool("w", '{"city": ""}', nome="get_weather"), risposta("serve una citta'")])
    with ClientMcp() as client:
        out = avvia(costruisci_grafo(modello, client_mcp=client), [{"role": "user", "content": "meteo?"}])
    assert out["messages"][2]["tool_call_id"] == "w" and out["messages"][2]["content"].startswith("Errore")
