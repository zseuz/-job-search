"""Catálogos del dominio: tecnologías reconocidas, tipos de cargo y búsquedas relacionadas."""

from __future__ import annotations

import re
from collections.abc import Mapping

#: Súbelo cada vez que cambies ``TECHS`` o ``ROLE_PATTERNS``: las ofertas guardadas se reclasifican una vez.
CATALOG_VERSION = 4

ROLE_DATA = "Analista de datos"
ROLE_DEVELOPER = "Desarrollador"
ROLE_OTHER = "Otros"

TECHS: tuple[str, ...] = (
    "Python",
    "SQL",
    "R",
    "Java",
    "JavaScript",
    "TypeScript",
    "C#",
    ".NET",
    "C++",
    "PHP",
    "Golang",
    "Kotlin",
    "Swift",
    "Ruby",
    "Scala",
    "React",
    "Angular",
    "Vue",
    "Node.js",
    "Django",
    "Flask",
    "FastAPI",
    "Spring",
    "Laravel",
    "Power BI",
    "Tableau",
    "Excel",
    "Looker",
    "Qlik",
    "Pandas",
    "Spark",
    "Hadoop",
    "Airflow",
    "dbt",
    "ETL",
    "Machine Learning",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "GCP",
    "Git",
    "Linux",
    "PostgreSQL",
    "MySQL",
    "SQL Server",
    "Oracle",
    "MongoDB",
    "MariaDB",
    "SQLite",
    "PL/SQL",
    "Redis",
    "Elasticsearch",
    "Cassandra",
    "DynamoDB",
    "Firebase",
    "Neo4j",
    "Teradata",
    "NoSQL",
    "BigQuery",
    "Snowflake",
    "Databricks",
    "Flutter",
    "React Native",
    "Android",
    "iOS",
)

# Límites de palabra que funcionan con símbolos (C#, .NET, C++, Node.js). Los nombres de una o dos
# letras ('R', 'Go') distinguen mayúsculas para no confundirse con palabras comunes.
TECH_PATTERNS: Mapping[str, re.Pattern[str]] = {
    tech: re.compile(
        r"(?<![\w+#.])" + re.escape(tech) + r"(?![\w+#])",
        re.IGNORECASE if len(tech) > 2 else 0,
    )
    for tech in TECHS
}

ROLE_PATTERNS: Mapping[str, re.Pattern[str]] = {
    ROLE_DATA: re.compile(
        r"\bdata\b|\bdatos\b|\bbi\b|business intelligence|anal[ií]tica|analytics|estad[ií]stic|"
        r"cient[ií]fic[oa] de|scientist|big ?data|\betl\b|inteligencia de negocio",
        re.IGNORECASE,
    ),
    ROLE_DEVELOPER: re.compile(
        r"desarrollad|developer|programador|software|back-?end|front-?end|full[ -]?stack|"
        r"ingeniero de sistemas|web master|webmaster|\.net\b|\bjava\b|\bpython\b|\bphp\b|"
        r"\bangular\b|\breact\b|mobile|m[oó]vil|devops",
        re.IGNORECASE,
    ),
}

#: Búsquedas adicionales que se lanzan cuando el usuario pide ampliar los resultados.
RELATED_QUERIES: Mapping[str, tuple[str, ...]] = {
    ROLE_DATA: (
        "data analyst",
        "analista de bi",
        "analista de inteligencia de negocios",
        "ingeniero de datos",
        "científico de datos",
    ),
    ROLE_DEVELOPER: (
        "programador",
        "ingeniero de software",
        "desarrollador backend",
        "desarrollador frontend",
        "desarrollador full stack",
    ),
}

#: Etiquetas de contrato que se reconocen entre las etiquetas de una oferta.
CONTRACT_PATTERN = re.compile(
    r"t[eé]rmino|indefinid|fijo|obra|prestaci|aprendiz|pr[aá]ctic|temporal|freelance", re.IGNORECASE
)

#: Cómo se agrupan las tecnologías en el filtro de la página. Cada tecnología de ``TECHS`` está en un grupo.
TECH_GROUPS: Mapping[str, tuple[str, ...]] = {
    "Lenguajes": (
        "Java",
        "Python",
        "JavaScript",
        "TypeScript",
        "C#",
        "PHP",
        "Golang",
        "Kotlin",
        "Swift",
        "Ruby",
        "Scala",
        "C++",
        "R",
        "SQL",
    ),
    "Frameworks y plataformas": (
        "Angular",
        "React",
        "Vue",
        "Node.js",
        ".NET",
        "Spring",
        "Django",
        "Flask",
        "FastAPI",
        "Laravel",
        "Flutter",
        "React Native",
        "Android",
        "iOS",
    ),
    "Datos y BI": (
        "Power BI",
        "Tableau",
        "Excel",
        "Looker",
        "Qlik",
        "Pandas",
        "Spark",
        "Hadoop",
        "Airflow",
        "dbt",
        "ETL",
        "Machine Learning",
        "BigQuery",
        "Snowflake",
        "Databricks",
    ),
    "Bases de datos": (
        "PostgreSQL",
        "MySQL",
        "SQL Server",
        "Oracle",
        "PL/SQL",
        "MongoDB",
        "NoSQL",
        "MariaDB",
        "SQLite",
        "Redis",
        "Elasticsearch",
        "Cassandra",
        "DynamoDB",
        "Firebase",
        "Neo4j",
        "Teradata",
    ),
    "Nube y DevOps": ("Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "Linux"),
}
