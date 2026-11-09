"""Chat HTTP locale: stessa conversazione e stessi strumenti della CLI, senza dipendenze web."""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

from app.cli import SYSTEM_PROMPT
from app.client_mcp import ClientMcp, ErroreMcp
from app.grafo import costruisci_grafo
from app.modello import ErroreModello, chiama_modello

PAGINA = Path(__file__).with_name("chat.html")
PORTA = 8765


def crea_handler(grafo):
    cronologia = [{"role": "system", "content": SYSTEM_PROMPT}]

    class ChatHandler(BaseHTTPRequestHandler):
        def rispondi(self, stato, dati, tipo="application/json; charset=utf-8"):
            corpo = json.dumps(dati, ensure_ascii=False).encode("utf-8") if tipo.startswith("application/json") else dati
            self.send_response(stato)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(corpo)

        def autorizzato(self):
            host = self.headers.get("Host")
            return host in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}") and (
                not self.headers.get("Origin") or self.headers["Origin"] == f"http://{host}"
            )

        def do_GET(self):
            if not self.autorizzato():
                return self.rispondi(403, {"error": "Origine non consentita."})
            if self.path == "/":
                return self.rispondi(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/api/messages":
                visibili = [{"role": m["role"], "content": m["content"]} for m in cronologia
                            if m["role"] in ("user", "assistant") and m.get("content") and not m.get("tool_calls")]
                return self.rispondi(200, {"messages": visibili})
            self.rispondi(404, {"error": "Pagina non trovata."})

        def do_POST(self):
            if not self.autorizzato():
                return self.rispondi(403, {"error": "Origine non consentita."})
            if self.path != "/api/chat":
                return self.rispondi(404, {"error": "Pagina non trovata."})
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self.rispondi(415, {"error": "Inviare JSON."})
            try:
                lunghezza = int(self.headers.get("Content-Length", ""))
            except ValueError:
                lunghezza = 0
            if not 0 < lunghezza <= 4096 or self.headers.get("Transfer-Encoding"):
                return self.rispondi(400, {"error": "Domanda troppo lunga o mancante (massimo 4096 byte)."})
            try:
                dati = json.loads(self.rfile.read(lunghezza))
            except (ValueError, UnicodeDecodeError):
                return self.rispondi(400, {"error": "JSON non valido."})
            domanda = dati.get("message") if isinstance(dati, dict) else None
            if not isinstance(domanda, str) or not domanda.strip():
                return self.rispondi(400, {"error": "Scrivi una domanda prima di inviarla."})
            try:
                risultato = grafo.invoke({"messages": cronologia + [{"role": "user", "content": domanda.strip()}], "passaggi": 0})
            except ErroreModello as errore:
                return self.rispondi(502, {"error": str(errore)})
            except Exception:
                logging.exception("Errore durante la domanda")
                return self.rispondi(500, {"error": "Errore interno: riprova la domanda."})
            cronologia[:] = risultato["messages"]
            self.rispondi(200, {"answer": cronologia[-1]["content"]})

    return ChatHandler


def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="[log] %(message)s")
    for variabile in ("LM_BASE_URL", "LM_MODEL"):
        if variabile not in os.environ:
            print(f"Errore: variabile {variabile} mancante. Copiare .env.example in .env e compilarlo.")
            return 1
    try:
        with ClientMcp() as client:
            grafo = costruisci_grafo(lambda messages: chiama_modello(messages, client.schemi), client_mcp=client)
            with HTTPServer((os.getenv("WEB_HOST", "127.0.0.1"), PORTA), crea_handler(grafo)) as server:
                print(f"Chat disponibile su http://127.0.0.1:{PORTA}/", flush=True)
                server.serve_forever()
    except ErroreMcp as errore:
        print(errore)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
