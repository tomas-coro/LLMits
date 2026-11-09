# Piano — chat browser locale

Specifica: `docs/superpowers/specs/2026-11-09-chat-browser.md`. Approvato in chat il 09/11/2026. Base: `dev` dopo il merge fast-forward del branch MCP, sviluppo su `feat/frontend`.

1. Aggiungere `app/web.py`: HTTP server stdlib con risorsa HTML e API JSON per la domanda e per ricaricare la cronologia. Riutilizzare `SYSTEM_PROMPT`, `costruisci_grafo`, `chiama_modello` e `ClientMcp`. Validare input/host/origine, gestire errori senza compromettere la cronologia e chiudere il client MCP all'uscita.
2. Aggiungere una sola pagina statica `app/chat.html`: layout responsivo, etichette accessibili, stato di caricamento e messaggi senza `innerHTML`. Nessuna dipendenza o servizio esterno.
3. Test HTTP con grafo finto in `tests/test_web.py`: validazione, cronologia, errori, risposta, testo non interpretato come HTML; verificare i test esistenti e visivamente il browser. Aggiornare README e CLAUDE.md; aggiungere un servizio web a Compose senza cambiare la CLI. Verificare Docker, controllare diff/status e fare un commit selettivo sul branch della funzione. Push solo su richiesta.
