"""Il grafo LangGraph: stato, nodi e instradamento.

    START -> llm -> [il modello chiede un tool?]
                       si -> tools -> llm
                       no -> END
    (se i passaggi superano il limite: llm -> limite -> END)
"""

import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.strumenti import adesso, esegui_tool

log = logging.getLogger("assistente")  # traccia visibile: chiamate al modello e agli strumenti

MAX_PASSAGGI = 5  # chiamate al modello consentite per ogni domanda dell'utente


class Stato(TypedDict):
    messages: list  # cronologia: system, user, assistant, tool (formato OpenAI)
    passaggi: int  # chiamate al modello fatte nella domanda corrente


def costruisci_grafo(modello_fn, adesso_fn=adesso):
    """Costruisce il grafo. `modello_fn(messages)` restituisce il messaggio 'assistant'.

    Riceverla come parametro permette ai test di usare un modello finto.
    """

    def nodo_llm(stato):
        n = stato["passaggi"] + 1
        log.info("nodo llm: inizio chiamata %d", n)
        risposta = modello_fn(stato["messages"])
        log.info("nodo llm: fine chiamata %d", n)
        return {"messages": stato["messages"] + [risposta], "passaggi": stato["passaggi"] + 1}

    def nodo_tools(stato):
        # Un risultato per ogni richiesta, legato dal tool_call_id della richiesta.
        risultati = []
        for chiamata in stato["messages"][-1]["tool_calls"]:
            nome, argomenti = chiamata["function"]["name"], chiamata["function"]["arguments"]
            log.info("strumento richiesto: %s %s", nome, argomenti)
            testo = esegui_tool(nome, argomenti, adesso_fn)
            log.info("strumento risultato: %s", testo)
            risultati.append({"role": "tool", "tool_call_id": chiamata["id"], "content": testo})
        return {"messages": stato["messages"] + risultati}

    def nodo_limite(stato):
        # Chiude ogni richiesta pendente con un errore (cronologia coerente) e avvisa l'utente.
        chiusure = [
            {"role": "tool", "tool_call_id": c["id"], "content": "Errore: limite di passaggi raggiunto."}
            for c in stato["messages"][-1]["tool_calls"]
        ]
        avviso = {
            "role": "assistant",
            "content": f"Errore: raggiunto il limite di {MAX_PASSAGGI} passaggi senza una risposta finale.",
        }
        return {"messages": stato["messages"] + chiusure + [avviso]}

    def bivio(stato):
        if not stato["messages"][-1].get("tool_calls"):
            return "fine"
        if stato["passaggi"] >= MAX_PASSAGGI:
            return "limite"
        return "tools"

    grafo = StateGraph(Stato)
    grafo.add_node("llm", nodo_llm)
    grafo.add_node("tools", nodo_tools)
    grafo.add_node("limite", nodo_limite)
    grafo.add_edge(START, "llm")
    grafo.add_conditional_edges("llm", bivio, {"tools": "tools", "limite": "limite", "fine": END})
    grafo.add_edge("tools", "llm")
    grafo.add_edge("limite", END)
    return grafo.compile()
