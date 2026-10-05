"""Ayudantes para leer HTML de terceros con BeautifulSoup, con tipos limpios."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from buscador_empleos.domain.text import clean, clean_text


def parse_html(markup: str) -> BeautifulSoup:
    return BeautifulSoup(markup, "html.parser")


def text_of(node: Tag | None, separator: str = " ") -> str:
    """Texto de un nodo con los espacios colapsados; vacío si el nodo no existe."""
    return clean(node.get_text(separator)) if node is not None else ""


def paragraphs_of(node: Tag | None) -> str:
    """Texto de un nodo conservando los saltos de línea (para descripciones largas)."""
    return clean_text(node.get_text("\n")) if node is not None else ""


def attr(node: Tag | None, name: str) -> str:
    """Valor de un atributo como texto; vacío si el nodo o el atributo no existen."""
    if node is None:
        return ""
    value = node.get(name)
    if value is None:
        return ""
    return value if isinstance(value, str) else " ".join(value)


def html_to_text(html: str | None) -> str:
    """HTML de una descripción -> texto con párrafos y viñetas ('• ')."""
    soup = parse_html(html or "")
    for line_break in soup.select("br"):
        line_break.replace_with("\n")
    for item in soup.select("li"):
        item.insert(0, "• ")
    for block in soup.select("p, div, li, ul, ol, h1, h2, h3, h4, h5, h6, tr"):
        block.append("\n")
    return clean_text(soup.get_text(""))
