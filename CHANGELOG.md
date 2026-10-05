# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [1.0.0] — 2026-10-05

Primera versión estable: reorganización completa en capas.

### Cambiado
- **Arquitectura en capas** (`domain`, `services`, `infrastructure`, `web`) con diseño `src/` y el paquete `buscador_empleos`. La parte web sigue MVC.
- Las **fuentes de empleo son clases** (`JobSource`) con el cliente HTTP inyectado, en vez de funciones que parchaban módulos.
- `Job.create()` recibe **solo argumentos con nombre** y un reloj inyectable.
- Configuración por **variables de entorno** validadas (`BUSCADOR_*`); nueva línea de comandos (`buscador-empleos`, `python -m buscador_empleos`).
- JavaScript dividido en **módulos ES**; CSS reorganizado con variables de diseño.
- `POST /api/search` responde **202** (antes 200) y **400** con un mensaje si el cuerpo es inválido o faltan cargos o fuentes (antes iniciaba una búsqueda vacía).
- Los errores de la API son siempre JSON; los acentos ya no se escapan en las respuestas.

### Agregado
- Escritura **atómica** de `jobs.json`, acceso seguro entre hilos y errores claros si el archivo está dañado.
- Cabeceras de seguridad con **CSP estricta** (sin scripts ni estilos en línea).
- Endpoint `/api/health`.
- `pyproject.toml`, `ruff`, `mypy --strict`, cobertura mínima del 90 %, integración continua y guía de contribución.
- **260 pruebas** (99 % de cobertura), incluidas pruebas de arquitectura y de la lógica de JavaScript.

### Corregido
- Si fallaba el guardado de una búsqueda, la app no avisaba; ahora lo muestra en pantalla.
- Los grupos de tecnologías ya no están duplicados entre Python y JavaScript.

## [0.x] — antes de la reorganización

Versiones iniciales: búsqueda en siete fuentes, filtros por tecnología, salario y fecha, descripción desplegable y ampliación con cargos relacionados.
