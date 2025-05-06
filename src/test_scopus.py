# src/test_scopus.py

from scopus_client import buscar_pubs_con_metadatos_scopus
import csv


def main():
    afiliacion = "Centro de Investigaciones en Psicología y Psicopedagogía"
    # Obtener artículos con metadatos completos (sin depender de token)
    articulos = buscar_pubs_con_metadatos_scopus(afiliacion, count=25)
    print(f"Encontré {len(articulos)} artículos en Scopus para la afiliación:")
    for art in articulos:
        print(f" - EID {art['EID']}: {art['Title']} ({art['Year']}) en {art['Journal']}")
        print(f"    Autores: {', '.join(art['Authors'])}\n")

    # Guardar en CSV
    with open("publicaciones_scopus.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = ["EID", "Title", "Authors", "Year", "Journal"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for art in articulos:
            writer.writerow({
                "EID": art["EID"],
                "Title": art["Title"],
                "Authors": "; ".join(art["Authors"]),
                "Year": art["Year"],
                "Journal": art["Journal"]
            })
    print("Datos guardados en publicaciones_scopus.csv")

if __name__ == "__main__":
    main()

