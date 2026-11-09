"""Convertitore di unita': logica pura, senza rete e senza MCP (il server MCP la espone come tool)."""

import math

# unita -> (grandezza, funzione verso l'unita' base, funzione dall'unita' base)
# Base: metro per la lunghezza, grado Celsius per la temperatura.
_UNITA = {
    "m": ("lunghezza", lambda x: x, lambda x: x),
    "km": ("lunghezza", lambda x: x * 1000, lambda x: x / 1000),
    "C": ("temperatura", lambda x: x, lambda x: x),
    "F": ("temperatura", lambda x: (x - 32) * 5 / 9, lambda x: x * 9 / 5 + 32),
}
UNITA_SUPPORTATE = tuple(_UNITA)


def converti(value, from_unit, to_unit):
    """Converte `value` da `from_unit` a `to_unit` (stessa grandezza). Solleva ValueError se non e' possibile.

    Restituisce {"value": numero arrotondato a 6 decimali, "unit": unita' del risultato}.
    """
    # bool e' un sottotipo di int in Python: True non e' un numero sensato da convertire.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("il valore deve essere un numero.")
    if not math.isfinite(value):
        raise ValueError("il valore deve essere un numero finito (no NaN o infinito).")
    for unita in (from_unit, to_unit):
        if not isinstance(unita, str) or unita not in _UNITA:  # str: una lista non e' hashable
            raise ValueError(f"unita' sconosciuta '{unita}'. Unita' ammesse: {', '.join(UNITA_SUPPORTATE)}.")
    grandezza_da, verso_base, _ = _UNITA[from_unit]
    grandezza_a, _, da_base = _UNITA[to_unit]
    if grandezza_da != grandezza_a:
        raise ValueError(
            f"conversione tra grandezze diverse non possibile: {from_unit} ({grandezza_da}) "
            f"e {to_unit} ({grandezza_a})."
        )
    # Arrotondare toglie il rumore dei float (37 C -> 98.60000000000001 F).
    return {"value": round(da_base(verso_base(value)), 6), "unit": to_unit}
