# Specifica - calcolatrice MCP

## Obiettivo e perimetro

Aggiungere un quarto tool, `calculate`, al server MCP esistente. Orologio, convertitore e meteo restano invariati. Fuori perimetro: funzioni matematiche (`sqrt`, `sin`), variabili, router, revisore, resource, prompt, UI.

## Contratto

- `calculate(expression: str)`: valuta un'espressione aritmetica con numeri, `+ - * / ** %`, parentesi e meno unario.
- Parser sicuro con il modulo `ast`: ammette solo nodi numerici e operatori elencati. Mai `eval`/`exec`.
- Risultato: `{"value": numero, "expression": espressione ricevuta}`, arrotondato a 6 decimali come il convertitore.
- Errori chiari, mai un numero inventato, resi come `ToolError`:
  - espressione vuota, non valida o con elementi non ammessi (nomi, chiamate, stringhe);
  - divisione o modulo per zero;
  - risultato non finito;
  - esponente troppo grande (limite fisso, es. |esponente| <= 1000) e lunghezza massima dell'espressione, per evitare calcoli che bloccano il programma.
- Logica pura in `app/calcolatrice.py` (senza MCP); il server la espone in `app/mcp_server.py` con descrizione che elenca gli operatori ammessi.
- L'host acquisisce il tool con la discovery: nessuno schema duplicato nel codice dell'agente.

## Evidenze di accettazione

1. Test senza modello e senza rete: espressioni valide (precedenza, parentesi, meno unario, `**`, `%`), errori (zero, sintassi, nomi, chiamate, `9**9**9`, vuota, troppo lunga).
2. Test MCP: discovery con quattro tool, schema di `calculate`, invocazione diretta e errore come errore del tool.
3. Test del grafo con modello finto: la calcolatrice nello stesso turno con gli altri tool, cronologia e `tool_call_id` invariati.
4. Prova reale distinta con LM Studio (`PROVA_REALE=1`): il modello sceglie `calculate` e usa il risultato; log con richiesta, argomenti, esito. Se manca, dichiararlo.
5. README e CLAUDE.md aggiornati solo dove cambia qualcosa. Nessuna nuova dipendenza.

## Flusso

Branch `feat/calcolatrice` da `dev`. Un commit verificato, con stop e via libera esplicito prima di commit e merge.
