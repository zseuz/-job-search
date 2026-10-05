"""Dobles de prueba y ayudantes compartidos. Ninguna prueba usa internet."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from buscador_empleos.domain.job import Job
from buscador_empleos.infrastructure.http import HttpResponse


def no_pause(_low: float, _high: float) -> None:
    """Las fuentes esperan entre peticiones para ser corteses; en las pruebas no se espera."""


class FakeResponse:
    """Respuesta HTTP de mentira."""

    def __init__(self, text: str = "", status: int = 200, data: Any = None) -> None:
        self.status_code = status
        self._data = data
        self.text = json.dumps(data) if data is not None else text

    def json(self) -> Any:
        return self._data if self._data is not None else json.loads(self.text)


@dataclass(frozen=True)
class Call:
    method: str
    url: str
    params: Mapping[str, Any] | None = None
    headers: Mapping[str, str] | None = None
    body: Any = None


Matcher = str | Callable[[Call], bool]
Reply = HttpResponse | Exception | Callable[[Call], HttpResponse]


@dataclass
class FakeHttpClient:
    """Cliente HTTP programable. Las rutas se evalúan en orden y gana la primera que coincida.

    Ejemplo::

        http = FakeHttpClient()
        http.when("/listado", text=LISTADO_HTML)
        http.when(lambda call: call.params["page"] == 2, status=500)
        http.when("/detalle", error=TimeoutError("lento"))
    """

    routes: list[tuple[Matcher, Reply]] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)

    def when(
        self,
        match: Matcher,
        *,
        text: str = "",
        data: Any = None,
        status: int = 200,
        error: Exception | None = None,
        reply: Callable[[Call], HttpResponse] | None = None,
    ) -> FakeHttpClient:
        outcome: Reply = reply or error or FakeResponse(text, status, data)
        self.routes.append((match, outcome))
        return self

    def get(
        self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None
    ) -> HttpResponse:
        return self._answer(Call("GET", url, params, headers))

    def post_json(
        self,
        url: str,
        body: Any,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        return self._answer(Call("POST", url, params, headers, body))

    def urls(self, method: str | None = None) -> list[str]:
        return [c.url for c in self.calls if method in (None, c.method)]

    def _answer(self, call: Call) -> HttpResponse:
        self.calls.append(call)
        for match, outcome in self.routes:
            if (match in call.url) if isinstance(match, str) else match(call):
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome(call) if callable(outcome) else outcome
        raise AssertionError(f"Petición inesperada sin ruta definida: {call.method} {call.url}")


class LogCollector:
    """Recoge los mensajes que una fuente le muestra al usuario."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def __call__(self, message: str) -> None:
        self.messages.append(message)

    def contains(self, fragment: str) -> bool:
        return any(fragment in message for message in self.messages)


def make_job(
    job_id: str = "1", source: str = "Fuente", title: str = "Desarrollador Python", **overrides: Any
) -> Job:
    """Oferta de ejemplo con una descripción real; cualquier campo se puede sobrescribir."""
    fields: dict[str, Any] = {
        "company": "ACME",
        "location": "Bogotá",
        "url": f"https://example.test/{job_id}",
        "posted": "Hace 2 días",
        "description": "Buscamos desarrollador con Python y SQL. " * 5,
    }
    fields.update(overrides)
    return Job.create(source=source, source_id=job_id, title=title, **fields)


@contextmanager
def temp_data_file() -> Iterator[Path]:
    """Ruta de un jobs.json dentro de una carpeta temporal que todavía no existe."""
    with tempfile.TemporaryDirectory() as folder:
        yield Path(folder) / "data" / "jobs.json"
