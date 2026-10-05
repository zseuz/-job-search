# Buscador de empleos (Bogotá y remoto)

Agrega ofertas de 7 fuentes en español y las muestra en una página con filtros (tecnologías, salario, fecha, modalidad, descripción).

| Grupo | Fuentes |
|---|---|
| Colombia | Computrabajo, elempleo, Hireline |
| Colombia y Latinoamérica (tecnología) | Get on Board, Torre |
| Redes y agregadores | LinkedIn (API pública, sin sesión), Indeed |

Los salarios en otras monedas se convierten a pesos con tasas aproximadas (`FX_TO_COP` en `app/config.py`); el texto original se conserva.
Descartadas: Himalayas, RemoteOK y We Work Remotely (en inglés), Magneto (su búsqueda no responde sin sesión), Jooble (Cloudflare), Glassdoor (exige login), Workana (freelance).

## Uso
```
py -m pip install -r requirements.txt
py run.py          # http://localhost:5000
py -m unittest discover -s tests
```

## Arquitectura MVC
| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Modelo | `app/models` | `Job` (entidad), `extractors` (reglas: salario, modalidad, fecha, tecnologías), `catalog`, `JobRepository` (JSON) |
| Vista | `app/views` | `templates/index.html`, `static/css`, `static/js` |
| Controlador | `app/controllers` | `pages_controller` (página), `jobs_controller` (API `/api/jobs`, `/api/search`, `/api/status`) |
| Servicios | `app/services` | `scrapers/*` (una fuente por archivo) y `SearchService` (búsqueda en segundo plano) |

Para agregar una fuente: crear `app/services/scrapers/<fuente>.py` con una función `(query, pages, log) -> list[Job]` y registrarla en `scrapers/__init__.py`.
"# -job-search" 
