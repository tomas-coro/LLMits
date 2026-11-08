"""Client minimo per il server locale di LM Studio.

Scheletro da completare con Claude Code (slide 19-22):
configurazione, messaggi, payload e chiamata HTTP.
Import e gestione degli errori sono gia' presenti: conservarli.
"""

import json
import os

import requests
from dotenv import load_dotenv

# --- Configurazione -------------------------------------------------------
# URL e modello stanno in .env (escluso da Git): niente valori nel codice.
# os.environ[...] dà KeyError se la variabile manca: errore visibile, non un default silenzioso.
load_dotenv()
base_url = os.environ["LM_BASE_URL"]
model = os.environ["LM_MODEL"]

# --- Messaggi -------------------------------------------------------------
# "system" = regole generali per il modello, "user" = la domanda (letta da terminale).
SYSTEM_PROMPT = "Sei un assistente utile. Rispondi sempre in italiano, in modo breve e chiaro."

# --- Chiamata -------------------------------------------------------------
def ask(question):
    """Invia una domanda al modello e stampa la risposta man mano che arriva (streaming)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "temperature": 0.3,
        "max_tokens": 300,
        "reasoning_effort": "none",  # senza, il modello puo' consumare i token ragionando e rispondere vuoto
        "stream": True,  # il server manda tanti piccoli eventi invece di un JSON finale
    }
    try:
        response = requests.post(f"{base_url}/chat/completions", json=payload, timeout=120, stream=True)
        response.raise_for_status()  # status 4xx/5xx -> HTTPError, gestito sotto
        # Senza charset nell'header requests assume Latin-1 e "è" diventa "Ã¨": forzo UTF-8.
        response.encoding = "utf-8"
        # Ogni evento e' una riga "data: {json}"; l'ultima e' "data: [DONE]".
        # Il testo nuovo sta in choices[0].delta.content (assente nel primo e nell'ultimo evento).
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            chunk = line[len("data: "):]
            if chunk == "[DONE]":
                break
            delta = json.loads(chunk)["choices"][0]["delta"]
            print(delta.get("content") or "", end="", flush=True)
        print()  # a capo finale
    except requests.exceptions.Timeout:
        print()
        print("Attesa scaduta: controllare server, carico e tempi.")
    except requests.exceptions.ConnectionError:
        print()
        print("Connessione fallita: controllare server, URL e porta.")
    except requests.exceptions.HTTPError:
        print("Errore HTTP:", response.status_code, response.text)


# --- Ciclo da terminale ---------------------------------------------------
# Un errore stampa il messaggio e si puo' riprovare con un'altra domanda.
while True:
    try:
        question = input("\nDomanda (scrivi 'esci' per uscire): ").strip()
    except EOFError:  # input terminato (es. pipe): si esce invece di andare in errore
        break
    if question.lower() == "esci":
        break
    if not question:  # invio a vuoto: non spreco una chiamata al modello
        continue
    ask(question)
