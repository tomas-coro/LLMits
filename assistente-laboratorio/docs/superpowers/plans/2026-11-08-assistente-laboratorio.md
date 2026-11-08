# Assistente di laboratorio (Lezione 4) - Piano di implementazione

> **Per chi esegue:** usare superpowers:executing-plans (esecuzione in questa sessione, con punti di controllo). I passi usano la sintassi checkbox (`- [ ]`). Regola di Tomas: l'agente NON esegue `git commit` né `git push`: a ogni task mostra i comandi e li lancia Tomas.

**Obiettivo:** applicazione da terminale con grafo LangGraph esplicito, cronologia in memoria, strumento orologio chiamato davvero dal modello, avviabile anche con Docker Compose.

**Architettura:** 4 moduli piccoli in `app/` (grafo, modello, strumenti, cli). Il grafo riceve la funzione-modello come parametro, così i test usano un modello finto. LM Studio resta sul Mac, raggiunto via API compatibile OpenAI con `requests`.

**Stack:** Python 3.13, `langgraph`, `requests`, `python-dotenv`, `tzdata`, `pytest`, Docker Compose.

## Vincoli globali (dalla specifica, valgono per ogni task)

- Lavorare solo dentro `assistente-laboratorio/` (la repo contiene altre lezioni: non leggerle per copiarne il codice, non modificarle).
- Python sincrono, moduli piccoli, commenti dove la logica non è ovvia.
- Configurazione solo da variabili d'ambiente `LM_BASE_URL` e `LM_MODEL`; l'ID del modello è quello di `GET /v1/models`, mai inventato. `.env.example` senza segreti, `.env` fuori da Git.
- Dipendenze con versione fissata: `langgraph==1.2.20`, `requests==2.34.2`, `python-dotenv==1.2.4`, `pytest==9.2.0`, `tzdata==2026.6`.
- Fuori ambito: MCP, RAG, altri strumenti, streaming, interfacce grafiche, cloud, persistenza della cronologia.
- Nessun fallback silenzioso: ogni errore è un messaggio leggibile; mai un successo finto.
- Limite: 5 chiamate al modello per domanda; il contatore riparte da 0 a ogni nuova domanda.
- Test automatici senza modello acceso; prove reali (LM Studio, Docker) separate e attivate esplicitamente (`PROVA_REALE=1`).
- Conventional Commits in italiano; `git status` e controllo del diff prima di ogni commit; staging selettivo; push solo su richiesta; mai `.env`, `.venv`, cache.
- Nessun trattino lungo nei testi: solo `-`.

Tutti i comandi si lanciano da `~/Desktop/LLMits/assistente-laboratorio` salvo dove indicato; i `git` dalla radice `~/Desktop/LLMits`.

---

### Task 1: Struttura del progetto e grafo fisso

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `.env.example`, `.env` (locale, non versionato)
- Create: `app/__init__.py` (vuoto), `app/grafo.py`
- Test: `tests/test_grafo.py`

**Interfaces:**
- Produces: `costruisci_grafo(modello_fn) -> grafo compilato`; `grafo.invoke({"messages": [...], "passaggi": 0})` restituisce lo stesso dizionario aggiornato. `modello_fn(messages) -> dict` messaggio `{"role": "assistant", "content": str}`.

- [ ] **Step 1: Creare ambiente e file di configurazione**

```bash
cd ~/Desktop/LLMits/assistente-laboratorio
mkdir -p app tests
touch app/__init__.py
cat > requirements.txt <<'EOF'
langgraph==1.2.20
requests==2.34.2
python-dotenv==1.2.4
tzdata==2026.6
pytest==9.2.0
EOF
printf '[pytest]\npythonpath = .\ntestpaths = tests\n' > pytest.ini
printf '.pytest_cache/\n' > .gitignore
printf 'LM_BASE_URL=http://127.0.0.1:1234/v1\nLM_MODEL=ID_MODELLO_REALE\n' > .env.example
printf 'LM_BASE_URL=http://127.0.0.1:1234/v1\nLM_MODEL=google/gemma-4-e2b\n' > .env
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements.txt
```

