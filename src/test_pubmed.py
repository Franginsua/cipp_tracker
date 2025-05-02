# src/test_pubmed.py

import json
from pubmed_client import buscar_por_pmid

def main():
    # PMID de ejemplo (puedes cambiarla por otra que te interese)
    pmid = "31452104"
    resultado = buscar_por_pmid(pmid)
    # Imprimimos el JSON de forma legible
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
