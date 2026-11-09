"""Server chat vero su porta effimera, grafo finto: nessuna chiamata a LM Studio."""

import http.client
import json
import threading
from http.server import HTTPServer

import pytest

from app.modello import ErroreModello
from app.web import PAGINA, crea_handler


class GrafoFinto:
    def __init__(self):
        self.ricevuti = []
        self.fallisce = False

    def invoke(self, stato):
        self.ricevuti.append(stato)
        if self.fallisce:
            raise ErroreModello("LM Studio non disponibile")
        return {"messages": stato["messages"] + [{"role": "assistant", "content": "<b>risposta</b>"}]}


@pytest.fixture
def web():
    grafo = GrafoFinto()
    server = HTTPServer(("127.0.0.1", 0), crea_handler(grafo))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server.server_port, grafo
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def richiesta(porta, metodo, percorso, dati=None, headers=None):
    connessione = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    connessione.request(metodo, percorso, body=dati, headers={"Host": f"127.0.0.1:{porta}", **(headers or {})})
    risposta = connessione.getresponse()
    stato, corpo = risposta.status, risposta.read()
    connessione.close()
    return stato, corpo


def invia(porta, testo, headers=None):
    return richiesta(porta, "POST", "/api/chat", json.dumps({"message": testo}), {"Content-Type": "application/json", **(headers or {})})


def test_domande_cronologia_e_ricarica(web):
    porta, grafo = web
    assert json.loads(richiesta(porta, "GET", "/api/messages")[1]) == {"messages": []}
    assert json.loads(invia(porta, "prima")[1]) == {"answer": "<b>risposta</b>"}
    invia(porta, "seconda")
    assert [m["content"] for m in grafo.ricevuti[1]["messages"]] == [
        grafo.ricevuti[0]["messages"][0]["content"], "prima", "<b>risposta</b>", "seconda"
    ]
    visibili = json.loads(richiesta(porta, "GET", "/api/messages")[1])["messages"]
    assert [m["content"] for m in visibili] == ["prima", "<b>risposta</b>", "seconda", "<b>risposta</b>"]


def test_errore_non_salva_il_turno(web):
    porta, grafo = web
    grafo.fallisce = True
    stato, corpo = invia(porta, "fallisce")
    assert stato == 502 and "LM Studio" in json.loads(corpo)["error"]
    grafo.fallisce = False
    invia(porta, "riesce")
    assert [m["content"] for m in grafo.ricevuti[-1]["messages"]][1:] == ["riesce"]


@pytest.mark.parametrize("dati,headers,stato", [
    (b'{', {"Content-Type": "application/json"}, 400),
    (b'{"message":"   "}', {"Content-Type": "application/json"}, 400),
    (b'[]', {"Content-Type": "application/json"}, 400),
    (b'{"message":"ciao"}', {"Content-Type": "text/plain"}, 415),
    (b'x' * 4097, {"Content-Type": "application/json"}, 400),
    (b'{"message":"ciao"}', {"Content-Type": "application/json", "Origin": "https://altro.example"}, 403),
    (b'{"message":"ciao"}', {"Content-Type": "application/json", "Host": "altro.example"}, 403),
])
def test_richieste_non_valide(web, dati, headers, stato):
    porta, grafo = web
    assert richiesta(porta, "POST", "/api/chat", dati, headers)[0] == stato
    assert not grafo.ricevuti


def test_pagina_locale_non_interpreta_risposte_come_html(web):
    porta, _ = web
    stato, corpo = richiesta(porta, "GET", "/")
    assert stato == 200 and b'id="question"' in corpo
    assert b'body.textContent = text' in corpo
    assert b'innerHTML' not in corpo
    assert PAGINA.exists()
