# Calcolatrice MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** aggiungere il tool `calculate(expression)` al server MCP esistente, con parser aritmetico sicuro.

**Architecture:** logica pura in `app/calcolatrice.py` (modulo `ast`, nessun `eval`), esposta da `app/mcp_server.py` come i tool esistenti; l'host la scopre con la discovery, senza schemi duplicati. Il grafo non cambia.

**Tech Stack:** Python 3.13, FastMCP (gia' presente, `fastmcp==4.1.6`), pytest. Nessuna nuova dipendenza.

## Global Constraints

- Specifica: `docs/superpowers/specs/2026-11-09-tool-calcolatrice.md` (approvata il 09/11/2026).
- Lavorare solo in `assistente-laboratorio/`, branch `feat/calcolatrice` (da `dev`).
- Test con `.venv/bin/python -m pytest -q` (il Python di sistema non ha le dipendenze).
- Niente `print()` nel server MCP (su stdout passa il protocollo).
- Errori come `ToolError`, mai un numero inventato.
- **Nessun commit e nessun merge senza via libera esplicito di Tomas** (fermarsi e dire cosa verrebbe committato e con quale messaggio).

Nota di coerenza con la specifica: la discovery del server MCP pubblica **tre** tool (`convert_units`, `get_weather`, `calculate`); l'orologio e' locale, quindi i tool totali dell'agente sono quattro.

## File

- Create: `app/calcolatrice.py` (logica pura), `tests/test_calcolatrice.py`
- Modify: `app/mcp_server.py` (nuovo tool), `app/cli.py` (system prompt), `tests/test_mcp.py`, `tests/test_grafo.py`, `tests/test_reale.py`, `README.md`, `CLAUDE.md`

---

### Task 1: Logica della calcolatrice

**Files:**
- Create: `app/calcolatrice.py`
- Test: `tests/test_calcolatrice.py`

**Interfaces:**
- Produces: `calcola(expression) -> {"value": float, "expression": str}`; solleva `ValueError` con messaggio italiano. Costanti `MAX_LUNGHEZZA = 200`, `MAX_ESPONENTE = 1000`.

- [ ] **Step 1: Scrivere i test (falliscono)**

```python
import pytest

from app.calcolatrice import MAX_ESPONENTE, MAX_LUNGHEZZA, calcola


@pytest.mark.parametrize(
    "espressione, atteso",
    [
        ("2 + 3", 5.0),
        ("2 + 3 * 4", 14.0),  # precedenza
        ("(2 + 3) * 4", 20.0),  # parentesi
        ("-5 + 2", -3.0),  # meno unario
        ("--3", 3.0),
        ("2 ** 10", 1024.0),
        ("-2 ** 2", -4.0),  # come in Python: -(2 ** 2)
        ("2 ** -1", 0.5),
        ("10 % 3", 1.0),
        ("7 / 2", 3.5),
        ("0.1 + 0.2", 0.3),  # senza arrotondamento verrebbe 0.30000000000000004
    ],
)
def test_espressioni_valide(espressione, atteso):
    assert calcola(espressione) == {"value": atteso, "expression": espressione}


@pytest.mark.parametrize(
    "espressione, messaggio",
    [
        ("", "vuota"),
        ("   ", "vuota"),
        ("2 +", "non valida"),
        ("abc", "non ammesso"),  # nomi
        ("__import__('os')", "non ammesso"),  # chiamate
        ("'a' * 3", "non ammesso"),  # stringhe
        ("1 < 2", "non ammesso"),  # confronti
        ("True + 1", "non ammesso"),  # bool non e' un numero
        ("1j", "non ammesso"),  # numeri complessi
        ("1 / 0", "divisione per zero"),
        ("5 % 0", "divisione per zero"),
        ("9 ** 9 ** 9", "esponente"),
        (f"2 ** {MAX_ESPONENTE + 1}", "esponente"),
        ("10 ** 308 * 10", "non finito"),
        ("(-8) ** 0.5", "non reale"),
        ("9" * (MAX_LUNGHEZZA + 1), "troppo lunga"),
    ],
)
def test_errori_chiari(espressione, messaggio):
    with pytest.raises(ValueError, match=messaggio):
        calcola(espressione)


def test_argomento_non_testo():
    with pytest.raises(ValueError, match="testo"):
        calcola(5)


def test_limite_esponente_e_incluso():
    assert calcola(f"1 ** {MAX_ESPONENTE}")["value"] == 1.0
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/bin/python -m pytest tests/test_calcolatrice.py -q`
Expected: errore di import (`app.calcolatrice` non esiste).

- [ ] **Step 3: Implementare**

```python
"""Calcolatrice: logica pura, senza rete e senza MCP (il server MCP la espone come tool).

Usa il modulo `ast` e ammette solo numeri e operatori elencati: niente eval/exec, quindi
un'espressione come "__import__('os')" viene rifiutata invece di essere eseguita.
"""

import ast
import math
import operator

MAX_LUNGHEZZA = 200  # caratteri: evita espressioni enormi
MAX_ESPONENTE = 1000  # |esponente| massimo: evita 9 ** 9 ** 9, che bloccherebbe il programma

_BINARI = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARI = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _valuta(nodo):
    """Valuta un nodo dell'albero; solleva ValueError per tutto cio' che non e' ammesso."""
    # type(...) in (int, float) esclude bool (True e' un int in Python) e i complessi.
    if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
        return float(nodo.value)  # tutto in float: niente interi giganti che non entrano in isfinite
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _UNARI:
        return _UNARI[type(nodo.op)](_valuta(nodo.operand))
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _BINARI:
        sinistra = _valuta(nodo.left)
        destra = _valuta(nodo.right)
        if isinstance(nodo.op, ast.Pow) and abs(destra) > MAX_ESPONENTE:
            raise ValueError(f"esponente troppo grande (massimo {MAX_ESPONENTE} in valore assoluto).")
        return _BINARI[type(nodo.op)](sinistra, destra)
    raise ValueError("elemento non ammesso: sono ammessi solo numeri, + - * / ** %, parentesi e meno unario.")


def calcola(expression):
    """Valuta un'espressione aritmetica. Solleva ValueError se non e' possibile.

    Restituisce {"value": numero arrotondato a 6 decimali, "expression": espressione ricevuta}.
    """
    if not isinstance(expression, str):
        raise ValueError("l'espressione deve essere un testo.")
    if not expression.strip():
        raise ValueError("l'espressione e' vuota.")
    if len(expression) > MAX_LUNGHEZZA:
        raise ValueError(f"espressione troppo lunga (massimo {MAX_LUNGHEZZA} caratteri).")
    try:
        albero = ast.parse(expression.strip(), mode="eval")
        valore = _valuta(albero.body)
    except SyntaxError:
        raise ValueError("espressione non valida.") from None
    except ZeroDivisionError:
        raise ValueError("divisione per zero.") from None
    except OverflowError:
        raise ValueError("risultato troppo grande (non finito).") from None
    if isinstance(valore, complex):  # (-8) ** 0.5 in Python da' un numero complesso
        raise ValueError("il risultato non e' un numero reale.")
    if not math.isfinite(valore):
        raise ValueError("risultato non finito (infinito o NaN).")
    # Arrotondare toglie il rumore dei float (0.1 + 0.2 -> 0.30000000000000004).
    return {"value": round(valore, 6), "expression": expression}
```

- [ ] **Step 4: Verificare che passino**

Run: `.venv/bin/python -m pytest tests/test_calcolatrice.py -q`
Expected: tutti passati. Se un messaggio non combacia con `match=`, correggere il messaggio nel codice (non indebolire il test).

---

### Task 2: Tool MCP, discovery, grafo e prompt

**Files:**
- Modify: `app/mcp_server.py`, `app/cli.py`, `tests/test_mcp.py`, `tests/test_grafo.py`

**Interfaces:**
- Consumes: `calcola(expression)` del Task 1.
- Produces: tool MCP `calculate` con parametro `expression: str`.

- [ ] **Step 1: Scrivere i test (falliscono)**

In `tests/test_mcp.py`: cambiare l'asserzione della discovery

```python
assert sorted(s["function"]["name"] for s in schemi) == ["calculate", "convert_units", "get_weather"]
```

e aggiungere, dopo `test_discovery_meteo`:

```python
def test_discovery_calcolatrice(client):
    funzione = next(s["function"] for s in client.schemi if s["function"]["name"] == "calculate")
    for operatore in ("+", "-", "*", "/", "**", "%"):  # gli operatori ammessi vanno documentati
        assert operatore in funzione["description"]
    parametri = funzione["parameters"]
    assert set(parametri["properties"]) == {"expression"}
    assert parametri["properties"]["expression"]["type"] == "string"
    assert parametri["required"] == ["expression"]
    assert client.ha_tool("calculate")


def test_calcolatrice_chiamata_diretta_valida(client):
    testo = client.chiama("calculate", {"expression": "(12 + 8) * 7 - 5"})
    assert json.loads(testo) == {"value": 135.0, "expression": "(12 + 8) * 7 - 5"}


@pytest.mark.parametrize(
    "espressione, atteso",
    [("1 / 0", "divisione per zero"), ("9 ** 9 ** 9", "esponente"), ("__import__('os')", "non ammesso")],
)
def test_calcolatrice_errore_non_e_un_successo(client, espressione, atteso):
    testo = client.chiama("calculate", {"expression": espressione})
    assert testo.startswith("Errore") and atteso in testo
```

In `tests/test_grafo.py`: in `ClientFinto.ha_tool` aggiungere `"calculate"` alla tupla, e in fondo alla sezione MCP:

```python
def test_calcolatrice_inoltrata_con_risultato_correlato_e_orologio_invariato():
    client = ClientFinto({"calculate": '{"value": 135.0, "expression": "(12 + 8) * 7 - 5"}'})
    modello = ModelloFinto(
        [
            richieste_multiple(
                ("a", "get_current_time", '{"timezone": "Asia/Tokyo"}'),
                ("b", "calculate", '{"expression": "(12 + 8) * 7 - 5"}'),
            ),
            risposta("21:00 e 135"),
        ]
    )
    out = avvia(
        costruisci_grafo(modello, client_mcp=client, adesso_fn=ora_fissa), [{"role": "user", "content": "ora e calcolo"}]
    )
    assert client.chiamate == [("calculate", {"expression": "(12 + 8) * 7 - 5"})]  # l'orologio non passa dal client
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool] == ["a", "b"]
    assert "135.0" in tool[1]["content"]
```

(Prima di scrivere: controllare in `tests/test_grafo.py` come il test vicino con orologio + convertitore, riga ~158, costruisce il grafo e `ora_fissa`, e copiarne la forma esatta.)

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/bin/python -m pytest tests/test_mcp.py tests/test_grafo.py -q`
Expected: falliscono la discovery (2 tool invece di 3) e le chiamate a `calculate`.

- [ ] **Step 3: Implementare**

In `app/mcp_server.py`: aggiungere `from app.calcolatrice import calcola` agli import (ordine alfabetico, prima di `app.convertitore`) e, prima del blocco `if __name__`:

```python
@mcp.tool(name="calculate")
def calculate(expression: str) -> dict:
    """Calcola un'espressione aritmetica.

    Operatori ammessi: + - * / ** % (somma, sottrazione, moltiplicazione, divisione, potenza, resto),
    parentesi e meno unario. Solo numeri: niente funzioni (sqrt, sin) ne' variabili. Esempio: "(12 + 8) * 7 - 5".
    Restituisce il risultato (campo value) e l'espressione ricevuta (campo expression).
    """
    try:
        return calcola(expression)
    except ValueError as errore:
        raise ToolError(f"Errore: {errore}") from None
```

In `app/cli.py`, estendere `SYSTEM_PROMPT` con una riga prima di quella sul meteo:

```python
    "Per calcoli aritmetici usa sempre lo strumento calculate: non calcolare a mente. "
```

- [ ] **Step 4: Verificare**

Run: `.venv/bin/python -m pytest -q`
Expected: tutto passato (81 + nuovi test), 3 skipped.

---

### Task 3: Prova reale, documentazione, verifica finale

**Files:**
- Modify: `tests/test_reale.py`, `README.md`, `CLAUDE.md`

- [ ] **Step 1: Aggiungere la prova reale** (dopo `test_il_modello_sceglie_davvero_convert_units`, stessa forma)

```python
def test_il_modello_sceglie_davvero_calculate():
    """Il server MCP e' vero (stdio) e il modello e' LM Studio: verifica la scelta della calcolatrice."""
    load_dotenv()
    messaggi = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Quanto fa (12 + 8) * 7 - 5? Usa lo strumento."},
    ]
    with ClientMcp() as client:
        grafo = costruisci_grafo(lambda m: chiama_modello(m, client.schemi), client_mcp=client)
        out = grafo.invoke({"messages": messaggi, "passaggi": 0})
    richieste = [c for m in out["messages"] if m.get("tool_calls") for c in m["tool_calls"]]
    assert [c["function"]["name"] for c in richieste][:1] == ["calculate"], (
        "Il modello non ha scelto calculate: registrare il blocco, non dichiarare completato."
    )
    tool = [m for m in out["messages"] if m["role"] == "tool"]
    assert json.loads(tool[0]["content"])["value"] == 135.0  # eseguito davvero dal server MCP
    assert tool[0]["tool_call_id"] == richieste[0]["id"]
    finale = out["messages"][-1]
    assert finale["role"] == "assistant" and "135" in finale["content"]
