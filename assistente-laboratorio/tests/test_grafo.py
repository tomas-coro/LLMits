from app.grafo import costruisci_grafo


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
