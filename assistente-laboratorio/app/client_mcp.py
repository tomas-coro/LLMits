"""Client MCP sincrono per il resto del programma (grafo e CLI sono sincroni, FastMCP e' asincrono).

Un thread di servizio con il suo event loop tiene aperta UNA sessione verso il server per tutta la
durata del programma: il server parte una volta sola e `chiama` e' una normale funzione bloccante.
"""

import asyncio
import gc
import sys
import threading
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

RADICE = Path(__file__).resolve().parent.parent  # cartella che contiene `app/`, da cui parte il server
TIMEOUT = 30  # secondi: avvio del server e ogni singola chiamata


class ErroreMcp(Exception):
    """Il server MCP non si avvia o non risponde, con un messaggio gia' leggibile per l'utente."""


class ClientMcp:
    def __init__(self, comando=sys.executable, args=("-m", "app.mcp_server"), timeout=TIMEOUT):
        self._comando, self._args = comando, list(args)
        self._timeout = timeout
        self._loop = None
        self._thread = None
        self._schemi = []
        self._nomi = set()
        self._esito = {}  # compilato dal thread di servizio se l'avvio fallisce
        self._fermata = None  # asyncio.Event: quando scatta, la sessione si chiude
        self._sessione = None

    # --- ciclo di vita -------------------------------------------------------------------------

    def avvia(self):
        """Avvia il server, apre la sessione e acquisisce gli strumenti (discovery). Solleva ErroreMcp."""
        self._loop = asyncio.new_event_loop()
        pronto = threading.Event()
        self._thread = threading.Thread(target=self._esegui_loop, args=(pronto,), daemon=True)
        self._thread.start()
        if not pronto.wait(self._timeout + 5):
            self.chiudi()
            raise ErroreMcp("Server MCP: avvio scaduto.")
        if "errore" in self._esito:
            self.chiudi()
            raise ErroreMcp(f"Server MCP non avviato: {self._esito['errore']}")

    def chiudi(self):
        """Chiude la sessione e termina il server. Si puo' chiamare piu' volte."""
        if self._loop is None:
            return
        if self._fermata is not None:
            self._loop.call_soon_threadsafe(self._fermata.set)
        self._thread.join(timeout=self._timeout)
        self._loop.close()
        self._loop = None

    def __enter__(self):
        self.avvia()
        return self

    def __exit__(self, *_):
        self.chiudi()

    def _esegui_loop(self, pronto):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._vita(pronto))
        # Fa distruggere ora transport e client (cicli di riferimenti compresi), mentre il loop e' ancora aperto.
        gc.collect()

    async def _vita(self, pronto):
        # Apertura, uso e chiusura della sessione avvengono tutte in questo task.
        self._fermata = asyncio.Event()
        try:
            # Il transport nasce e muore dentro questa funzione, cioe' prima che il loop si chiuda
            # (il suo __del__ tocca il loop: se il loop fosse gia' chiuso darebbe un errore).
            transport = StdioTransport(self._comando, self._args, cwd=str(RADICE))
            async with Client(transport, timeout=self._timeout) as client:
                tools = await client.list_tools()
                self._schemi = [_in_formato_openai(t) for t in tools]
                self._nomi = {t.name for t in tools}
                self._sessione = client
                pronto.set()
                await self._fermata.wait()
        except Exception as errore:  # noqa: BLE001 - qualsiasi problema di avvio va riportato all'utente
            if not pronto.is_set():
                self._esito["errore"] = str(errore) or type(errore).__name__
                pronto.set()
        finally:
            self._sessione = None

    # --- uso -----------------------------------------------------------------------------------

    @property
    def schemi(self):
        """Gli strumenti scoperti sul server, nel formato `tools` dell'API OpenAI."""
        return list(self._schemi)

    def ha_tool(self, nome):
        return nome in self._nomi

    def chiama(self, nome, argomenti):
        """Invoca uno strumento del server. Restituisce sempre un testo: mai un'eccezione, mai un errore mascherato da successo."""
        if self._loop is None or self._sessione is None:
            return "Errore: server MCP non disponibile."
        futuro = asyncio.run_coroutine_threadsafe(self._chiama(nome, argomenti), self._loop)
        try:
            return futuro.result(self._timeout + 5)
        except Exception as errore:  # noqa: BLE001 - un tool rotto non deve fermare la sessione
            futuro.cancel()
            return f"Errore: chiamata a '{nome}' fallita ({str(errore) or type(errore).__name__})."

    async def _chiama(self, nome, argomenti):
        risultato = await self._sessione.call_tool(nome, argomenti, raise_on_error=False)
        testo = "\n".join(b.text for b in risultato.content if getattr(b, "text", None))
        if risultato.is_error:
            # Il server e' raggiungibile ma il tool ha fallito: il testo diventa un errore esplicito.
            return testo if testo.startswith("Errore") else f"Errore: {testo or 'il tool ha restituito un errore.'}"
        return testo


def _in_formato_openai(tool):
    """Da definizione MCP (nome, descrizione, schema JSON) a definizione `tools` di OpenAI/LM Studio."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }
