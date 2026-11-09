# Assistente di laboratorio — interfaccia responsive

Frontend indipendente, senza dipendenze npm e senza font/CDN esterni. Include la nuova identità visiva, 5 icone SVG animate, scaffale orizzontale espandibile, home e conversazione distinte, suggerimenti che **compilano soltanto il campo**, stato di invio/attesa/errore, layout mobile e supporto `prefers-reduced-motion`.

## Avvio

Da questa cartella:

```bash
python3 -m http.server 8000
```

Apri `http://localhost:8000` nel browser. Per testare la grafica, non servono installazioni o un LLM.

## Demo e backend reale

Per impostazione predefinita, `config.js` contiene `endpoint: ''`: **la demo NON è collegata al modello locale**. Mostra risposte illustrative per alcune domande d'esempio, con etichette *Dimostrazione*. L'ora dimostrativa viene calcolata dal browser; le conversioni hanno esempi deterministici; il meteo non viene inventato.

Per usare la chat già funzionante nel progetto originale:

1. Copia i file frontend dentro il progetto, rispettando i percorsi.
2. Inserisci in `config.js` l'URL del **backend esistente** (ad esempio `endpoint: '/api/chat'`).
3. Allinea il contratto di `callBackend()` in `app.js` con quello esposto dal tuo server. Quello incluso è un adattatore generico a JSON.

### Contratto di API previsto dalla demo

**POST** all'endpoint definito:

```json
{
  "message": "Che ore sono a Tokyo?",
  "history": [
    { "role": "user", "content": "Ciao" },
    { "role": "assistant", "content": "Ciao!" }
  ]
}
```

Risposta prevista:

```json
{
  "reply": "A Tokyo sono le 22:04.",
  "tool_used": "Ora"
}
```

Sono accettati anche `response`, `answer` o `message` al posto di `reply`; e `tool`, `tools` al posto di `tool_used`. Questo non afferma che il tuo backend segua già tale contratto: **va verificato** contro il sorgente originale. Se il backend usa SSE/streaming, va adattata `callBackend()`.

Le **schede non chiamano i tool** e non cambiano parametri di invocazione: servono a descrivere le capacità. Solo il backend, insieme al modello locale, decide quale strumento usare. L'etichetta `Strumento: X` appare se il backend comunica `tool_used`.

## Aggiungere strumenti

Nel file `app.js`, aggiungi una voce al registro `capabilities`, con `{id, title, subtitle, kind, description, examples}` e la corrispondente icona SVG in `icons`. Lo scaffale si adatta automaticamente: desktop scorrevole/espandibile, mobile a scorrimento orizzontale. Per una capacità futura usa `kind:'future'` e `examples:[]` fino all'integrazione effettiva.

## Vincoli e limiti dichiarati

- Nessuna cronologia persistente: messaggi conservati **solo in memoria** nella pagina aperta.
- Nessuna promessa che meteo o backend siano offline: la località riguarda il modello eventualmente configurato dal progetto originale.
- `Backend configurato` significa URL presente, non connessione/model serving verificati.
- Nessuna libreria caricata dalla rete; nessun contenuto dell'utente iniettato come HTML.
- Questa consegna **non modifica** il progetto originale, perché non è stato fornito né individuato il suo repository.
