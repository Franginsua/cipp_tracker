# src/elsevier_client.py

import requests
import unicodedata
import time
from config import SCOPUS_API_KEY, SCOPUS_INST_TOKEN
from scimago_client import load_scimago_csv, get_quartile_by_issn

# Cargar mapeo ISSN->Quartile
QUARTILE_MAP = load_scimago_csv('scimagojr.csv')

# Endpoint Search API
BASE_SEARCH_URL = 'https://api.elsevier.com/content/search/scopus'


def _normalize(text: str) -> str:
    """
    Normaliza texto eliminando acentos.
    """
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def buscar_publicaciones_elsevier(
    afiliacion: str,
    count: int = 25
) -> list[dict]:
    """
    Busca publicaciones en Scopus/Elsevier por afiliación y devuelve metadatos.
    Incluye variantes de la cadena de afiliación (sin stopwords) para capturar más registros.
    Usa vista STANDARD para ajustarse a límites de servicio.

    Requiere API Key y SCOPUS_INST_TOKEN (opcional para remoto).
    Devuelve lista de dicts con campos:
      - EID, DOI, Title, Authors, Journal, ISSN, Year, Quartile
    """
    # Normalizar afiliación y generar variantes (sin tildes)
    norm = _normalize(afiliacion)
    # Variante sin stopwords comunes: 'de', 'en', 'y'
    words = [w for w in norm.split() if w.lower() not in ('de','en','y')]
    variant = ' '.join(words)
    terms = [norm, variant]
    # Construir consulta OR sobre variantes
    clauses = [f'AFFIL({t})' for t in terms]
    query = ' OR '.join(clauses)

    headers = {'X-ELS-APIKey': SCOPUS_API_KEY}
    if SCOPUS_INST_TOKEN:
        headers['X-ELS-Insttoken'] = SCOPUS_INST_TOKEN

    params = {'query': query, 'count': count, 'view': 'STANDARD'}
    resp = requests.get(BASE_SEARCH_URL, headers=headers, params=params)
    # Depuración de errores
    if resp.status_code == 400:
        print('Error Elsevier API (400): posiblemente sobrepasó el límite de resultados o view no permitido')
        return []
    resp.raise_for_status()
    data = resp.json()
    entries = data.get('search-results', {}).get('entry', [])

    resultados = []
    for entry in entries:
        eid = entry.get('eid','')
        doi = entry.get('prism:doi','')
        title = entry.get('dc:title','')
        journal = entry.get('prism:publicationName','')
        issn = entry.get('prism:issn','')
        cover_date = entry.get('prism:coverDate','')
        year = cover_date.split('-')[0] if cover_date else ''

        # Autores
        authors = []
        if 'author' in entry:
            for a in entry.get('author', []):
                name = a.get('authname') or ''
                authors.append(name)
        elif entry.get('dc:creator'):
            authors = [entry.get('dc:creator')]

        # Quartile
        quartile = get_quartile_by_issn(issn, QUARTILE_MAP)

        resultados.append({
            'EID': eid,
            'DOI': doi,
            'Title': title,
            'Authors': authors,
            'Year': year,
            'Journal': journal,
            'ISSN': issn,
            'Quartile': quartile
        })
        time.sleep(0.2)
    return resultados