```

- [ ] **Step 2: Lanciare la prova reale** (LM Studio acceso con `google/gemma-4-e2b`)

Run: `PROVA_REALE=1 .venv/bin/python -m pytest tests/test_reale.py -v -k calculate`
Expected: `1 passed`. Se scade per `Attesa scaduta` (modello freddo) rilanciare una volta e riportare entrambi gli esiti. Se il modello non sceglie `calculate`, **riportare il blocco** e non dichiarare completato.

- [ ] **Step 3: Aggiornare la documentazione** (solo comandi verificati)

- `README.md`: riga 3 "tre strumenti" -> "quattro strumenti" aggiungendo la calcolatrice `calculate`; elenco struttura (riga ~15): `mcp_server.py` pubblica `convert_units`, `get_weather` e `calculate`; nuova sezione dopo quella del meteo con operatori ammessi, limiti (200 caratteri, |esponente| <= 1000), errori e l'esempio "Quanto fa (12 + 8) * 7 - 5?"; nella sezione prove reali, aggiungere `test_il_modello_sceglie_davvero_calculate` con l'esito **reale** di Step 2 (non scriverlo prima di averlo).
- `CLAUDE.md`: nella lista Obiettivo aggiungere la calcolatrice `calculate` accanto a convertitore e meteo; in Confini aggiornare il perimetro ("orologio locale, convertitore, meteo e calcolatrice MCP").

- [ ] **Step 4: Verifica finale**

Run: `.venv/bin/python -m pytest -q` e `git status` e `git diff --stat`
Expected: tutto passato, solo i file elencati modificati, nessun `.DS_Store` o segreto in staging.

- [ ] **Step 5: STOP prima del commit**

Non committare. Riferire a Tomas: file coinvolti, esiti dei test (simulati vs reali, separati), prove non eseguite, e proporre il messaggio `feat(mcp): calcolatrice con parser aritmetico sicuro`. Attendere il via libera esplicito; poi commit, e di nuovo stop prima del merge su `dev` e `main`.

## Self-review

- Copertura specifica: parser `ast` e operatori (Task 1), errori elencati (Task 1), documentazione operatori nel catalogo (Task 2), discovery e invocazione diretta (Task 2), grafo con orologio nello stesso turno (Task 2), prova reale (Task 3), README/CLAUDE.md (Task 3), nessuna dipendenza nuova.
- Tipi coerenti: `calcola(expression)` -> dict `{"value", "expression"}` usato dal server e dai test; `calculate` e `expression` ovunque.
- Rischio noto: un modello piccolo puo' non scegliere `calculate` (prova reale indispensabile).
