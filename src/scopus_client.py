# src/scopus_client.py

import requests
from config import SCOPUS_API_KEY

# Endpoint de búsqueda de artículos en Scopus con metadatos completos
BASE_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"


def buscar_pubs_con_metadatos_scopus(
    afiliacion: str,
    count: int = 25
) -> list[dict]:
    """
    Busca artículos en Scopus por afiliación y devuelve sus metadatos.

    Usa view=COMPLETE para obtener título, autores, revista y año directamente
    del endpoint de búsqueda, solo con la API Key.

    Si recibe 401, retorna lista vacía con advertencia.

    Devuelve lista de dicts con claves: EID, Title, Authors, Journal, Year.
    """
    # Construir headers solo con API Key
    headers = {"X-ELS-APIKey": SCOPUS_API_KEY}
    # Consulta base: sigla institucional UCA
    query = "AFFIL(UCA)"
    params = {"query": query, "count": count, "view": "COMPLETE"}

    resp = requests.get(BASE_SEARCH_URL, headers=headers, params=params)
    if resp.status_code == 401:
        print("Warning: Unauthorized. Verifica tu SCOPUS_API_KEY en config.py.")
        return []
    resp.raise_for_status()

    data = resp.json()
    entries = data.get("search-results", {}).get("entry", [])
    resultados = []

    for entry in entries:
        eid = entry.get("eid")
        title = entry.get("dc:title", "")
        journal = entry.get("prism:publicationName", "")
        cover_date = entry.get("prism:coverDate", "")  # YYYY-MM-DD
        year = cover_date.split("-")[0] if cover_date else ""

        # Autores: lista en 'author' o fallback a 'dc:creator'
        authors = []
        if isinstance(entry.get("author"), list):
            for a in entry.get("author", []):
                name = a.get("authname") or f"{a.get('ce:given-name','')} {a.get('ce:surname','')}".strip()
                authors.append(name)
        elif entry.get("dc:creator"):
            authors = [entry.get("dc:creator")]

        resultados.append({
            "EID": eid,
            "Title": title,
            "Authors": authors,
            "Journal": journal,
            "Year": year
        })

    return resultados









