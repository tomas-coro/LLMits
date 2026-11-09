# Assistente di laboratorio

Applicazione da terminale che conversa con un modello locale servito da LM Studio. Il flusso è un grafo LangGraph esplicito, la cronologia vive in memoria per la durata della sessione e il modello può chiedere tre strumenti che il programma esegue davvero: l'orologio locale (con fuso orario esplicito), il convertitore di unità `convert_units` e il meteo attuale `get_weather` (Open-Meteo), gli ultimi due pubblicati da un server MCP locale (stdio).

## Struttura

```
app/
  cli.py        terminale, cronologia, messaggio di sistema
  grafo.py      grafo LangGraph: stato, nodi, bivio, limite di 5 passaggi
  modello.py    chiamata a LM Studio (API compatibile OpenAI)
  strumenti.py  strumento get_current_time e sua esecuzione
  convertitore.py  logica pura del convertitore (m, km, C, F)
  meteo.py         meteo da Open-Meteo (geocoding + previsione attuale), con errori distinti
  mcp_server.py    server MCP (FastMCP, stdio): pubblica convert_units e get_weather
  client_mcp.py    client MCP sincrono: avvia il server, discovery, inoltro delle chiamate
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

Il server MCP non si avvia a mano: all'avvio la CLI lo lancia come processo separato (`python -m app.mcp_server`, trasporto stdio), acquisisce gli strumenti con la discovery e lo chiude all'uscita. Nel container Compose i due processi vivono insieme. Se il server non parte, la CLI stampa `Server MCP non avviato: ...` ed esce. Unità del convertitore: `m`, `km` (lunghezza), `C`, `F` (temperatura); solo conversioni nella stessa grandezza. Esempio: "Quanti gradi Fahrenheit sono 100 gradi Celsius?".

`get_weather(city)` geocodifica la città con Open-Meteo (senza chiave API) e legge il meteo attuale: restituisce località scelta, temperatura in °C, condizioni e istante con fuso. Se più località hanno lo stesso nome sceglie la prima e lo dichiara nel campo `note`. Distingue città non trovata, timeout (5 s connessione, 10 s lettura), servizio irraggiungibile, risposta HTTP o JSON non valida. È l'unico strumento che usa la rete. Esempio: "Che tempo fa adesso a Roma?".

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

Test senza modello acceso e senza rete: grafo, instradamento, cronologia, strumento con istante controllato, log delle chiamate, errori del modello, terminale, convertitore (calcolo e rifiuti), meteo con risposte HTTP simulate (città unica, ambigua, assente, timeout, status HTTP, JSON o campi non validi), server MCP vero via stdio (discovery dei due tool, chiamate dirette, errori) e grafo con modello simulato. Esito reale: `81 passed, 3 skipped` (le 3 prove reali sono saltate senza `PROVA_REALE=1`).

```bash
PROVA_REALE=1 .venv/bin/python -m pytest tests/test_reale.py -v
```

Prove reali con LM Studio acceso (separate dai test automatici):

- `test_il_modello_chiama_davvero_l_orologio`: chiede l'ora a Tokyo. Esito reale: `1 passed` (11 s, prima dell'integrazione MCP).
- `test_il_modello_sceglie_davvero_convert_units`: con server MCP vero, verifica che il modello scelga `convert_units` con argomenti 100, `C`, `F`, che il server risponda `212.0 F` con lo stesso `tool_call_id` e che `212` compaia nella risposta.
- `test_il_modello_sceglie_davvero_get_weather`: LM Studio, server MCP e **Open-Meteo reali** (serve la rete): il modello sceglie `get_weather` per Roma, il server restituisce un JSON con località e temperatura, e la risposta finale è non vuota.

Esito reale del 09/11/2026 con `google/gemma-4-e2b`: `3 passed` in 144 s (38-59 s a prova). Al primo giro 2 prove su 3 sono scadute per `Attesa scaduta` (timeout di 120 s di LM Studio lento a freddo); al secondo giro tutte e 3 sono passate. Prova **Docker** del 09/11/2026 (`docker compose run --rm -T --build assistente` con le domande da stdin, non in modalità interattiva con TTY): dal container, con LM Studio sull'host e rete verso Open-Meteo, il modello ha scelto `get_weather` (Roma, 16.9 °C, coperto) e `convert_units` (100 C = 212 F), con log completi e risposta finale corretta. Il server MCP e la CLI girano insieme nel container come processi separati.

PowerShell: `$env:PROVA_REALE="1"; .\.venv\Scripts\python.exe -m pytest tests/test_reale.py -v` (non provato su Windows).

## Diagnosi rapida

| Messaggio o sintomo | Primo controllo |
|---|---|
| `Errore: variabile LM_MODEL mancante...` (o `LM_BASE_URL`) | Esiste `.env`? Copiato da `.env.example` e compilato? |
| `Connessione fallita: controllare server, URL e porta.` | LM Studio ha il server acceso? `LM_BASE_URL` è giusto? |
| `Attesa scaduta: controllare server, carico e tempi.` | Il modello è caricato? Il primo avvio è lento: riprova |
| `Errore HTTP: ...` | Leggi il testo dopo il codice; spesso `LM_MODEL` non coincide con l'id di `/v1/models` |
| `raggiunto il limite di 5 passaggi senza una risposta finale` | Il modello ha richiamato lo strumento troppe volte: riformula la domanda |
| `Server MCP non avviato: ...` | Dipendenze installate (`fastmcp==4.1.6` in `requirements.txt`)? Prova `.venv/bin/python -m app.mcp_server`: deve restare in attesa senza errori (Ctrl+C per uscire) |
| `Errore: Localita' non trovata`, `tempo massimo superato`, `servizio irraggiungibile`, `risposta HTTP ...` | Problema del meteo, non del grafo: controlla la rete (nel container serve accesso a Internet) e il nome della città |
| Un tool risponde `Errore: ...` | Il convertitore rifiuta unità diverse da `m`, `km`, `C`, `F` e conversioni tra grandezze diverse: il testo dell'errore dice quale |
| Il container non raggiunge LM Studio | Nel container `localhost` è il container: serve `host.docker.internal` (già in `compose.yaml`). Se rifiuta, in LM Studio attiva "Serve on Local Network" (sul Mac provato: non è servito) |
| Risposte lente o in coda | LM Studio elabora una richiesta alla volta: fai una domanda per volta |
