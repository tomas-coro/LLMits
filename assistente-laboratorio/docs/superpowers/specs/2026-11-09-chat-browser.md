# Specifica — chat browser locale (lezione 6)

Approvata in chat il 09/11/2026. Una chat accessibile da un browser sul computer dell'utente riusa grafo, LM Studio e i tre tool esistenti; la CLI resta utilizzabile. Nessuna nuova dipendenza, account, database, cloud, streaming o esposizione pubblica.

- Un solo utente e una sola cronologia in memoria, conservata finché il server rimane acceso; al riavvio si azzera. Ricaricare la pagina mostra la cronologia corrente (solo domande e risposte, mai messaggi interni dei tool).
- L'utente può inviare una domanda non vuota; il server la inoltra al grafo, mostra la risposta oppure un errore leggibile. Un turno fallito non entra in cronologia. Invii concorrenti sono serializzati; durante l'attesa l'interfaccia disabilita l'invio.
- Avvio locale in Python, MCP avviato una volta e chiuso all'uscita. Server HTTP in ascolto solo su loopback; in Docker la porta è pubblicata solo su loopback dell'host. Richieste validate (dimensione, tipo JSON, testo, origine e host). Le risposte del modello sono inserite come testo, mai HTML.
- Evidenze: test senza LM Studio per input, cronologia, errori e risposta del grafo; verifica browser su desktop e mobile, oltre alla suite esistente. README e comandi PowerShell aggiornati. Verificare Compose e documentare qualsiasi prova non eseguita. Nessun push senza richiesta.
