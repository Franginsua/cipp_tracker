# --- Para correr el código usar:  
# python src\dedeupe_merge.py --elsevier "publicaciones_elsevier.csv" --pubmed "publicaciones_pubmed.csv" --out "merged_dedup.csv" --log "duplicates_log.csv" ---

from __future__ import annotations
import argparse
import pandas as pd
import re
import difflib
import sys
from typing import Optional

# --- Intentar usar librerías opcionales para mejores resultados ---
try:
    from unidecode import unidecode as _unidecode
except Exception:
    _unidecode = None

try:
    from rapidfuzz import fuzz as _rf_fuzz
except Exception:
    _rf_fuzz = None

# --- Normalización de texto / DOI ---
def remove_accents_basic(s: str) -> str:
    try:
        return s.encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def normalize_text(s: Optional[str]) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    if _unidecode:
        s = _unidecode(s)
    else:
        s = remove_accents_basic(s)
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return s.strip()

def normalize_doi(doi: Optional[str]) -> str:
    if doi is None or (isinstance(doi, float) and pd.isna(doi)):
        return ""
    d = str(doi).strip()
    d = d.lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.strip()

# --- Fuzzy matching ---
def token_set_ratio(a: str, b: str) -> float:
    if _rf_fuzz:
        return float(_rf_fuzz.token_set_ratio(a, b))
    a_tokens = set([t for t in a.split() if t])
    b_tokens = set([t for t in b.split() if t])
    if not a_tokens and not b_tokens:
        return 100.0
    if not a_tokens or not b_tokens:
        return 0.0
    common = a_tokens.intersection(b_tokens)
    token_ratio = 100.0 * (2 * len(common)) / (len(a_tokens) + len(b_tokens))
    seq_ratio = difflib.SequenceMatcher(None, a, b).ratio() * 100.0
    return max(token_ratio, seq_ratio)

