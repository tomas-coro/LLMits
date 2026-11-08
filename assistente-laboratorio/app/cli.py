"""Interfaccia da terminale: chiede una domanda, la passa al grafo, stampa la risposta."""

import logging
import os
import sys

from dotenv import load_dotenv

from app.grafo import costruisci_grafo
from app.modello import ErroreModello, chiama_modello

SYSTEM_PROMPT = (
    "Sei un assistente utile. Rispondi sempre in italiano, in modo breve e chiaro. "
    "Per sapere data e ora usa sempre lo strumento get_current_time con un fuso orario esplicito: "
    "non indovinare l'ora."
)


def main():
    load_dotenv()
    # I log vanno su stderr (non si mescolano alle risposte) e mostrano il giro del grafo.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="[log] %(message)s")
    for variabile in ("LM_BASE_URL", "LM_MODEL"):
        if variabile not in os.environ:
            print(f"Errore: variabile {variabile} mancante. Copiare .env.example in .env e compilarlo.")
            return 1

    grafo = costruisci_grafo(chiama_modello)
    # La cronologia vive solo qui, in memoria: si perde quando il programma si chiude.
    cronologia = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            domanda = input("\nDomanda (scrivi 'esci' per uscire): ").strip()
        except EOFError:  # input terminato (es. pipe): si esce invece di andare in errore
            break
        if domanda.lower() == "esci":
            break
        if not domanda:
            continue
        print("sto pensando...")
        try:
            risultato = grafo.invoke(
                {"messages": cronologia + [{"role": "user", "content": domanda}], "passaggi": 0}
            )
        except ErroreModello as errore:
            # Il turno fallito non entra in cronologia: si puo' riprovare con un'altra domanda.
            print(errore)
            continue
        cronologia = risultato["messages"]
        print(cronologia[-1]["content"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
