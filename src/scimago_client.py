# src/scimago_client.py

import csv
import re


def normalize_issn(issn: str) -> str:
    """
    Normaliza un ISSN eliminando cualquier carácter que no sea dígito o 'X'.
    Ejemplo: '1663-4365' -> '16634365'
    """
    return re.sub(r"[^0-9Xx]", "", issn or "").upper()


def load_scimago_csv(path: str = "scimagojr.csv") -> dict:
    """
    Carga el CSV de SCImago Journal & Country Rank y devuelve un mapeo
    de ISSN normalizado a Quartile.

    Detecta automáticamente las columnas que contienen 'issn' y 'quartile' en el encabezado.
    Soporta delimitadores ';' o ','.
    """
    mapping = {}
    with open(path, encoding='utf-8') as f:
        # Detectar delimitador
        sample = f.read(1024)
        f.seek(0)
        delimiter = ';' if ';' in sample.splitlines()[0] else ','
        reader = csv.DictReader(f, delimiter=delimiter)
        # Detectar columnas de ISSN y Quartile
        fieldnames = reader.fieldnames or []
        issn_cols = [h for h in fieldnames if 'issn' in h.lower()]
        quart_cols = [h for h in fieldnames if 'quartile' in h.lower()]
        if not issn_cols or not quart_cols:
            raise ValueError(f"No se encontraron columnas ISSN o Quartile en {fieldnames}")
        quart_col = quart_cols[0]

        for row in reader:
            quartile = row.get(quart_col, '').strip()
            if not quartile:
                continue
            # Recorrer todas las columnas de ISSN
            for col in issn_cols:
                raw = row.get(col, '')
                if not raw:
                    continue
                # Puede haber múltiples ISSNs separados por ',' o ';'
                for single in re.split(r"[;,]", raw):
                    norm_key = normalize_issn(single.strip())
                    if norm_key:
                        mapping[norm_key] = quartile
    return mapping


def get_quartile_by_issn(issn: str, mapping: dict) -> str:
    """
    Devuelve el cuartil correspondiente al ISSN dado (normalizado) según el mapeo.
    Si no se encuentra, retorna 'N/A'.
    """
    norm_key = normalize_issn(issn)
    return mapping.get(norm_key, 'N/A')