# --- Column-matching helper ---
def find_column_like(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = list(df.columns)
    lower_map = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    for c in cols:
        lc = c.lower()
        for cand in candidates:
            if cand.lower() in lc:
                return c
    return None

# --- Construir DataFrame estandarizado a partir del CSV original ---
def build_standard_df(df: pd.DataFrame, mapping: dict, source_name: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)  # importante: usar index de df para evitar desalineos
    # source_orig como serie clara
    out["source_orig"] = pd.Series([source_name] * len(df), index=df.index)

    def get_col(name: Optional[str]):
        if name and name in df.columns:
            return df[name].astype(object)
        # devolvemos una Serie con mismo índice
        return pd.Series([""] * len(df), index=df.index)

    out["doi"] = get_col(mapping.get("doi"))
    out["pmid"] = get_col(mapping.get("pmid"))
    out["title"] = get_col(mapping.get("title"))
    out["authors"] = get_col(mapping.get("authors"))
    out["year"] = get_col(mapping.get("year"))
    out["journal"] = get_col(mapping.get("journal"))
    out["issn"] = get_col(mapping.get("issn"))
    out["quartile"] = get_col(mapping.get("quartile"))  # nuevo: toma la columna Quartile si existe
    # abstract y affiliation los seguimos trayendo (por si existen) pero no los pondremos en salida final
    out["abstract"] = get_col(mapping.get("abstract"))
    out["affiliation"] = get_col(mapping.get("affiliation"))

    # normalizaciones auxiliares
    out["doi_norm"] = out["doi"].apply(normalize_doi)
    out["pmid_norm"] = out["pmid"].fillna("").astype(str)
    out["title_norm"] = out["title"].apply(normalize_text)
    out["authors_key"] = out["authors"].apply(
        lambda s: (normalize_text(s).split(";")[0].split(",")[0].strip()) if s else ""
    )
    out["year_norm"] = out["year"].fillna("").astype(str).str.extract(r"(\d{4})", expand=False).fillna("")
    out["orig_index"] = df.index.astype(str)
    return out

# --- Score para elegir el "mejor" registro ---
def score_row(row: pd.Series) -> int:
    score = 0
    if row.get("doi_norm"):
        score += 50
    if row.get("pmid_norm"):
        score += 30
    if row.get("abstract") and str(row.get("abstract")).strip():
        score += 5
    authors = str(row.get("authors") or "")
    score += min(len(authors.split()), 10)
    if row.get("year_norm"):
        score += 2
    return score

# --- Función adicional: fusionar títulos casi idénticos aunque tengan DOI distinto ---
def merge_similar_titles_across_dois(df: pd.DataFrame, title_col="title_norm", authors_col="authors_key",
                                     doi_col="doi", orig_idx_col="orig_index",
                                     title_threshold: int = 98, author_threshold: int = 90):
    """
    Busca filas en df con títulos muy parecidos (>= title_threshold) y autores parecidos
    o mismo año — las fusiona dejando la 'mejor' según score_row y guardando los DOI
    alternativos en 'alt_dois'. Devuelve (df_new, extra_duplicates_list).
    """
    df = df.reset_index(drop=True)
    n = len(df)
    to_drop = set()
    extra_log = []

    # Asegurar columnas auxiliares
    if "alt_dois" not in df.columns:
        df["alt_dois"] = ""

    for i in range(n):
        if i in to_drop:
            continue
        for j in range(i + 1, n):
            if j in to_drop:
                continue
            tscore = token_set_ratio(str(df.at[i, title_col]), str(df.at[j, title_col]))
            ascore = token_set_ratio(str(df.at[i, authors_col]), str(df.at[j, authors_col])) if df.at[i, authors_col] and df.at[j, authors_col] else 0.0
            year_i = str(df.at[i, "year"]).strip() if "year" in df.columns else ""
            year_j = str(df.at[j, "year"]).strip() if "year" in df.columns else ""
            year_match = (year_i and year_j and year_i == year_j)
            if tscore >= title_threshold and (ascore >= author_threshold or year_match):
                # consider them same article
                # choose best representative by score
                group_idxs = [i, j]
                best_local = max(group_idxs, key=lambda k: score_row(df.loc[k]))
                other = j if best_local == i else i

                # store other doi into alt_dois of the best (if different and non-empty)
                best_doi = str(df.at[best_local, doi_col]) or ""
                other_doi = str(df.at[other, doi_col]) or ""
                alt = str(df.at[best_local, "alt_dois"]) or ""
                alt_set = set([x for x in alt.split(";") if x])
                if other_doi and other_doi != best_doi:
                    alt_set.add(other_doi)
                df.at[best_local, "alt_dois"] = ";".join(sorted(alt_set)) if alt_set else ""

                # merge sources (if present) — usar df.loc[...] para obtener la Series y .get()
                srcs = set()
                for s in str(df.loc[best_local].get("sources", "")).split(";"):
                    if s:
                        srcs.add(s)
                for s in str(df.loc[other].get("sources", "")).split(";"):
                    if s:
                        srcs.add(s)
                if srcs:
                    df.at[best_local, "sources"] = ";".join(sorted(srcs))

                # log the dropped one
                extra_log.append({
                    "kept_index": df.at[best_local, orig_idx_col],
                    "dropped_index": df.at[other, orig_idx_col],
                    "reason": "same_title_diff_doi",
                    "kept_title": df.at[best_local, "title"],
                    "dropped_title": df.at[other, "title"]
                })

                to_drop.add(other)

    if to_drop:
        df = df.drop(list(to_drop)).reset_index(drop=True)
    return df, extra_log


# --- Merge & dedupe ---
def merge_and_dedupe(elsevier_csv: str, pubmed_csv: str, output_csv: str = "merged_dedup.csv",
                     duplicates_log: str = "duplicates_log.csv", fuzzy_threshold: int = 92):
    # Leer CSVs (puedes cambiar dtype si querés preservar todo como str)
    e = pd.read_csv(elsevier_csv)
    p = pd.read_csv(pubmed_csv)

    candidates = {
        "doi": ["doi", "dc_identifier", "scopus_doi"],
        "pmid": ["pmid", "pubmed_id", "pubmed id"],
        "title": ["title", "titulo", "article_title", "document_title"],
        "authors": ["authors", "author", "author_names"],
        "year": ["year", "cover_date", "publication_year", "coverdate"],
        "journal": ["journal", "publication_name", "source", "journal_title"],
        "issn": ["issn"],
        "abstract": ["abstract", "description", "dc_description"],
        "affiliation": ["affiliation", "affiliations", "author_affiliations"],
        "quartile": ["quartile", "Quartile"]  # nuevo candidato
    }
    mapping_e = {k: find_column_like(e, v) for k, v in candidates.items()}
    mapping_p = {k: find_column_like(p, v) for k, v in candidates.items()}

    e_std = build_standard_df(e, mapping_e, "elsevier")
    p_std = build_standard_df(p, mapping_p, "pubmed")

    all_df = pd.concat([e_std, p_std], ignore_index=False, sort=False)  # mantenemos índices fuente
    # asegurar strings
    for col in ["doi_norm", "pmid_norm", "title_norm", "authors_key", "year_norm"]:
        if col in all_df.columns:
            all_df[col] = all_df[col].fillna("").astype(str)

    # 1) Dedupe por DOI exacto
    with_doi = all_df[all_df["doi_norm"] != ""].copy()
    without_doi = all_df[all_df["doi_norm"] == ""].copy()
    deduped_parts = []
    duplicates_records = []

    for doi, group in with_doi.groupby("doi_norm"):
        best_idx = max(group.index, key=lambda i: score_row(group.loc[i]))
        best = group.loc[best_idx].copy()
        sources = sorted(list(set(group["source_orig"].astype(str))))
        best["sources"] = ";".join(sources)
        deduped_parts.append(best)
        for i in group.index:
            if i != best_idx:
                duplicates_records.append({
                    "kept_index": best["orig_index"],
                    "dropped_index": group.loc[i]["orig_index"],
                    "reason": "same_doi",
                    "kept_title": best["title"],
                    "dropped_title": group.loc[i]["title"]
                })

    # 2) Dedupe por PMID en los sin DOI
    with_pmid = without_doi[without_doi["pmid_norm"] != ""].copy()
    without_pmid = without_doi[without_doi["pmid_norm"] == ""].copy()

    for pmid, group in with_pmid.groupby("pmid_norm"):
        best_idx = max(group.index, key=lambda i: score_row(group.loc[i]))
        best = group.loc[best_idx].copy()
        sources = sorted(list(set(group["source_orig"].astype(str))))
        best["sources"] = ";".join(sources)
        deduped_parts.append(best)
        for i in group.index:
            if i != best_idx:
                duplicates_records.append({
                    "kept_index": best["orig_index"],
                    "dropped_index": group.loc[i]["orig_index"],
                    "reason": "same_pmid",
                    "kept_title": best["title"],
                    "dropped_title": group.loc[i]["title"]
                })

    # 3) Fuzzy dedupe para el resto (sin DOI ni PMID)
    remaining = without_pmid.reset_index(drop=True).copy()
    used = set()
    clusters = []
    for i in range(len(remaining)):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        r1 = remaining.loc[i]
        t1 = r1["title_norm"]
        a1 = r1["authors_key"]
        y1 = r1["year_norm"]
        for j in range(i + 1, len(remaining)):
            if j in used:
                continue
            r2 = remaining.loc[j]
            t2 = r2["title_norm"]
            a2 = r2["authors_key"]
            y2 = r2["year_norm"]
            title_score = token_set_ratio(t1, t2)
            author_score = token_set_ratio(a1, a2) if a1 and a2 else 0.0
            year_match = (y1 and y2 and (y1 == y2 or abs(int(y1) - int(y2)) <= 1))
            if title_score >= fuzzy_threshold and (author_score >= 80 or year_match):
                cluster.append(j)
                used.add(j)
        clusters.append(cluster)

    for cluster in clusters:
        rows = remaining.loc[cluster]
        best_idx = max(rows.index, key=lambda i: score_row(rows.loc[i]))
        best = rows.loc[best_idx].copy()
        sources = sorted(list(set(rows["source_orig"].astype(str))))
        best["sources"] = ";".join(sources)
        deduped_parts.append(best)
        for i in rows.index:
            if i != best_idx:
                duplicates_records.append({
                    "kept_index": best["orig_index"],
                    "dropped_index": rows.loc[i]["orig_index"],
                    "reason": "fuzzy_match",
                    "kept_title": best["title"],
                    "dropped_title": rows.loc[i]["title"]
                })

    # 4) juntar resultados parciales en un DataFrame
    if deduped_parts:
        deduped_df = pd.DataFrame(deduped_parts).reset_index(drop=True)
    else:
        deduped_df = pd.DataFrame(columns=all_df.columns)

    # --- NUEVO: fusionar por título casi idéntico aunque existan DOIs distintos ---
    # thresholds ajustables (puedes cambiarlos desde aquí o parametrizarlos si querés)
    title_merge_threshold = 98   # umbral alto: sólo fusiones con títulos prácticamente idénticos
    author_merge_threshold = 90  # umbral autores (si aplica)
    deduped_df, extra_log = merge_similar_titles_across_dois(deduped_df,
                                                            title_col="title_norm",
                                                            authors_col="authors_key",
                                                            doi_col="doi",
                                                            orig_idx_col="orig_index",
                                                            title_threshold=title_merge_threshold,
                                                            author_threshold=author_merge_threshold)
    if extra_log:
        duplicates_records.extend(extra_log)

    # 5) preparar columnas finales y guardar
    final_cols = ["doi", "pmid", "title", "authors", "year", "journal", "issn", "quartile",
                  "sources", "source_orig", "orig_index", "alt_dois"]
    for c in final_cols:
        if c not in deduped_df.columns:
            deduped_df[c] = ""
    deduped_df = deduped_df[final_cols]

    deduped_df.to_csv(output_csv, index=False)
    pd.DataFrame(duplicates_records).to_csv(duplicates_log, index=False)

    print(f"Guardado merged dedup en: {output_csv} (rows: {len(deduped_df)})")
    print(f"Guardado log de duplicados en: {duplicates_log} (rows: {len(duplicates_records)})")

# --- CLI ---
def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge & dedupe Elsevier + PubMed CSVs")
    parser.add_argument("--elsevier", required=True, help="Ruta al CSV generado por Elsevier")
    parser.add_argument("--pubmed", required=True, help="Ruta al CSV generado por PubMed")
    parser.add_argument("--out", default="merged_dedup.csv", help="Ruta de salida para CSV unificado")
    parser.add_argument("--log", default="duplicates_log.csv", help="Ruta de salida para log de duplicados")
    parser.add_argument("--threshold", type=int, default=92, help="Umbral fuzzy token-set (0-100). Default 92")
    args = parser.parse_args(argv)

    merge_and_dedupe(args.elsevier, args.pubmed, args.out, args.log, args.threshold)

if __name__ == "__main__":
    main()
