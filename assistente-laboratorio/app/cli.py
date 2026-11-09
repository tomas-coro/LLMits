"""Interfaccia da terminale: chiede una domanda, la passa al grafo, stampa la risposta."""

import logging
import os
import sys

from dotenv import load_dotenv

from app.client_mcp import ClientMcp, ErroreMcp
from app.grafo import costruisci_grafo
from app.modello import ErroreModello, chiama_modello

SYSTEM_PROMPT = (
    "Sei un assistente utile. Rispondi sempre in italiano, in modo breve e chiaro. "
    "Per sapere data e ora usa sempre lo strumento get_current_time con un fuso orario esplicito: "
    "non indovinare l'ora. "
    "Per convertire valori tra m, km, C e F usa sempre lo strumento convert_units: non calcolare a mente. "
    "Per il meteo attuale di una citta' usa sempre lo strumento get_weather: non inventare temperature."
)


def conversazione(grafo):
    """Il ciclo domanda/risposta, finche' l'utente scrive 'esci' o l'input finisce."""
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


def main():
    load_dotenv()
    # I log vanno su stderr (non si mescolano alle risposte) e mostrano il giro del grafo.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="[log] %(message)s")
    for variabile in ("LM_BASE_URL", "LM_MODEL"):
        if variabile not in os.environ:
            print(f"Errore: variabile {variabile} mancante. Copiare .env.example in .env e compilarlo.")
            return 1

    # Il server MCP parte una volta sola e resta aperto per tutta la sessione.
    client = ClientMcp()
    try:
        client.avvia()
    except ErroreMcp as errore:
        print(errore)
        return 1
    try:
        # Gli strumenti del server arrivano dalla discovery e si aggiungono a quello locale dell'orologio.
        grafo = costruisci_grafo(lambda messages: chiama_modello(messages, client.schemi), client_mcp=client)
        conversazione(grafo)
    finally:
        client.chiudi()  # chiude la sessione e termina il processo del server, anche dopo un errore
    return 0


if __name__ == "__main__":
    sys.exit(main())
