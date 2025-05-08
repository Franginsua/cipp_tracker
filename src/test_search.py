# src/test_search.py

from pubmed_client import buscar_pubs_por_filiacion, buscar_por_pmid
from scimago_client import load_scimago_csv, get_quartile_by_issn
import csv

# Carga el mapeo de ISSN -> Quartile de SCImago
QUARTILE_MAP = load_scimago_csv('scimagojr.csv')


def obtener_datos(pmid: str):
    """
    Devuelve un dict con PMID, DOI, título, autores, año, journal, ISSN y Quartile.
    """
    meta = buscar_por_pmid(pmid)
    info = meta['result'][pmid]

    title = info.get('title', '')
    authors_list = info.get('authors', [])
    authors = [a.get('name', '') for a in authors_list]

    pubdate = info.get('pubdate', '')
    year = pubdate[:4] if pubdate else ''

    # Revista y ISSNs
    journal = info.get('fulljournalname') or info.get('source', '')
    issn = info.get('issn') or info.get('essn', '')

    # Extraer DOI de los articleids, si existe
    doi = ''
    for aid in info.get('articleids', []):
        if aid.get('idtype') == 'doi':
            doi = aid.get('value')
            break

    # Obtener cuartil desde el mapeo de SCImago
    quartile = get_quartile_by_issn(issn, QUARTILE_MAP)

    return {
        'PMID': pmid,
        'DOI': doi,
        'Title': title,
        'Authors': "; ".join(authors),
        'Year': year,
        'Journal': journal,
        'ISSN': issn,
        'Quartile': quartile
    }


def main():
    pmids = buscar_pubs_por_filiacion(retmax=100)
    print(f"Encontré {len(pmids)} PMIDs para las variantes de afiliación:")

    datos = [obtener_datos(pmid) for pmid in pmids]

    with open('publicaciones_cipp.csv', mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['PMID', 'DOI', 'Title', 'Authors', 'Year', 'Journal', 'ISSN', 'Quartile']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(datos)

    print("\nDatos guardados en publicaciones_cipp.csv con DOI y cuartiles incluidos.")


if __name__ == '__main__':
    main()
