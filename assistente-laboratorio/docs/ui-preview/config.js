/**
 * CONFIGURAZIONE DEL FRONTEND
 *
 * Demo: endpoint vuoto => UI interattiva con risposte dimostrative esplicitamente etichettate.
 * Produzione: imposta l'endpoint del TUO backend esistente, ad esempio "/api/chat".
 *
 * Request JSON:  { message: string, history: [{ role: 'user'|'assistant', content: string }] }
 * Response JSON: { reply: string, tool_used?: string } (alias: response/answer/message; tool/tools)
 *
 * Non eseguiamo i tool dal browser e non forziamo la loro selezione: decide il modello lato backend.
 */
window.LAB_ASSISTANT_CONFIG = {
  endpoint: '',
  headers: {},
  timeoutMs: 60000,
};