Nota: `.env`, `.venv/` e `__pycache__/` sono già esclusi dal `.gitignore` nella radice della repo.
Verifica: `cd ~/Desktop/LLMits && git check-ignore assistente-laboratorio/.env assistente-laboratorio/.venv` deve stampare entrambi i percorsi.

- [ ] **Step 2: Scrivere il test che deve fallire** (`tests/test_grafo.py`)

```python
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
```

- [ ] **Step 3: Lanciare il test e vedere che fallisce**

Run: `.venv/bin/python -m pytest -q`
Atteso: errore `ModuleNotFoundError` o `ImportError` su `app.grafo`.

- [ ] **Step 4: Scrivere il grafo minimo** (`app/grafo.py`)

```python
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
```

- [ ] **Step 5: Lanciare il test e vedere che passa**

Run: `.venv/bin/python -m pytest -q`
Atteso: `1 passed`.

- [ ] **Step 6: Commit (lo lancia Tomas)**

```bash
cd ~/Desktop/LLMits
git status
git add assistente-laboratorio/requirements.txt assistente-laboratorio/pytest.ini assistente-laboratorio/.gitignore assistente-laboratorio/.env.example assistente-laboratorio/app assistente-laboratorio/tests
git commit -m "feat(grafo): struttura del progetto e grafo fisso con test"
```

---

### Task 2: Collegamento al modello, terminale e cronologia

**Files:**
- Create: `app/modello.py`, `app/cli.py`
- Test: `tests/test_modello.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `costruisci_grafo(modello_fn)` dal Task 1.
- Produces: `chiama_modello(messages) -> dict` (`{"role": "assistant", "content": str}` più `tool_calls` solo se presenti); `ErroreModello(Exception)` con messaggio leggibile; `main() -> int` in `app/cli.py`; `SYSTEM_PROMPT`.

- [ ] **Step 1: Scrivere i test che devono fallire**

`tests/test_modello.py`:

```python
import pytest
import requests

from app import modello
from app.modello import ErroreModello, chiama_modello


class RispostaFinta:
    def __init__(self, corpo, status=200):
        self._corpo, self.status_code, self.text = corpo, status, str(corpo)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError()

    def json(self):
        return self._corpo


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setenv("LM_BASE_URL", "http://finto/v1")
    monkeypatch.setenv("LM_MODEL", "modello-finto")


def corpo(messaggio):
    return {"choices": [{"message": messaggio}]}


def test_toglie_i_campi_vuoti_di_lm_studio(monkeypatch):
    grezzo = {"role": "assistant", "content": "Ciao", "reasoning_content": "", "tool_calls": []}
    monkeypatch.setattr(modello.requests, "post", lambda *a, **k: RispostaFinta(corpo(grezzo)))
    assert chiama_modello([]) == {"role": "assistant", "content": "Ciao"}


def test_tiene_le_richieste_di_tool(monkeypatch):
    chiamate = [{"id": "1", "type": "function", "function": {"name": "get_current_time", "arguments": "{}"}}]
    grezzo = {"role": "assistant", "content": "", "tool_calls": chiamate}
    monkeypatch.setattr(modello.requests, "post", lambda *a, **k: RispostaFinta(corpo(grezzo)))
    assert chiama_modello([])["tool_calls"] == chiamate


@pytest.mark.parametrize(
    "eccezione, atteso",
    [
        (requests.exceptions.Timeout(), "Attesa scaduta"),
        (requests.exceptions.ConnectionError(), "Connessione fallita"),
    ],
)
def test_errori_di_rete_diventano_messaggi_leggibili(monkeypatch, eccezione, atteso):
    def solleva(*a, **k):
        raise eccezione

    monkeypatch.setattr(modello.requests, "post", solleva)
    with pytest.raises(ErroreModello, match=atteso):
        chiama_modello([])


def test_errore_http_mostra_stato_e_testo(monkeypatch):
    monkeypatch.setattr(modello.requests, "post", lambda *a, **k: RispostaFinta({"error": "x"}, status=404))
    with pytest.raises(ErroreModello, match="Errore HTTP: 404"):
        chiama_modello([])
```

`tests/test_cli.py`:

```python
from app import cli


