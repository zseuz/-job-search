# Cómo contribuir

## Preparar el entorno

```bash
py -m venv .venv
.venv\Scripts\activate              # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

## Antes de enviar un cambio

Deben pasar las cuatro comprobaciones (las mismas que corre la integración continua):

```bash
ruff check src tests && ruff format --check src tests   # estilo y errores probables
mypy                                                    # tipado estricto
coverage run -m unittest discover -s tests -t .         # pruebas
coverage report                                         # exige al menos 90 % de cobertura
```

- Todo cambio de comportamiento lleva **su prueba**. Las pruebas no usan internet: se usa `FakeHttpClient` (`tests/support.py`).
- Si cambias la lista de tecnologías o de cargos, **sube `CATALOG_VERSION`** en `domain/catalog.py`.
- Si cambias un campo que devuelve `/api/jobs`, actualiza también `filters.js`/`render.js` (hay una prueba que fija ese contrato).

## Reglas de arquitectura

Las dependencias van en un solo sentido: `web → services → domain ← infrastructure`.
`tests/test_architecture.py` lo comprueba. En corto:

- `domain/` solo usa la biblioteca estándar.
- `services/` no importa Flask ni los detalles de la red.
- Solo `web/` importa Flask.
- No uses `print()`: usa `logging` o el `log` que recibe cada fuente.
- Las dependencias se **reciben por constructor**; solo `bootstrap.py` crea objetos concretos.

## Agregar una fuente

1. Crea `src/buscador_empleos/infrastructure/sources/<fuente>.py` con una clase que herede de `JobSource`:

   ```python
   from buscador_empleos.domain.job import Job
   from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log


   class MiFuenteSource(JobSource):
       name = "MiFuente"

       def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
           jobs: list[Job] = []
           for page in range(1, pages + 1):
               try:
                   response = self._get("https://mifuente.test/buscar", params={"q": query, "page": page})
               except Exception as exc:          # una página caída no debe tumbar la búsqueda
                   log(f"  MiFuente: fallo ({exc})")
                   break
               ...                               # recorrer los resultados
               jobs.append(Job.create(source=self.name, source_id="123", title="...", url="...",
                                      posted="Hace 2 días", description="...", tags=["Término fijo"]))
               self._pause(0.5, 1.0)             # espera cortés entre peticiones
           return jobs
   ```

   - Si la fuente ya trae salario o modalidad estructurados, pásalos con `salary=Salary(texto, minimo_cop)` y `modality=...`.
   - Convierte monedas con `to_cop_monthly(..., rates=self._rates)`.
2. Regístrala en `build_sources()` (`infrastructure/sources/__init__.py`).
3. Escribe `tests/infrastructure/sources/test_<fuente>.py` con HTML o JSON de ejemplo y un `FakeHttpClient`.

Aparece sola en las casillas de la página y en el filtro de fuentes.

## Estilo

- Python: `ruff format` y `ruff check` (configurados en `pyproject.toml`). Tipos en todo el código de `src/`.
- Comentarios y documentación en español; identificadores en inglés.
- Mensajes de commit en imperativo y con el motivo del cambio.
