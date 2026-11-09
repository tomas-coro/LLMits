"""Server MCP (trasporto stdio): pubblica gli strumenti che l'agente scopre con la discovery.

Si avvia come processo separato: `python -m app.mcp_server`. Il client lo lancia da solo.
Su stdout passa il protocollo MCP: qui dentro niente print().
"""

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from app.calcolatrice import calcola
from app.convertitore import converti
from app.meteo import ErroreMeteo, ottieni_meteo

mcp = FastMCP("assistente-laboratorio")


@mcp.tool(name="convert_units")
def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Converte un valore tra unita' della stessa grandezza.

    Unita' supportate: m, km (lunghezza); C, F (temperatura, C = Celsius, F = Fahrenheit).
    Le unita' vanno scritte esattamente cosi' (C e F maiuscole). Non converte tra grandezze diverse.
    Restituisce il valore convertito (campo value) e la sua unita' (campo unit).
    """
    try:
        return converti(value, from_unit, to_unit)
    except ValueError as errore:
        # ToolError: l'errore arriva al client come errore del tool, non come successo.
        raise ToolError(f"Errore: {errore}") from None


@mcp.tool(name="get_weather")
def get_weather(city: str) -> dict:
    """Meteo attuale di una citta' (dati Open-Meteo, richiede la rete).

    Passare il nome della citta' (es. "Roma"). Restituisce la localita' scelta (location), la
    temperatura in °C (temperature_c), le condizioni (conditions) e l'istante di riferimento con
    fuso (time). Se piu' localita' hanno lo stesso nome sceglie la prima e lo dichiara nel campo note.
    """
    try:
        return ottieni_meteo(city)
    except ErroreMeteo as errore:
        raise ToolError(f"Errore: {errore}") from None


@mcp.tool(name="calculate")
def calculate(expression: str) -> dict:
    """Calcola un'espressione aritmetica.

    Operatori ammessi: + - * / ** % (somma, sottrazione, moltiplicazione, divisione, potenza, resto),
    parentesi e meno unario. Solo numeri: niente funzioni (sqrt, sin) ne' variabili. Esempio: "(12 + 8) * 7 - 5".
    Restituisce il risultato (campo value) e l'espressione ricevuta (campo expression).
    """
    try:
        return calcola(expression)
    except ValueError as errore:
        raise ToolError(f"Errore: {errore}") from None


if __name__ == "__main__":
    mcp.run(show_banner=False)
