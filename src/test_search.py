# src/test_search.py

from pubmed_client import buscar_pubs_por_filiacion, buscar_por_pmid
import csv

def obtener_datos(pmid: str):
    """Devuelve un dict con el PMID, título y autores (como string)"""
    meta = buscar_por_pmid(pmid)
    resultado = meta["result"][pmid]
 
    title = resultado["title"]
    authors = resultado.get("authors", [])
    nombres = [f"{a.get('name', '')}" for a in authors]
    return {
        "PMID": pmid,
        "Title": title,
        "Authors": "; ".join(nombres)
    }

def main():
    pmids = buscar_pubs_por_filiacion(retmax=100)
    print(f"Encontré {len(pmids)} PMIDs para las variantes de afiliación:")
    
    # Recolectar datos usando map()
    datos = list(map(obtener_datos, pmids))

    # Guardar en CSV
    with open("publicaciones_cipp.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["PMID", "Title", "Authors"])
        writer.writeheader()
        writer.writerows(datos)

    print("\nDatos guardados en publicaciones_cipp.csv")

if __name__ == "__main__":
    main()
