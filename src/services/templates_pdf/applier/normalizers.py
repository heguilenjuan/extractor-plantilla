from typing import Dict, List, Callable

NORMALIZERS: Dict[str, Callable[[str], str]] = {
    "trim": lambda s: s.strip(),
    "toUpper": lambda s: s.upper(),
    "toLower": lambda s: s.lower(),
    "removeSpaces": lambda s: s.replace(" ", ""),
    "keepDigits": lambda s: "".join(ch for ch in s if ch.isdigit()),
}


def apply_normalizers(text: str, norms: List[str] | None) -> str:
    """Aplica una lista de normalizadores al texto"""
    s = text or ""
    for n in norms or []:
        fn = NORMALIZERS.get(n)
        if fn:
            s = fn(s)
    return s
