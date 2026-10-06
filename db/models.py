"""
Base SQLite légère : stocke les offres vues, leur score, le CV généré,
et le statut de candidature. Pas de dépendance externe (sqlite3 = stdlib).
"""
import sqlite3
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id TEXT PRIMARY KEY,           -- id unique (source + id source, ex "ft_123456")
    source TEXT NOT NULL,          -- "france_travail" | "adzuna" | "linkedin" | "hellowork" | ...
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    url TEXT NOT NULL,             -- lien direct vers l'offre / postuler
    description TEXT,
    start_date_raw TEXT,           -- date de début telle que trouvée dans l'annonce (texte brut)
    date_conflict INTEGER DEFAULT 0,  -- 1 si conflit détecté avec date_debut_disponible
    embed_score REAL,              -- similarité cosinus profil <-> offre
    llm_score INTEGER,             -- score 0-100 donné par le LLM local
    llm_justification TEXT,
    status TEXT DEFAULT 'new',     -- new | embedded | ignored | scored | cv_generated | applied | rejected
    cv_path TEXT,                  -- chemin du CV PDF généré pour cette offre
    letter_path TEXT,              -- chemin de la lettre de motivation PDF (générée à la demande)
    fetched_at TEXT DEFAULT (datetime('now')),
    raw_json TEXT                  -- payload brut de l'API, pour debug/re-traitement
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    # Migration douce : ajoute letter_path si la base existait déjà sans cette colonne
    cols = [r[1] for r in conn.execute("PRAGMA table_info(offers)").fetchall()]
    if "letter_path" not in cols:
        conn.execute("ALTER TABLE offers ADD COLUMN letter_path TEXT")
    conn.commit()
    conn.close()


def upsert_offer(offer: dict):
    """Insère une offre si elle n'existe pas déjà (par id). Ne écrase jamais
    un score déjà calculé lors d'un simple re-fetch. Le filtrage des centres
    de formation (EXCLUDE_COMPANIES) se fait en amont, dans filters.py,
    avant l'appel à cette fonction — pas ici."""
    conn = get_conn()
    existing = conn.execute("SELECT id FROM offers WHERE id = ?", (offer["id"],)).fetchone()
    if existing:
        conn.close()
        return False  # déjà connue, on ne retraite pas
    conn.execute(
        """INSERT INTO offers (id, source, title, company, location, url,
           description, start_date_raw, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            offer["id"], offer["source"], offer["title"], offer.get("company"),
            offer.get("location"), offer["url"], offer.get("description", ""),
            offer.get("start_date_raw", ""), json.dumps(offer.get("raw", {})),
        ),
    )
    conn.commit()
    conn.close()
    return True


def update_score(offer_id: str, embed_score: float = None, llm_score: int = None,
                  llm_justification: str = None, date_conflict: int = None, status: str = None):
    conn = get_conn()
    fields, values = [], []
    for col, val in [
        ("embed_score", embed_score), ("llm_score", llm_score),
        ("llm_justification", llm_justification), ("date_conflict", date_conflict),
        ("status", status),
    ]:
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    if not fields:
        return
    values.append(offer_id)
    conn.execute(f"UPDATE offers SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def set_cv_path(offer_id: str, cv_path: str):
    conn = get_conn()
    conn.execute("UPDATE offers SET cv_path = ?, status = 'cv_generated' WHERE id = ?",
                 (cv_path, offer_id))
    conn.commit()
    conn.close()


def set_letter_path(offer_id: str, letter_path: str):
    conn = get_conn()
    conn.execute("UPDATE offers SET letter_path = ? WHERE id = ?", (letter_path, offer_id))
    conn.commit()
    conn.close()


def get_offer_by_id(offer_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_offers_summary():
    """Liste légère (id, titre, entreprise, score) pour affichage de sélection."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, title, company, llm_score, cv_path, letter_path FROM offers "
        "WHERE llm_score IS NOT NULL ORDER BY llm_score DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_new_offers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM offers WHERE status = 'new'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_offers_pending_llm_score():
    """Offres dont l'embedding est fait mais qui n'ont pas encore de score LLM
    (utile pour reprendre après une interruption : rien n'est perdu)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM offers WHERE status = 'embedded' AND llm_score IS NULL"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_offers(min_score=0, limit=50, max_hours_old=None):
    """max_hours_old : si fourni, ne retourne que les offres récupérées dans
    cette fenêtre (ex: 24). Sans ça, retourne toutes les offres en base."""
    conn = get_conn()
    query = "SELECT * FROM offers WHERE llm_score >= ?"
    params = [min_score]
    if max_hours_old:
        query += " AND fetched_at >= datetime('now', ?)"
        params.append(f"-{max_hours_old} hours")
    query += " ORDER BY llm_score DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_offers_older_than(hours: int) -> int:
    """Supprime définitivement de la base les offres récupérées il y a plus
    de `hours` heures. Retourne le nombre de lignes supprimées."""
    conn = get_conn()
    cur = conn.execute("DELETE FROM offers WHERE fetched_at < datetime('now', ?)",
                        (f"-{hours} hours",))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted
