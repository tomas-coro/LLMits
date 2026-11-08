# Spiegazione del progetto (per la demo)

## 1. In una frase

Un chatbot da terminale che parla con un modello locale e, quando serve l'ora, la chiede a uno strumento vero invece di indovinarla.

## 2. Schema del grafo

```
START -> llm -> bivio --(il modello chiede uno strumento)--> tools -> llm
                  |--(risposta finale)-----------------------> END
                  |--(passaggi >= 5)--> limite --------------> END
```

- **llm:** chiama il modello con tutta la cronologia.
- **bivio:** guarda la risposta e decide la strada (strumento, fine o limite).
- **tools:** esegue lo strumento richiesto e aggiunge il risultato alla cronologia.
- **limite:** ferma il giro dopo 5 chiamate al modello e lascia un messaggio chiaro.

## 3. Il giro dell'orologio, passo per passo

Esempio reale: "Che ore sono a Roma?" -> risposta "Sono le 17:09 di Roma." (ora verificata: coincideva con l'orologio di Roma).

1. L'utente scrive la domanda e il programma la aggiunge alla cronologia.
2. Il modello non risponde con un'ora: chiede lo strumento `get_current_time` con il fuso `Europe/Rome`.
3. Il programma legge davvero l'orologio in quel fuso (il modello non può farlo).
4. Il risultato torna al modello, legato alla richiesta dal `tool_call_id`.
5. Il modello scrive la risposta finale in italiano.

## 4. Perché la cronologia funziona

Il modello non ricorda nulla tra una chiamata e l'altra. Il programma tiene la lista di tutti i messaggi e la rimanda intera a ogni domanda. Per questo, dopo "Mi chiamo Tomas.", alla domanda "Come mi chiamo?" il modello risponde "Ti chiami Tomas." (provato davvero). Chiusa la sessione, la lista sparisce: non c'è persistenza.

## 5. Perché i test non usano il modello

Il modello è lento e non sempre uguale: un test che dipende da lui darebbe esiti diversi a ogni lancio. Nei test il grafo riceve un modello finto con risposte decise in anticipo. Questo **dimostra** che grafo, bivio, cronologia e strumento funzionano. **Non dimostra** che il modello vero sappia scegliere lo strumento: per questo esiste la prova reale (`PROVA_REALE=1`).

## 6. Copione di demo (circa 5 minuti)

Prima di iniziare: avvia LM Studio e fai una domanda di prova per scaldare il modello. Poi una richiesta alla volta.

1. `Mi chiamo Tomas.` Dire: "La conversazione parte, il programma salva i messaggi."
2. `Che ore sono a Tokyo?` Dire: "Qui il modello non indovina: chiede lo strumento e il programma legge l'orologio vero." (provato: risposta con l'ora giusta)
3. `Come mi chiamo?` Dire: "Ricorda il nome perché rimandiamo tutta la cronologia."
4. `Usa lo strumento con timezone 'Atlantide/Poseidonia' e dimmi l'ora.` Dire: "Con un fuso che non esiste lo strumento dà un errore chiaro e il modello lo riporta, senza inventare un'ora." (provato: "il fuso orario 'Atlantide/Poseidonia' non è riconosciuto")

Nota: "Che ore sono su Marte?" non va bene per la demo, perché il modello non chiama lo strumento e risponde che l'ora marziana è diversa (provato).

## 7. Domande probabili del docente

1. **Differenza tra chatbot e agente?** Il chatbot risponde solo con il testo che genera. L'agente può anche chiedere azioni (qui, l'orologio) e usarne il risultato.
2. **Cosa decide il modello e cosa il programma?** Il modello decide se serve lo strumento e con quali argomenti. Il programma decide se e come eseguirlo, valida gli argomenti e fissa il limite.
3. **Perché il limite di 5 passaggi?** Un modello può richiamare lo strumento all'infinito. Il limite garantisce che ogni domanda finisca.
4. **Perché `host.docker.internal`?** Nel container `localhost` è il container stesso. Quel nome punta al computer host, dove gira LM Studio.
5. **Cosa non è provato?** Vedi sezione 8.

## 8. Cosa è stato provato davvero e cosa no

Provato:
- 15 test automatici senza modello: `15 passed, 1 skipped`.
- Prova reale con LM Studio: `1 passed` (11 s), il modello ha chiamato lo strumento.
- Prova a mano da terminale: nome ricordato, ora di Roma corretta (17:09).
- Fuso sconosciuto: errore chiaro, nessuna ora inventata.
- Docker: build riuscita, il container raggiunge LM Studio (stato 200, senza impostazioni extra), risposta "01:20 del 9 novembre 2026 a Tokyo" coincidente con l'ora reale (57 s al primo avvio a freddo).

Non provato:
- Windows / PowerShell (comandi scritti ma non eseguiti).
- Altri modelli oltre a `google/gemma-4-e2b`: un modello diverso può non usare lo strumento.
- Uso interattivo in Docker (`docker compose run --rm app`): provato solo da pipe con `-T`.
- Il modello può rifiutare lo strumento in casi particolari (esempio: "ora su Marte").
