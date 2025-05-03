# src/pubmed_client.py

import requests
import time
from config import PUBMED_API_KEY


def buscar_por_pmid(pmid: str) -> dict:
    """
    Consulta el resumen de un artículo en PubMed usando su PMID.
    Devuelve un dict con la respuesta JSON.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {
        "db": "pubmed",
        "retmode": "json",
        "id": pmid,
        "api_key": PUBMED_API_KEY
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def buscar_pubs_por_filiacion(
    retmax: int = 100
) -> list[str]:
    """
    Busca PMIDs en PubMed ejecutando búsquedas individuales para cada variante
    de afiliación del CIPP. Devuelve lista de PMIDs únicos (sin duplicados), ordenados.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    terms = [
        # Versiones exactas con comillas
        '"Centro de Investigaciones en Psicología y Psicopedagogía"[Affiliation]',
        '"Centro de Investigaciones en Psicologia y Psicopedagogia"[Affiliation]',
        '"centro de investigaciones en psicologia y psicopedagogía"[Affiliation]',
        '"centro de investigaciones en psicología y psicopedagogia"[Affiliation]',
        # Versiones sin comillas para Automatic Term Mapping
        'Centro de Investigaciones en Psicología y Psicopedagogía[Affiliation]',
        'Centro de Investigaciones en Psicologia y Psicopedagogia[Affiliation]',
        # Sin preposición 'de'
        '"Centro de Investigaciones Psicología y Psicopedagogía"[Affiliation]',
        '"Centro de Investigaciones Psicologia y Psicopedagogia"[Affiliation]',
        # Variante con sigla entre paréntesis
        '"Centro de Investigaciones en Psicología y Psicopedagogía (CIPP)"[Affiliation]',
        '"Centro de Investigaciones en Psicologia y Psicopedagogia (CIPP)"[Affiliation]',
        # Variantes en inglés
        '"Center for Research in Psychology and Psychopedagogy"[Affiliation]',
        'Center for Research in Psychology and Psychopedagogy[Affiliation]',
        '"Center Research Psychology Psychopedagogy"[Affiliation]',
        # Sigla + contexto
        'CIPP[Affiliation] AND Argentina[Affiliation]',
        'CIPP[Affiliation] AND Pontificia Universidad Católica Argentina[Affiliation]',
        'CIPP[Affiliation] AND Pontificia Universidad Catolica Argentina[Affiliation]',
        'CIPP[Affiliation] AND Universidad Católica Argentina[Affiliation]',
        'CIPP[Affiliation] AND Universidad Catolica Argentina[Affiliation]',
        'CIPP[Affiliation] AND Buenos Aires[Affiliation]',
        # Búsqueda por palabras clave individuales con AND
        'Centro[Affiliation] AND Investigaciones[Affiliation] AND Psicología[Affiliation] AND Psicopedagogía[Affiliation]',
        'Centro[Affiliation] AND Investigaciones[Affiliation] AND Psicologia[Affiliation] AND Psicopedagogia[Affiliation]'
    ]
    all_pmids = set()
    for term in terms:
        params = {
            "db": "pubmed",
            "retmode": "json",
            "retmax": retmax,
            "term": term,
            "api_key": PUBMED_API_KEY
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        all_pmids.update(ids)
        time.sleep(0.3)  # Pequeña pausa para no saturar la API
    return sorted(all_pmids)

