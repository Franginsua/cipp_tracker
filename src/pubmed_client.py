# src/pubmed_client.py

import requests
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
    resp.raise_for_status()   # Lanza error si no fue 200 OK
    return resp.json()