def test_cronologia_cresce_tra_i_turni_e_il_turno_fallito_non_si_salva(monkeypatch, capsys):
    ricevuti = []

    def modello_finto(messages):
        ricevuti.append([m["content"] for m in messages])
        if len(ricevuti) == 2:
            raise cli.ErroreModello("Connessione fallita: prova")
        return {"role": "assistant", "content": f"risposta{len(ricevuti)}"}

    monkeypatch.setenv("LM_BASE_URL", "x")
    monkeypatch.setenv("LM_MODEL", "y")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "chiama_modello", modello_finto)
    domande = iter(["uno", "due", "tre", "esci"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(domande))

    assert cli.main() == 0
    # turno 1 ok; turno 2 fallisce (non salvato); turno 3 vede solo il turno 1
    assert ricevuti[2][1:] == ["uno", "risposta1", "tre"]
    assert "Connessione fallita: prova" in capsys.readouterr().out


def test_variabili_mancanti_danno_errore_chiaro(monkeypatch, capsys):
    monkeypatch.delenv("LM_BASE_URL", raising=False)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    assert cli.main() == 1
    assert "LM_BASE_URL mancante" in capsys.readouterr().out
```

- [ ] **Step 2: Lanciare i test e vedere che falliscono**

Run: `.venv/bin/python -m pytest -q`
Atteso: errori di import su `app.modello` e `app.cli` (il test del Task 1 passa ancora).

- [ ] **Step 3: Scrivere `app/modello.py`**

```python
"""Collegamento a LM Studio: l'unico file che usa la rete."""

import os

import requests


class ErroreModello(Exception):
    """Problema nel parlare col modello, con un messaggio gia' leggibile per l'utente."""


def chiama_modello(messages):
    """Invia la conversazione a LM Studio e restituisce il messaggio 'assistant' (pulito)."""
    # os.environ[...] da' KeyError se manca la variabile: errore visibile, non un default silenzioso.
    base_url = os.environ["LM_BASE_URL"]
    payload = {
        "model": os.environ["LM_MODEL"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 300,
        "reasoning_effort": "none",  # senza, il modello puo' consumare i token ragionando e rispondere vuoto
        "stream": False,
    }
    try:
        risposta = requests.post(f"{base_url}/chat/completions", json=payload, timeout=120)
        risposta.raise_for_status()
        grezzo = risposta.json()["choices"][0]["message"]
    except requests.exceptions.Timeout:
        raise ErroreModello("Attesa scaduta: controllare server, carico e tempi.") from None
    except requests.exceptions.ConnectionError:
        raise ErroreModello("Connessione fallita: controllare server, URL e porta.") from None
    except requests.exceptions.HTTPError:
        raise ErroreModello(f"Errore HTTP: {risposta.status_code} {risposta.text}") from None

    # LM Studio manda anche campi vuoti (reasoning_content, tool_calls: []): teniamo solo il necessario.
    pulito = {"role": "assistant", "content": grezzo.get("content") or ""}
    if grezzo.get("tool_calls"):
        pulito["tool_calls"] = grezzo["tool_calls"]
    return pulito
```

- [ ] **Step 4: Scrivere `app/cli.py`**

```python
"""Interfaccia da terminale: chiede una domanda, la passa al grafo, stampa la risposta."""

import os
import sys

from dotenv import load_dotenv

from app.grafo import costruisci_grafo
from app.modello import ErroreModello, chiama_modello

SYSTEM_PROMPT = "Sei un assistente utile. Rispondi sempre in italiano, in modo breve e chiaro."


def main():
    load_dotenv()
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
```

- [ ] **Step 5: Lanciare i test e vedere che passano**

Run: `.venv/bin/python -m pytest -q`
Atteso: `8 passed` (1 grafo + 5 modello + 2 cli; il parametrico conta 2 casi).

- [ ] **Step 6: Prova reale rapida di cronologia (non sostituisce il Task 4)**

LM Studio acceso, modello caricato, nessuna altra richiesta in corso (il server elabora una richiesta alla volta). Lanciare in background, ~60-90 secondi:

```bash
printf 'Mi chiamo Tomas. Ricordalo.\nCome mi chiamo?\nesci\n' | .venv/bin/python -m app.cli
```

Atteso: la seconda risposta contiene "Tomas". Se il modello non risponde in tempo, controllare carico e RAM del Mac prima di riprovare.

- [ ] **Step 7: Commit (lo lancia Tomas)**

```bash
cd ~/Desktop/LLMits
git status
git add assistente-laboratorio/app assistente-laboratorio/tests
git commit -m "feat(modello): chiamata a LM Studio, terminale e cronologia con test"
```

---

### Task 3: Strumento orologio, bivio e limite di passaggi

**Files:**
- Create: `app/strumenti.py`
- Modify (sostituire per intero): `app/grafo.py`
- Modify: `app/modello.py` (aggiungere lo schema dei tool al payload)
- Modify: `app/cli.py` (riga `SYSTEM_PROMPT`)
- Test: `tests/test_grafo.py` (aggiungere), `tests/test_modello.py` (aggiungere)

**Interfaces:**
- Consumes: `costruisci_grafo(modello_fn)`, `chiama_modello`, `SYSTEM_PROMPT` dai task precedenti.
- Produces: `adesso() -> datetime` (UTC); `SCHEMI` (lista schemi per il modello); `get_current_time(fuso, adesso_fn=adesso) -> str`; `esegui_tool(nome, argomenti, adesso_fn=adesso) -> str`; `MAX_PASSAGGI = 5`; `costruisci_grafo(modello_fn, adesso_fn=adesso)`.

- [ ] **Step 1: Aggiungere i test che devono fallire**

In `tests/test_grafo.py` sostituire la riga di import iniziale e aggiungere in fondo:

```python
from datetime import datetime, timezone

from app.grafo import MAX_PASSAGGI, costruisci_grafo
```

(le classi e funzioni `ModelloFinto`, `risposta`, `avvia` restano come nel Task 1), poi in fondo al file:

```python
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
```

In `tests/test_modello.py` aggiungere in fondo:

```python
def test_il_payload_include_lo_schema_dell_orologio(monkeypatch):
    visto = {}

    def post_finto(url, json, timeout):
        visto["json"] = json
        return RispostaFinta(corpo({"role": "assistant", "content": "ok"}))

    monkeypatch.setattr(modello.requests, "post", post_finto)
    chiama_modello([])
    assert visto["json"]["tools"][0]["function"]["name"] == "get_current_time"
```

- [ ] **Step 2: Lanciare i test e vedere che falliscono**

Run: `.venv/bin/python -m pytest -q`
Atteso: `ImportError: cannot import name 'MAX_PASSAGGI'` e fallimento di `test_il_payload_include_lo_schema_dell_orologio`.

- [ ] **Step 3: Scrivere `app/strumenti.py`**

```python
"""Strumenti che il modello puo' chiedere al programma (qui: solo l'orologio).

Il modello NON conosce l'ora: chiede lo strumento, e' questo codice a leggere
davvero l'orologio e a restituire il risultato.
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def adesso():
    """Istante corrente in UTC. Nei test si passa al suo posto una funzione con ora fissa."""
    return datetime.now(timezone.utc)


# Descrizione dello strumento che mandiamo al modello: nome, a cosa serve, parametri.
SCHEMI = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Restituisce data e ora attuali in un fuso orario IANA (es. Europe/Rome).",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Nome IANA del fuso orario, es. Europe/Rome o Asia/Tokyo.",
                    }
                },
                "required": ["timezone"],
            },
        },
    }
]


def get_current_time(fuso, adesso_fn=adesso):
    """Ora attuale nel fuso richiesto, in formato ISO. Errore chiaro se il fuso manca o non esiste."""
    if not fuso or not isinstance(fuso, str):
        return "Errore: il parametro 'timezone' e' obbligatorio (es. Europe/Rome)."
    try:
        zona = ZoneInfo(fuso)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return f"Errore: fuso orario sconosciuto '{fuso}'. Usa un nome IANA, es. Europe/Rome."
    return adesso_fn().astimezone(zona).isoformat(timespec="seconds")


def esegui_tool(nome, argomenti, adesso_fn=adesso):
    """Esegue lo strumento richiesto dal modello. `argomenti` e' la stringa JSON inviata dal modello.

    Restituisce sempre un testo: in caso di problema e' un errore leggibile, mai un successo finto.
    """
    if nome != "get_current_time":
        return f"Errore: strumento sconosciuto '{nome}'."
    try:
        args = json.loads(argomenti) if argomenti else {}
    except json.JSONDecodeError:
        return "Errore: argomenti non validi (JSON non leggibile)."
    if not isinstance(args, dict):
        return "Errore: argomenti non validi (atteso un oggetto JSON)."
    return get_current_time(args.get("timezone"), adesso_fn)
```

- [ ] **Step 4: Sostituire per intero `app/grafo.py`**

```python
"""Il grafo LangGraph: stato, nodi e instradamento.

    START -> llm -> [il modello chiede un tool?]
                       si -> tools -> llm
                       no -> END
    (se i passaggi superano il limite: llm -> limite -> END)
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.strumenti import adesso, esegui_tool

MAX_PASSAGGI = 5  # chiamate al modello consentite per ogni domanda dell'utente


class Stato(TypedDict):
    messages: list  # cronologia: system, user, assistant, tool (formato OpenAI)
    passaggi: int  # chiamate al modello fatte nella domanda corrente


def costruisci_grafo(modello_fn, adesso_fn=adesso):
    """Costruisce il grafo. `modello_fn(messages)` restituisce il messaggio 'assistant'.

    Riceverla come parametro permette ai test di usare un modello finto.
    """

    def nodo_llm(stato):
        risposta = modello_fn(stato["messages"])
        return {"messages": stato["messages"] + [risposta], "passaggi": stato["passaggi"] + 1}

    def nodo_tools(stato):
        # Un risultato per ogni richiesta, legato dal tool_call_id della richiesta.
        risultati = []
        for chiamata in stato["messages"][-1]["tool_calls"]:
            testo = esegui_tool(chiamata["function"]["name"], chiamata["function"]["arguments"], adesso_fn)
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
```

- [ ] **Step 5: Collegare lo schema al modello e al prompt**

In `app/modello.py`: sotto `import requests` aggiungere `from app.strumenti import SCHEMI`, e nel `payload` aggiungere dopo `"messages": messages,` la riga `"tools": SCHEMI,`.

In `app/cli.py` sostituire la definizione di `SYSTEM_PROMPT` con:

```python
SYSTEM_PROMPT = (
    "Sei un assistente utile. Rispondi sempre in italiano, in modo breve e chiaro. "
    "Per sapere data e ora usa sempre lo strumento get_current_time con un fuso orario esplicito: "
    "non indovinare l'ora."
)
```

- [ ] **Step 6: Lanciare i test e vedere che passano**

Run: `.venv/bin/python -m pytest -q`
Atteso: `15 passed` (7 grafo + 6 modello + 2 cli). I test del Task 1 e 2 devono restare verdi.

- [ ] **Step 7: Commit (lo lancia Tomas)**

```bash
cd ~/Desktop/LLMits
git status
git add assistente-laboratorio/app assistente-laboratorio/tests
git commit -m "feat(strumenti): orologio con fuso esplicito, bivio dei tool e limite di passaggi"
```

---

### Task 4: Prova reale con LM Studio

**Files:**
- Create: `tests/test_reale.py`

**Interfaces:**
- Consumes: `costruisci_grafo`, `chiama_modello`, `SYSTEM_PROMPT`.
- Produces: la prova che il modello locale sceglie davvero lo strumento (o la registrazione del blocco).

- [ ] **Step 1: Scrivere la prova reale** (`tests/test_reale.py`)

```python
"""Prova REALE con LM Studio: si attiva solo con PROVA_REALE=1 (serve il server acceso)."""

import os
import re

import pytest
from dotenv import load_dotenv

from app.cli import SYSTEM_PROMPT
from app.grafo import costruisci_grafo
from app.modello import chiama_modello

pytestmark = pytest.mark.skipif(
    os.environ.get("PROVA_REALE") != "1",
    reason="Prova reale: attivare con PROVA_REALE=1 (serve LM Studio acceso)",
)


def test_il_modello_chiama_davvero_l_orologio():
    load_dotenv()
    grafo = costruisci_grafo(chiama_modello)
    messaggi = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Che ore sono a Tokyo? Usa lo strumento."},
    ]
    out = grafo.invoke({"messages": messaggi, "passaggi": 0})
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    assert tool, "Il modello non ha chiamato nessuno strumento: registrare il blocco, non dichiarare completato."
    assert re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+09:00$", tool[0]["content"])
    assert out["messages"][-1]["role"] == "assistant" and out["messages"][-1]["content"]
```

- [ ] **Step 2: Verificare che senza attivazione venga saltata**

Run: `.venv/bin/python -m pytest -q`
Atteso: `15 passed, 1 skipped`.

- [ ] **Step 3: Lanciare la prova reale** (in background, ~30-120 secondi; server libero)

Run: `PROVA_REALE=1 .venv/bin/python -m pytest tests/test_reale.py -v`
Atteso: `1 passed`. Se fallisce con "non ha chiamato nessuno strumento" o va in timeout: NON si dichiara completato; si annota l'esito nel resoconto e in `SPIEGAZIONE.md`.

- [ ] **Step 4: Prova a mano da terminale (quella che mostrerai al docente)**

```bash
printf 'Mi chiamo Tomas.\nChe ore sono a Roma?\nCome mi chiamo?\nesci\n' | .venv/bin/python -m app.cli
```

Atteso: la seconda risposta contiene un'ora; la terza contiene "Tomas". Annotare le risposte vere (servono per la demo).

- [ ] **Step 5: Commit (lo lancia Tomas)**

```bash
cd ~/Desktop/LLMits
git status
git add assistente-laboratorio/tests/test_reale.py
git commit -m "test(strumenti): prova reale con LM Studio, attivabile con PROVA_REALE=1"
```

---

### Task 5: Docker Compose

**Files:**
- Create: `Dockerfile`, `compose.yaml`, `.dockerignore`

**Interfaces:**
- Consumes: `app.cli` come punto di avvio (`python -m app.cli`), `requirements.txt`, `.env` (per `LM_MODEL`).
- Produces: avvio con `docker compose run --rm app`.

- [ ] **Step 1: Installare Docker Desktop (lo fa Tomas, ~15 minuti)**

Scaricare Docker Desktop per Mac da docker.com, avviarlo e attendere che sia "running". Verifica: `docker --version` e `docker compose version` devono stampare una versione. Se il Mac è lento, chiudere altre app: il modello occupa già 4,4 GB su 8 GB.

- [ ] **Step 2: Scrivere i file**

`Dockerfile`:

```dockerfile
FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
CMD ["python", "-m", "app.cli"]
```

`compose.yaml`:

```yaml
# LM Studio resta sul Mac: dentro il container "localhost" sarebbe il container stesso,
# quindi si usa host.docker.internal per raggiungere il Mac.
services:
  app:
    build: .
    environment:
      LM_BASE_URL: http://host.docker.internal:1234/v1
      LM_MODEL: ${LM_MODEL}  # letto da .env (stesso ID di GET /v1/models)
    stdin_open: true
    tty: true
```

`.dockerignore`:

```
.env
.venv
__pycache__
.pytest_cache
tests
docs
```

- [ ] **Step 3: Costruire l'immagine**

Run: `docker compose build`
Atteso: build completata senza errori.

- [ ] **Step 4: Verificare che il container raggiunga LM Studio**

Run: `docker compose run --rm -T app python -c "import requests; print(requests.get('http://host.docker.internal:1234/v1/models', timeout=10).status_code)"`
Atteso: `200`. Se `Connessione rifiutata`: in LM Studio, sezione Developer, Server Settings, attivare "Serve on Local Network" (ascolto su tutte le interfacce), poi riprovare. Annotare cosa è servito.

- [ ] **Step 5: Prova reale nel container** (in background; server libero)

Run: `printf 'Che ore sono a Tokyo?\nesci\n' | docker compose run --rm -T app`
Atteso: risposta con un'ora. `-T` serve perché l'input arriva da una pipe e non da un terminale. Per l'uso interattivo (demo): `docker compose run --rm app`.

- [ ] **Step 6: Commit (lo lancia Tomas)**

```bash
cd ~/Desktop/LLMits
git status
git add assistente-laboratorio/Dockerfile assistente-laboratorio/compose.yaml assistente-laboratorio/.dockerignore
git commit -m "feat(docker): avvio con Docker Compose, LM Studio sull'host"
```

---

### Task 6: README e SPIEGAZIONE

**Files:**
- Create: `README.md`, `SPIEGAZIONE.md`

**Interfaces:**
- Consumes: tutti i comandi e i risultati reali dei task precedenti.
- Produces: documentazione con soli comandi verificati.

- [ ] **Step 1: Scrivere `README.md`**

Sezioni obbligatorie, ognuna con i comandi realmente eseguiti nei task precedenti (se un comando non è stato eseguito, non va nel README):

1. Cos'è e struttura delle cartelle.
2. Prerequisiti (LM Studio con server acceso e modello caricato, Python 3.13, Docker Desktop per il passo Docker).
3. Preparazione: creare `.venv`, installare `requirements.txt` (versione macOS/Linux e versione PowerShell con `py -m venv .venv` e `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`), copiare `.env.example` in `.env`, leggere l'ID del modello con `GET /v1/models`.
4. Avvio: `.venv/bin/python -m app.cli` e `docker compose run --rm app`.
5. Test: `pytest` (senza modello) e `PROVA_REALE=1 pytest tests/test_reale.py` (con modello); cosa copre ciascuno.
6. Diagnosi rapida: tabella messaggio -> primo controllo (`Connessione fallita`, `Errore HTTP`, `Attesa scaduta`, variabile mancante, limite di passaggi, container che non raggiunge LM Studio, richieste in coda perché il server elabora una alla volta).

- [ ] **Step 2: Scrivere `SPIEGAZIONE.md`**

Sezioni obbligatorie, in italiano semplice per chi è principiante:

1. **In una frase:** cosa fa il programma.
2. **Schema del grafo** (disegno ASCII del grafo `START -> llm -> bivio -> tools -> llm / END`, più il ramo `limite`), con una riga per nodo.
3. **Il giro dell'orologio passo per passo,** con le risposte vere annotate al Task 4: domanda -> il modello chiede lo strumento -> il programma legge l'orologio -> il risultato torna al modello (legato dal `tool_call_id`) -> risposta finale.
4. **Perché la cronologia funziona:** il modello non ricorda; si rimanda ogni volta la lista dei messaggi.
5. **Perché i test non usano il modello** e cosa dimostra e non dimostra una risposta simulata.
6. **Copione di demo di circa 5 minuti:** 3 domande brevi già provate (nome, ora in un fuso, ora in un fuso sconosciuto per mostrare l'errore chiaro), cosa dire per ognuna, e la regola "scaldare il modello prima" (fare una domanda di prova prima di iniziare, una richiesta alla volta).
7. **Domande probabili del docente con risposta** (max 5): differenza tra chatbot e agente; cosa decide il modello e cosa decide il programma; perché il limite di 5 passaggi; perché `host.docker.internal`; cosa non è provato.
8. **Cosa è stato provato davvero e cosa no,** con esiti reali del Task 4 e 5.

- [ ] **Step 3: Verificare i comandi del README**

Eseguire (o rileggere gli esiti già ottenuti per) ogni comando elencato; correggere il README dove un comando non coincide con l'esito reale. Controllare che non compaiano trattini lunghi: `grep -n "-\|-" README.md SPIEGAZIONE.md` non deve stampare nulla.

- [ ] **Step 4: Commit (lo lancia Tomas)**

```bash
cd ~/Desktop/LLMits
git status
git add assistente-laboratorio/README.md assistente-laboratorio/SPIEGAZIONE.md
git commit -m "docs: README e guida alla spiegazione per la demo"
```

Il push finale lo decide Tomas: `git push` dalla radice.

---

## Autoverifica rispetto alla specifica

| Requisito della specifica | Task |
|---|---|
| Grafo esplicito con stato, nodi, bivio | 1, 3 |
| Cronologia in memoria, turno fallito non salvato | 2 |
| Orologio con fuso obbligatorio, errori chiari, istante controllabile | 3 |
| Limite di 5 passaggi, cronologia valida dopo il limite | 3 |
| 6 test senza modello (più test su modello e terminale) | 1, 2, 3 |
| Prova reale con LM Studio, separata (`PROVA_REALE=1`) | 4 |
| Docker Compose e prova reale nel container | 5 |
| README con comandi verificati, anche PowerShell | 6 |
| SPIEGAZIONE con schema, demo, domande del docente | 6 |
| Criteri di completamento | 3 (pytest), 4 (orologio reale), 2 e 4 (cronologia), 5 (Docker), 6 (documenti) |
