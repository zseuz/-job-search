# Arquitectura

La aplicación está organizada en **cuatro capas** con dependencias en un solo sentido. La parte web sigue **MVC**.

```text
        web  ──▶  services  ──▶  domain  ◀──  infrastructure
```

| Capa | Rol en MVC | Puede importar | No puede importar |
|---|---|---|---|
| `domain` | **Modelo** | solo la biblioteca estándar | Flask, `requests`, `bs4`, las demás capas |
| `services` | casos de uso (Modelo) | `domain`, la interfaz de las fuentes | Flask, `requests`, `bs4` |
| `infrastructure` | adaptadores (Modelo) | `domain` | `services`, `web`, Flask |
| `web` | **Vista + Controlador** | `domain`, `services`, `settings`, `bootstrap` | `infrastructure` directamente |

La raíz de composición (`bootstrap.py`) es el único lugar que conoce las piezas concretas y las conecta.
`tests/test_architecture.py` analiza los `import` de cada archivo y falla si alguna capa rompe estas reglas.

## Vista general

```mermaid
flowchart TB
    U([👤 Navegador])

    subgraph web["🖥️ web — Vista y Controlador"]
        direction TB
        CT["controllers/<br/>pages.py · api.py"]
        SC["schemas.py<br/>validación de entrada"]
        SE["serializers.py<br/>JSON de salida"]
        ER["errors.py · security.py"]
        VW["templates/ · static/<br/>HTML · CSS · JS (módulos ES)"]
    end

    subgraph services["⚙️ services — casos de uso"]
        direction TB
        SS["SearchService<br/>búsqueda en segundo plano"]
        JS["JobService<br/>consulta de ofertas"]
    end

    subgraph domain["🧱 domain — Modelo"]
        direction TB
        JB["Job"]
        RU["salary · dates · modality<br/>classification · catalog"]
        PO["JobRepository<br/>(puerto)"]
    end

    subgraph infra["🔌 infrastructure — adaptadores"]
        direction TB
        SR["sources/<br/>JobSource × 7"]
        HT["http.py<br/>HttpClient"]
        JR["JsonJobRepository"]
        HM["html.py"]
    end

    EXT[["🌍 Portales de empleo"]]
    DB[("💾 data/jobs.json")]

    U <--> VW
    U -->|HTTP| CT
    CT --> SC & SE
    CT --> SS & JS
    SS --> SR
    SS & JS --> PO
    SR --> HT --> EXT
    SR --> HM
    SR -->|crea| JB
    JB --> RU
    JR -.->|implementa| PO
    JR <--> DB
```

## Puertos y adaptadores

El dominio y los servicios dependen de **interfaces**; la infraestructura las implementa. Eso permite probar sin red ni disco y cambiar una pieza sin tocar el resto.

```mermaid
classDiagram
    direction LR
    class JobRepository {
        <<Protocol>>
        +load() Snapshot
        +find(job_id) Job
        +merge(jobs) MergeResult
    }
    class JsonJobRepository {
        -_lock: RLock
        -_cache
        +load() Snapshot
        +find(job_id) Job
        +merge(jobs) MergeResult
    }
    class HttpClient {
        <<Protocol>>
        +get(url, params, headers) HttpResponse
        +post_json(url, body, params, headers) HttpResponse
    }
    class RequestsClient
    class ChromeClient
    class JobSource {
        <<abstract>>
        +name: str
        +search(query, pages, log) list~Job~
    }
    class ComputrabajoSource
    class ElempleoSource
    class IndeedSource
    class SearchService {
        +start(request) bool
        +status() dict
    }
    class JobService {
        +list_jobs() JobListing
        +get_job(id) Job
    }

    JobRepository <|.. JsonJobRepository
    HttpClient <|.. RequestsClient
    HttpClient <|.. ChromeClient
    JobSource <|-- ComputrabajoSource
    JobSource <|-- ElempleoSource
    JobSource <|-- IndeedSource
    JobSource o-- HttpClient : usa
    SearchService o-- JobRepository
    SearchService o-- JobSource : muchas
    JobService o-- JobRepository
```

## Una búsqueda de principio a fin

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant V as Vista (JS)
    participant C as api.py
    participant S as SearchService
    participant X as JobSource
    participant R as JobRepository

    U->>V: «Actualizar ofertas»
    V->>C: POST /api/search
    C->>C: schemas.parse_search_request (valida)
    C->>S: start(SearchRequest)
    S-->>C: aceptada
    C-->>V: 202 Accepted

    loop cada cargo × cada fuente (hilo de fondo)
        S->>X: search(cargo, páginas, log)
        X->>X: listado + detalle de cada oferta
        X-->>S: list[Job]
    end
    S->>R: merge(ofertas)
    R->>R: escritura atómica de jobs.json

    loop mientras corre
        V->>C: GET /api/status
        C-->>V: progreso y registro
    end
    V->>C: GET /api/jobs
    C->>R: load() (con caché)
    C-->>V: JSON
    V-->>U: lista actualizada
```

## Decisiones de diseño

| Decisión | Por qué |
|---|---|
| **Diseño `src/`** y paquete con nombre propio (`buscador_empleos`) | Evita importar el código sin instalar y que el paquete se llame genéricamente `app`. |
| **Dominio sin dependencias externas** | Las reglas (salarios, fechas, clasificación) son lo más valioso y lo que más cambia: deben poder probarse al instante y sin red. |
| **Fuentes como clases con `HttpClient` inyectado** | Las pruebas pasan un cliente falso en vez de parchar módulos. Cada fuente es independiente: agregar una no toca ninguna otra. |
| **Raíz de composición única** (`bootstrap.py`) | Un solo lugar conoce las clases concretas; el resto recibe interfaces. |
| **Configuración por entorno, validada y de solo lectura** (`Settings`) | Un valor inválido detiene el arranque con un mensaje claro, no falla más tarde. |
| **Escritura atómica del JSON** (archivo temporal + reemplazo) | Un corte a mitad de escritura no deja el archivo dañado. |
| **Caché del repositorio invalidada por cambio del archivo** | Reconstruir cada oferta recalcula tecnologías; sin caché cada petición tardaba ~2 s. |
| **Versión del catálogo guardada junto a los datos** | Si cambia la lista de tecnologías, las ofertas guardadas se reclasifican una sola vez. |
| **Validación en el borde** (`schemas.py`) y errores JSON coherentes | El servicio recibe objetos ya válidos; el cliente siempre recibe `{"error": ...}` en la API. |
| **`POST /api/search` responde 202** | La búsqueda es asíncrona: «aceptada», no «terminada». |
| **CSP estricta, sin scripts ni estilos en línea** | La página solo carga recursos propios; se puede prohibir todo lo demás. |
| **Los datos de la página se entregan como JSON, no se duplican en JS** | Los grupos de tecnologías viven una sola vez, en el dominio. |
| **JavaScript en módulos ES; la lógica pura separada del DOM** | `filters.js` se prueba con `node --test` sin navegador. |
| **Pruebas de arquitectura** | Las reglas de capas dejan de ser una convención y pasan a ser una comprobación automática. |

## Cómo extender

- **Una fuente nueva:** ver [CONTRIBUTING.md](../CONTRIBUTING.md#agregar-una-fuente).
- **Otro almacenamiento** (SQLite, etc.): implementar `JobRepository` y pasarlo a `build_container(repository=...)`. Nada más cambia.
- **Otra tecnología o tipo de cargo:** editar `domain/catalog.py` y **subir `CATALOG_VERSION`**.
