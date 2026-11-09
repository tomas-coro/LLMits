# Piano proposto — convertitore e meteo MCP

Specifica: `docs/superpowers/specs/2026-11-09-tool-mcp-convertitore-meteo.md`. **Non iniziare a implementare prima dell'approvazione di questo piano.** Lavorare solo in `assistente-laboratorio/`, nel branch corrente.

## Decisioni tecniche

- Aggiungere soltanto `fastmcp` come nuova dipendenza diretta, con versione fissata dopo verifica della compatibilità con Python 3.13. `requests` e `pytest` sono già installati. Usare client/server FastMCP su stdio; il client è asincrono: gestire esplicitamente il ciclo di vita della sessione nel percorso CLI senza chiamare un client disconnesso. Non implementare MCP a mano.
- Mantenere `app/strumenti.py` per l'orologio; esporre convertitore e meteo nel server MCP in moduli piccoli. In `app/modello.py` inviare all'API LM Studio l'unione dello schema locale e degli schemi ottenuti dal server. In `app/grafo.py` instradare i nomi MCP al client e mantenere gestione degli errori, log, correlazione e limite. In `app/cli.py` avviare/chiudere la connessione MCP e mostrare errori di avvio comprensibili. Evitare di interrompere l'intera sessione per un errore di un singolo tool.
- Open-Meteo: endpoint di geocoding e current forecast, selezionando e dichiarando la prima località tra i risultati. Verificare campi e codici meteo con la documentazione ufficiale; timeout sulle due richieste. Non mettere segreti nel codice o in Git. Non aggiungere API o servizi Docker separati.

## Incrementi, controlli e commit

1. **Convertitore e prima integrazione MCP.** Test del calcolo su unità ammesse/errore, discovery e call diretta via stdio; test del grafo con modello finto per tool MCP e orologio nello stesso turno. Solo dopo implementare server, client e wiring, senza perdere i test esistenti. Eseguire `python -m pytest -q` e una prova reale dedicata con LM Studio. Aggiornare README con comandi verificati, controllare `git status` e diff, commit selettivo `feat(mcp): integra il convertitore di unità` solo se verificato.
2. **Meteo.** Test HTTP con `requests` simulato (città unica/ambigua/inesistente, timeout, status HTTP e JSON/campi invalidi); implementare `get_weather` sullo stesso server e verificare discovery e call diretta, oltre al grafo con modello simulato. Verificare Open-Meteo reale, poi prova end-to-end con LM Studio, poi Docker Compose (LM Studio sull'host, rete per il meteo). Aggiornare README/CLAUDE.md se necessari, test completi, status/diff, commit selettivo `feat(mcp): aggiunge il meteo da Open-Meteo` solo se verificato.
3. **Consegna.** Riportare test eseguiti e risultati separando simulazioni da prove reali; indicare esplicitamente eventuali prove non eseguibili. Nessun push senza richiesta.

## Rischi da monitorare

- Compatibilità FastMCP/Python 3.13 e gestione della sessione async MCP accanto alla CLI e al grafo sincroni: scegliere il collegamento più piccolo che mantenga una sessione valida, senza riscrivere l'applicazione.
- Un modello locale può non selezionare correttamente più tool: la prova reale è indispensabile; il test simulato da solo non prova la selezione.
- Open-Meteo e rete Docker possono essere irraggiungibili: distinguere il blocco esterno da un difetto del grafo.
