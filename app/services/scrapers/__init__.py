"""Registro de fuentes de empleo: nombre visible -> funcion de busqueda(query, paginas, log)."""
from app.services.scrapers.computrabajo import computrabajo
from app.services.scrapers.elempleo import elempleo
from app.services.scrapers.getonboard import getonboard
from app.services.scrapers.hireline import hireline
from app.services.scrapers.indeed import indeed
from app.services.scrapers.linkedin import linkedin
from app.services.scrapers.torre import torre

SOURCES = {
    # Colombia
    "Computrabajo": computrabajo, "elempleo": elempleo, "Hireline": hireline,
    # Colombia y Latinoamérica (tecnología)
    "Get on Board": getonboard, "Torre": torre,
    # Redes y agregadores
    "LinkedIn": linkedin, "Indeed": indeed,
}
