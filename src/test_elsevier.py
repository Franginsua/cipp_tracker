# src/test_elsevier.py

from elsevier_client import buscar_publicaciones_elsevier
import csv


def main():
    # Uso de búsqueda avanzada con AND para capturar todas las variantes que dieron 69 resultados
    afiliacion = 'centro AND investigaciones AND psicologia AND psicopedagogia'
    pubs = buscar_publicaciones_elsevier(afiliacion, count=100)
    print(f"Encontré {len(pubs)} publicaciones en Elsevier/Scopus para afiliación:")
    for p in pubs[:5]:
        print(f"- EID {p['EID']}: {p['Title']} ({p['Year']}) en {p['Journal']}")

    # Guardar CSV
    with open('publicaciones_elsevier.csv','w', newline='', encoding='utf-8') as f:
        fieldnames = ['EID','DOI','Title','Authors','Year','Journal','ISSN','Quartile']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in pubs:
            writer.writerow({
                'EID': p['EID'],
                'DOI': p['DOI'],
                'Title': p['Title'],
                'Authors': '; '.join(p['Authors']),
                'Year': p['Year'],
                'Journal': p['Journal'],
                'ISSN': p['ISSN'],
                'Quartile': p['Quartile']
            })
    print('CSV guardado: publicaciones_elsevier.csv')


if __name__ == '__main__':
    main()
