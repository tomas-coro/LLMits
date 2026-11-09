"""Calcolatrice: logica pura, senza rete e senza MCP (il server MCP la espone come tool).

Usa il modulo `ast` e ammette solo numeri e operatori elencati: niente eval/exec, quindi
un'espressione come "__import__('os')" viene rifiutata invece di essere eseguita.
"""

import ast
import math
import operator

MAX_LUNGHEZZA = 200  # caratteri: evita espressioni enormi
MAX_ESPONENTE = 1000  # |esponente| massimo: evita 9 ** 9 ** 9, che bloccherebbe il programma

_BINARI = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARI = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _valuta(nodo):
    """Valuta un nodo dell'albero; solleva ValueError per tutto cio' che non e' ammesso."""
    # type(...) in (int, float) esclude bool (True e' un int in Python) e i complessi.
    if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
        return float(nodo.value)  # tutto in float: niente interi giganti che non entrano in isfinite
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _UNARI:
        return _UNARI[type(nodo.op)](_valuta(nodo.operand))
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _BINARI:
        sinistra = _valuta(nodo.left)
        destra = _valuta(nodo.right)
        if isinstance(nodo.op, ast.Pow) and abs(destra) > MAX_ESPONENTE:
            raise ValueError(f"esponente troppo grande (massimo {MAX_ESPONENTE} in valore assoluto).")
        return _BINARI[type(nodo.op)](sinistra, destra)
    raise ValueError("elemento non ammesso: sono ammessi solo numeri, + - * / ** %, parentesi e meno unario.")


def calcola(expression):
    """Valuta un'espressione aritmetica. Solleva ValueError se non e' possibile.

    Restituisce {"value": numero arrotondato a 6 decimali, "expression": espressione ricevuta}.
    """
    if not isinstance(expression, str):
        raise ValueError("l'espressione deve essere un testo.")
    if not expression.strip():
        raise ValueError("l'espressione e' vuota.")
    if len(expression) > MAX_LUNGHEZZA:
        raise ValueError(f"espressione troppo lunga (massimo {MAX_LUNGHEZZA} caratteri).")
    try:
        albero = ast.parse(expression.strip(), mode="eval")
        valore = _valuta(albero.body)
    except SyntaxError:
        raise ValueError("espressione non valida.") from None
    except ZeroDivisionError:
        raise ValueError("divisione per zero.") from None
    except OverflowError:
        raise ValueError("risultato troppo grande (non finito).") from None
    if isinstance(valore, complex):  # (-8) ** 0.5 in Python da' un numero complesso
        raise ValueError("risultato non reale (numero complesso).")
    if not math.isfinite(valore):
        raise ValueError("risultato non finito (infinito o NaN).")
    # Arrotondare toglie il rumore dei float (0.1 + 0.2 -> 0.30000000000000004).
    return {"value": round(valore, 6), "expression": expression}
