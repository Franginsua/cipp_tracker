# src/test_search.py

from pubmed_client import buscar_pubs_por_filiacion, buscar_por_pmid
import csv


def obtener_datos(pmid: str):
    """
    Devuelve un dict con PMID, título, autores, año y revista.
    """
    meta = buscar_por_pmid(pmid)
    info = meta["result"][pmid]
    title = info.get("title", "")
    # Obtener autores como string
    authors = info.get("authors", [])
    nombres = [a.get("name", "") for a in authors]
    # Año de publicación (primeros 4 caracteres de pubdate)
    pubdate = info.get("pubdate", "")
    year = pubdate[:4] if pubdate else ""
    # Revista abreviada y nombre completo
    journal = info.get("source", "")
    full_journal = info.get("fulljournalname", "")
    return {
        "PMID": pmid,
        "Title": title,
        "Authors": "; ".join(nombres),
        "Year": year,
        "Journal": full_journal or journal
    }


def main():
    pmids = buscar_pubs_por_filiacion(retmax=100)
    print(f"Encontré {len(pmids)} PMIDs para las variantes de afiliación:")

    # Recolectar datos con map()
    datos = list(map(obtener_datos, pmids))

    # Guardar en CSV con columnas extra
    with open("publicaciones_cipp.csv", mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["PMID", "Title", "Authors", "Year", "Journal"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(datos)

    print("\nDatos guardados en publicaciones_cipp.csv")

if __name__ == "__main__":
    main()
