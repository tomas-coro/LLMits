# Assistente di laboratorio

Applicazione da terminale che conversa con un modello locale servito da LM Studio. Il flusso è un grafo LangGraph esplicito, la cronologia vive in memoria per la durata della sessione e il modello può chiedere uno strumento orologio (con fuso orario esplicito) che il programma esegue davvero.

## Struttura

```
app/
  cli.py        terminale, cronologia, messaggio di sistema
  grafo.py      grafo LangGraph: stato, nodi, bivio, limite di 5 passaggi
  modello.py    chiamata a LM Studio (API compatibile OpenAI)
  strumenti.py  strumento get_current_time e sua esecuzione
tests/          test automatici (senza modello) e prova reale (PROVA_REALE=1)
docs/           specifica e piano
Dockerfile, compose.yaml, .dockerignore   avvio con Docker Compose
SPIEGAZIONE.md  guida per spiegare il progetto e fare la demo
```

## Prerequisiti

- LM Studio con il server acceso (porta 1234) e un modello caricato.
- Python 3.13.
- Docker Desktop, solo per l'avvio con Docker.

## Preparazione

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
curl -s http://127.0.0.1:1234/v1/models
```

PowerShell (Windows):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
Invoke-RestMethod http://127.0.0.1:1234/v1/models
```

Il comando `/v1/models` elenca i modelli: copia l'`id` del modello di chat in `LM_MODEL` dentro `.env` (mai inventarlo). `LM_BASE_URL` resta `http://127.0.0.1:1234/v1`. Il file `.env` non va in Git.

## Avvio

```bash
.venv/bin/python -m app.cli
```

PowerShell: `.\.venv\Scripts\python.exe -m app.cli`

Con Docker (LM Studio resta sul computer host):

```bash
docker compose build
docker compose run --rm assistente
```

Per seguire i log da un secondo terminale, avvia il container con un nome e leggilo mentre è attivo:

```bash
docker compose run --rm --name assistente-demo assistente
docker ps
docker logs assistente-demo
```

Con `--rm` il container sparisce all'uscita: per analizzare un arresto dopo la chiusura, ripeti la prova senza `--rm`.

Per uscire scrivi `esci`.

Durante ogni domanda il programma scrive su stderr una traccia con prefisso `[log]`: inizio e fine di ogni chiamata al modello, strumento richiesto (nome e argomenti) e risultato. Esempio reale per "Che ore sono a Tokyo?":

```
[log] nodo llm: inizio chiamata 1
[log] nodo llm: fine chiamata 1
[log] strumento richiesto: get_current_time {"timezone":"Asia/Tokyo"}
[log] strumento risultato: 2026-11-09T01:45:41+09:00
[log] nodo llm: inizio chiamata 2
[log] nodo llm: fine chiamata 2
```

## Test

```bash
.venv/bin/python -m pytest -q
```

16 test senza modello acceso: grafo, instradamento, cronologia, strumento con istante controllato, log delle chiamate, errori del modello, terminale. Esito reale: `16 passed, 1 skipped`.

```bash
PROVA_REALE=1 .venv/bin/python -m pytest tests/test_reale.py -v
```

Prova reale con LM Studio acceso: chiede l'ora a Tokyo e verifica che il modello chiami davvero lo strumento. Esito reale: `1 passed` (11 s).

PowerShell: `$env:PROVA_REALE="1"; .\.venv\Scripts\python.exe -m pytest tests/test_reale.py -v` (non provato su Windows).

## Diagnosi rapida

| Messaggio o sintomo | Primo controllo |
|---|---|
| `Errore: variabile LM_MODEL mancante...` (o `LM_BASE_URL`) | Esiste `.env`? Copiato da `.env.example` e compilato? |
| `Connessione fallita: controllare server, URL e porta.` | LM Studio ha il server acceso? `LM_BASE_URL` è giusto? |
| `Attesa scaduta: controllare server, carico e tempi.` | Il modello è caricato? Il primo avvio è lento: riprova |
| `Errore HTTP: ...` | Leggi il testo dopo il codice; spesso `LM_MODEL` non coincide con l'id di `/v1/models` |
| `raggiunto il limite di 5 passaggi senza una risposta finale` | Il modello ha richiamato lo strumento troppe volte: riformula la domanda |
| Il container non raggiunge LM Studio | Nel container `localhost` è il container: serve `host.docker.internal` (già in `compose.yaml`). Se rifiuta, in LM Studio attiva "Serve on Local Network" (sul Mac provato: non è servito) |
| Risposte lente o in coda | LM Studio elabora una richiesta alla volta: fai una domanda per volta |
