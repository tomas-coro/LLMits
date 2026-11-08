# Specifica: assistente-laboratorio (Lezione 4)

Data: 2026-11-08. Stato: da approvare.

## Obiettivo

Applicazione da terminale in Python che conversa con un modello servito da LM Studio (sul computer host) e:

1. organizza il flusso in un grafo LangGraph esplicito (stato, nodi, instradamento riconoscibili);
2. conserva la cronologia per la durata della sessione (nessuna persistenza su disco);
3. offre uno strumento orologio con fuso orario esplicito, richiesto dal modello tramite tool calling ed eseguito davvero dal programma;
4. si avvia anche con Docker Compose.

Consegna: lavoro funzionante, mostrabile dal vivo sul Mac dello studente, con documentazione per spiegarlo.

## Fuori ambito (non anticipare)

MCP, RAG, altri strumenti oltre l'orologio, streaming, interfacce grafiche, servizi cloud, persistenza della cronologia. Questi temi arrivano nelle lezioni successive.

## Scelte tecniche

- Python sincrono, moduli piccoli, commenti dove la logica non è ovvia.
- Chiamata al modello con `requests` verso `POST {LM_BASE_URL}/chat/completions` (API compatibile OpenAI), con `stream: false`. Il codice di rete riusa l'impostazione della Lezione 3 (errori Timeout, ConnectionError, HTTPError gestiti e mostrati, mai nascosti).
- Messaggi come dizionari nel formato OpenAI (`system`, `user`, `assistant`, `tool`).
- Configurazione solo da variabili d'ambiente: `LM_BASE_URL`, `LM_MODEL`. L'ID del modello è quello restituito da `GET /v1/models`, mai inventato. `.env.example` senza segreti, `.env` fuori da Git.
- Dipendenze con versioni fissate e motivate: `langgraph` (richiesto dal corso), `requests` e `python-dotenv` (già usati nella Lezione 3), `pytest` (test), `tzdata` (le immagini Docker leggere non hanno il database dei fusi orari; senza, l'orologio fallirebbe nel container).

## Architettura

```
assistente-laboratorio/
  app/
    grafo.py       stato, nodi, bivio, costruzione del grafo
    modello.py     chiamata a LM Studio (unico punto che usa la rete)
    strumenti.py   orologio: funzione, schema per il modello, registro
    cli.py         ciclo da terminale
  tests/
  Dockerfile
  compose.yaml
  requirements.txt
  .env.example
  README.md
  SPIEGAZIONE.md
  CLAUDE.md
```

### Grafo

```
START -> llm -> [il messaggio del modello contiene tool_calls?]
                   si -> tools -> llm
                   no -> END
```

- **Stato:** `messages` (lista di dizionari) e `passaggi` (contatore delle chiamate al modello nel turno corrente).
- **Nodo `llm`:** chiama il modello con tutti i messaggi e gli schemi dei tool; aggiunge la risposta ai messaggi; incrementa `passaggi`.
- **Nodo `tools`:** per ogni `tool_call` esegue lo strumento e aggiunge un messaggio `role: tool` con lo stesso `tool_call_id` della richiesta.
- **Bivio:** dopo ogni chiamata al modello, se il messaggio contiene `tool_calls` e `passaggi` è già 5, il grafo termina con un messaggio di errore chiaro (limite superato); se contiene `tool_calls` e `passaggi` è sotto 5 va a `tools`; se non contiene `tool_calls` va a `END`.
- `passaggi` riparte da 0 a ogni nuova domanda dell'utente (lo imposta `cli.py` quando avvia il grafo).
- Il grafo si costruisce con una funzione che riceve la funzione-modello (iniezione), così i test usano una funzione finta.

### Cronologia

La tiene `cli.py` in una lista in memoria. A ogni domanda la passa al grafo e salva la lista aggiornata restituita. Alla chiusura del programma si perde.

### Strumento orologio

- Nome: `get_current_time`. Unico parametro: `timezone` (stringa IANA, es. `Europe/Rome`), obbligatorio.
- Esegue con `zoneinfo`; restituisce data e ora ISO nel fuso richiesto.
- Fuso mancante o sconosciuto: restituisce un messaggio di errore chiaro come risultato del tool (il modello lo legge e può correggersi); non inventa mai un'ora.
- L'istante corrente arriva da una funzione sostituibile, così i test fissano l'ora.

### Interfaccia da terminale

Chiede una domanda, mostra "sto pensando..." durante la chiamata, stampa la risposta finale. Esce con `esci`. Righe vuote ignorate. Gli errori di rete mostrano il messaggio e permettono di riprovare, senza perdere la cronologia (il turno fallito non viene salvato).

## Gestione errori

Nessun fallback silenzioso. Server spento, timeout, errore HTTP: messaggio leggibile con la causa e il primo controllo da fare. Tool inesistente richiesto dal modello o argomenti non validi: messaggio `tool` con l'errore, mai un successo finto. Limite ai passaggi superato: errore esplicito.

## Test

**Automatici, senza modello acceso** (`pytest`):

1. percorso fisso: risposta senza tool, il grafo termina;
2. cronologia: due turni di seguito, il secondo contiene il primo;
3. bivio: con una funzione-modello finta che chiede il tool, il grafo passa da `tools` e torna a `llm`;
4. orologio con istante controllato: ora attesa nel fuso richiesto;
5. fuso sconosciuto o mancante: errore chiaro;
6. limite ai passaggi: un modello finto che chiede sempre il tool viene fermato a 5.

**Prove reali, separate e attivate esplicitamente** (variabile `PROVA_REALE=1`):

- con LM Studio: il modello `google/gemma-4-e2b` sceglie davvero il tool orologio, il programma lo esegue, la risposta finale usa il risultato. Verifica preliminare già eseguita (2026-11-08): data la richiesta "Che ore sono a Tokyo?", il modello ha restituito `get_current_time({"timezone":"Asia/Tokyo"})` con `finish_reason: tool_calls`. Il giro completo non è ancora provato.
- con Docker: il container raggiunge LM Studio tramite `host.docker.internal`. Rischio noto: se LM Studio ascolta solo su `127.0.0.1` potrebbe non essere raggiungibile; si verifica con la prova.

Nel resoconto finale: che cosa è stato eseguito, con quale esito, che cosa resta da provare. Una risposta simulata non dimostra che il modello sappia usare lo strumento.

## Docker

`Dockerfile` per l'app (immagine Python leggera, dipendenze da `requirements.txt`). `compose.yaml` con `LM_BASE_URL=http://host.docker.internal:1234/v1`, `LM_MODEL` da `.env`, terminale interattivo. Avvio: `docker compose run --rm app`. LM Studio non viene containerizzato.

## Documenti

- `README.md`: configurazione, avvio, test, diagnosi, con solo comandi verificati; comandi anche per PowerShell.
- `SPIEGAZIONE.md`: schema del grafo, come funziona il giro dell'orologio, copione di demo di circa 5 minuti con 2-3 domande brevi da provare prima, domande probabili del docente con risposta.

## Git e ordine di lavoro

Conventional Commits in italiano, uno per incremento, `git status` e controllo del diff prima di ogni commit, staging selettivo. Push solo su richiesta.

1. Grafo fisso + test
2. Chiamata al modello + cronologia
3. Tool orologio + test
4. Prova reale con LM Studio
5. Docker + prova reale
6. README e SPIEGAZIONE

## Criteri di completamento

- `pytest` passa (6 verifiche) senza modello acceso.
- Prova reale: una domanda sull'ora in un fuso esplicito produce una chiamata del tool e una risposta con l'ora vera.
- Una seconda domanda nella stessa sessione dimostra la cronologia.
- `docker compose run --rm app` avvia l'app e risponde (oppure il blocco è documentato con la causa).
- README ed SPIEGAZIONE esistono e i comandi riportati sono stati eseguiti.
