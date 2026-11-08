"""Il grafo LangGraph: stato, nodi e instradamento.

    START -> llm -> END
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class Stato(TypedDict):
    messages: list  # cronologia: system, user, assistant, tool (formato OpenAI)
    passaggi: int  # chiamate al modello fatte nella domanda corrente


def costruisci_grafo(modello_fn):
    """Costruisce il grafo. `modello_fn(messages)` restituisce il messaggio 'assistant'.

    Riceverla come parametro permette ai test di usare un modello finto.
    """

    def nodo_llm(stato):
        risposta = modello_fn(stato["messages"])
        return {"messages": stato["messages"] + [risposta], "passaggi": stato["passaggi"] + 1}

    grafo = StateGraph(Stato)
    grafo.add_node("llm", nodo_llm)
    grafo.add_edge(START, "llm")
    grafo.add_edge("llm", END)
    return grafo.compile()
