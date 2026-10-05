"""Catalogos del dominio: tecnologias reconocidas y tipos de cargo."""
import re

# Subir este numero al cambiar TECHS o ROLE_RES: las ofertas guardadas se reclasifican una sola vez.
CATALOG_VERSION = 4

TECHS = [
    "Python", "SQL", "R", "Java", "JavaScript", "TypeScript", "C#", ".NET", "C++", "PHP", "Golang",
    "Kotlin", "Swift", "Ruby", "Scala", "React", "Angular", "Vue", "Node.js", "Django", "Flask",
    "FastAPI", "Spring", "Laravel", "Power BI", "Tableau", "Excel", "Looker", "Qlik", "Pandas",
    "Spark", "Hadoop", "Airflow", "dbt", "ETL", "Machine Learning", "Docker", "Kubernetes", "AWS",
    "Azure", "GCP", "Git", "Linux", "PostgreSQL", "MySQL", "SQL Server", "Oracle", "MongoDB", "MariaDB", "SQLite", "PL/SQL", "Redis", "Elasticsearch", "Cassandra", "DynamoDB",
    "Firebase", "Neo4j", "Teradata", "NoSQL",
    "BigQuery", "Snowflake", "Databricks", "Flutter", "React Native", "Android", "iOS",
]
# patrones con limites de palabra que funcionen con simbolos (C#, .NET, C++, Node.js)
TECH_RE = {t: re.compile(r"(?<![\w+#.])" + re.escape(t) + r"(?![\w+#])", re.I if len(t) > 2 else 0)
           for t in TECHS}


ROLE_RES = {
    "Analista de datos": re.compile(
        r"\bdata\b|\bdatos\b|\bbi\b|business intelligence|anal[ií]tica|analytics|estad[ií]stic|"
        r"cient[ií]fic[oa] de|scientist|big ?data|\betl\b|inteligencia de negocio", re.I),
    "Desarrollador": re.compile(
        r"desarrollad|developer|programador|software|back-?end|front-?end|full[ -]?stack|"
        r"ingeniero de sistemas|web master|webmaster|\.net\b|\bjava\b|\bpython\b|\bphp\b|"
        r"\bangular\b|\breact\b|mobile|m[oó]vil|devops", re.I),
}
