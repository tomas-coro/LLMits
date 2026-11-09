# Specifica — convertitore e meteo MCP

## Obiettivo e perimetro

Estendere l'agente della lezione 4 con due nuovi tool MCP, uno alla volta: convertitore di unità e meteo. L'orologio locale esistente rimane disponibile; totale: tre tool. Non implementare router, revisore, resource, prompt, UI o altri tool della lezione 6.

## Contratti

- `convert_units(value, from_unit, to_unit)`: numero finito e unità fra `m`, `km`, `C`, `F`. Converte soltanto all'interno della stessa grandezza; risultato numerico e unità esplicita. Rifiuta numero non finito, unità sconosciute e conversioni tra grandezze diverse con errore chiaro. Le unità supportate vanno documentate nel catalogo MCP.
- `get_weather(city)`: geocodifica la città tramite Open-Meteo e consulta il meteo attuale. Restituisce località scelta (anche paese/regione se disponibili), temperatura in °C, condizioni comprensibili e istante di riferimento con fuso. Se più località coincidono, la scelta non deve essere silenziosa: dichiarare quella selezionata. Distinguere città assente/non trovata, timeout o servizio irraggiungibile, risposta HTTP o JSON non valida; non inventare dati. Timeout di rete espliciti. L'accesso alla rete è richiesto solo per questo tool.
- Il server MCP pubblica nomi, descrizioni e schemi; l'host li acquisisce con discovery e inoltra le invocazioni al server, non duplica gli schemi MCP nel codice dell'agente. Usare un trasporto MCP locale stdio. Il tool dell'orologio conserva il suo contratto locale.
- Il grafo conserva la cronologia OpenAI, un risultato per ogni tool call con il suo `tool_call_id`, i log di richiesta/esito e il limite di cinque chiamate al modello. Un errore del tool non deve apparire come successo. La CLI resta l'interfaccia utente; LM Studio resta sull'host. Server MCP e agente possono vivere nello stesso container Compose, come processi separati via stdio.

## Evidenze di accettazione

1. Test isolati senza modello e senza rete: conversioni valide e non valide; meteo con risposte HTTP simulate, città ambigua, città assente, timeout, payload inatteso.
2. Test del server MCP: discovery di entrambi i tool, nomi/schemi e invocazioni dirette. Test del grafo con modello simulato: inoltro, risposta correlata, cronologia, limite e orologio invariati.
3. Prove reali distinte: LM Studio sceglie ciascun tool e usa il risultato nella risposta; il meteo consulta davvero Open-Meteo; log con richiesta, argomenti, esito e correlazione. Verifica da Docker con accesso alla rete e a LM Studio. Se una prova manca/fallisce, dichiararla esplicitamente.
4. README e CLAUDE.md aggiornati dove cambiano comandi, dipendenze e confini; un commit verificato per incremento. Nessun segreto o archivio temporaneo nel repository.

Specifica proposta in chat e approvata dall'utente prima del piano; il piano richiede approvazione separata prima di modificare il codice.
