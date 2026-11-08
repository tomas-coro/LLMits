"""Client minimo per il server locale di LM Studio.

Scheletro da completare con Claude Code (slide 19-22):
configurazione, messaggi, payload e chiamata HTTP.
Import e gestione degli errori sono gia' presenti: conservarli.
"""

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
# "system" = regole generali per il modello, "user" = la domanda.
messages = [
    {"role": "system", "content": "Sei un assistente utile. Rispondi sempre in italiano, in modo breve e chiaro."},
    {"role": "user", "content": "Spiega in due frasi cos'e' un LLM."},
]

# --- Payload --------------------------------------------------------------
payload = {
    "model": model,
    "messages": messages,
    "temperature": 0.3,
    "max_tokens": 300,
    "reasoning_effort": "none",  # senza, il modello puo' consumare i token ragionando e rispondere vuoto
    "stream": False,  # risposta unica; lo streaming arriva piu' avanti
}

# --- Chiamata -------------------------------------------------------------
try:
    response = requests.post(f"{base_url}/chat/completions", json=payload, timeout=120)
    response.raise_for_status()  # status 4xx/5xx -> HTTPError, gestito sotto
    data = response.json()
    print(data["choices"][0]["message"]["content"])
except requests.exceptions.Timeout:
    print("Attesa scaduta: controllare server, carico e tempi.")
except requests.exceptions.ConnectionError:
    print("Connessione fallita: controllare server, URL e porta.")
except requests.exceptions.HTTPError:
    print("Errore HTTP:", response.status_code, response.text)
