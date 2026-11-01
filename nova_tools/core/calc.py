"""Güvenli bilimsel hesap makinesi ve özet (hash) fonksiyonları.

eval() kullanılmaz; ifade AST üzerinden yalnızca izin verilen düğümlerle hesaplanır.
"""
from __future__ import annotations

import ast
import hashlib
import math
import operator
import re


class CalcError(ValueError):
    """Kullanıcıya gösterilecek Türkçe hesaplama hatası."""


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTS = {"pi": math.pi, "π": math.pi, "e": math.e, "tau": math.tau}
MAX_EXPONENT = 10_000
MAX_FACTORIAL = 1000


def _factorial(x: float) -> float:
    if x < 0 or x != int(x):
        raise CalcError("Faktöriyel yalnızca 0 veya pozitif tam sayılar için tanımlıdır.")
    if x > MAX_FACTORIAL:
        raise CalcError(f"Faktöriyel için üst sınır {MAX_FACTORIAL}.")
    return math.factorial(int(x))


def _functions(angle_mode: str) -> dict:
    deg = angle_mode == "deg"
    to_rad = (lambda x: math.radians(x)) if deg else (lambda x: x)
    from_rad = (lambda x: math.degrees(x)) if deg else (lambda x: x)

    def tan(x):
        r = to_rad(x)
        if deg and abs((x % 180) - 90) < 1e-12:
            raise CalcError("tan bu açıda tanımsız.")
        return math.tan(r)

    def log(x):
        if x <= 0:
            raise CalcError("Logaritma yalnızca pozitif sayılar için tanımlıdır.")
        return math.log10(x)

    def ln(x):
        if x <= 0:
            raise CalcError("Logaritma yalnızca pozitif sayılar için tanımlıdır.")
        return math.log(x)

    def sqrt(x):
        if x < 0:
            raise CalcError("Negatif sayının karekökü reel değildir.")
        return math.sqrt(x)

    def asin(x):
        if not -1 <= x <= 1:
            raise CalcError("asin için değer -1 ile 1 arasında olmalı.")
        return from_rad(math.asin(x))

    def acos(x):
        if not -1 <= x <= 1:
            raise CalcError("acos için değer -1 ile 1 arasında olmalı.")
        return from_rad(math.acos(x))

    return {
        "sin": lambda x: math.sin(to_rad(x)),
        "cos": lambda x: math.cos(to_rad(x)),
        "tan": tan,
        "asin": asin,
        "acos": acos,
        "atan": lambda x: from_rad(math.atan(x)),
        "sqrt": sqrt,
        "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
        "log": log,
        "ln": ln,
        "exp": math.exp,
        "abs": abs,
        "fact": _factorial,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,
    }


def normalize(expr: str) -> str:
    s = expr.strip()
    s = (s.replace("×", "*").replace("÷", "/").replace("−", "-")
         .replace("^", "**"))
    s = re.sub(r"√\s*(\d+(?:[.,]\d+)?)", r"sqrt(\1)", s)
    s = s.replace("√", "sqrt")
    # Türkçe ondalık virgül → nokta (çok argümanlı fonksiyon yok)
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    # Yüzde: 50% -> (50/100)
    s = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", s)
    # Faktöriyel: 5! -> fact(5)
    s = re.sub(r"(\d+(?:\.\d+)?)!", r"fact(\1)", s)
    if "!" in s:
        raise CalcError("Faktöriyel yalnızca sayılarda (5!) ya da fact(...) ile kullanılabilir.")
    return s


def evaluate(expr: str, angle_mode: str = "deg") -> float:
    """İfadeyi güvenli biçimde hesaplar. angle_mode: 'deg' veya 'rad'."""
    s = normalize(expr)
    if not s:
        raise CalcError("İfade boş.")
    if len(s) > 500:
        raise CalcError("İfade çok uzun.")
    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError as e:
        raise CalcError("Geçersiz ifade.") from e
    funcs = _functions(angle_mode)

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
                raise CalcError("Üs çok büyük.")
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
                raise CalcError("Sıfıra bölme tanımsız.")
            try:
                return _BIN_OPS[type(node.op)](left, right)
            except OverflowError as e:
                raise CalcError("Sonuç çok büyük.") from e
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Name):
            if node.id in _CONSTS:
                return _CONSTS[node.id]
            raise CalcError(f"Bilinmeyen ad: {node.id}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = funcs.get(node.func.id)
            if fn is None:
                raise CalcError(f"Bilinmeyen fonksiyon: {node.func.id}")
            if len(node.args) != 1 or node.keywords:
                raise CalcError(f"{node.func.id} tek bir değer alır.")
            try:
                return fn(ev(node.args[0]))
            except (ValueError, OverflowError) as e:
                if isinstance(e, CalcError):
                    raise
                raise CalcError(f"{node.func.id} için geçersiz değer.") from e
        raise CalcError("Desteklenmeyen ifade.")

    result = ev(tree)
    if isinstance(result, complex):
        raise CalcError("Sonuç karmaşık sayı.")
    if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
        raise CalcError("Sonuç tanımsız.")
    return result


def format_number(value: float) -> str:
    """Sonucu okunaklı biçimde (Türkçe ondalık virgülüyle) döndürür."""
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer() and abs(value) < 1e16):
        text = str(int(value))
    else:
        if abs(value) >= 1e16 or (value != 0 and abs(value) < 1e-9):
            text = f"{value:.10e}"
        else:
            text = f"{value:.12g}"
            if "e" not in text and "." in text:
                text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def sha256_text(text: str, encoding: str = "utf-8") -> str:
    return hashlib.sha256(text.encode(encoding)).hexdigest()
