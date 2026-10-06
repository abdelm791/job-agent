"""
Connecteur API Adzuna. Doc : https://developer.adzuna.com/docs/search

Inscription gratuite : https://developer.adzuna.com/signup
-> récupère app_id / app_key, mets-les dans les variables d'environnement
   ADZUNA_APP_ID / ADZUNA_APP_KEY
"""
import requests
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_COUNTRY, PROFILE,
                     FETCH_MAX_HOURS_OLD, ADZUNA_MAX_PAGES, ADZUNA_RESULTS_PER_PAGE)

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

# Délai entre deux appels pour éviter le throttling (Adzuna renvoie des 503
# "Fastly" quand les requêtes arrivent trop vite d'affilée)
REQUEST_DELAY_SECONDS = 1.2
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5


def _get_with_retry(url, params):
    """GET avec reprise automatique sur 503 (throttling/indisponibilité
    temporaire côté Adzuna), backoff progressif entre les tentatives."""
    resp = None
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code == 503:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                print(f"[adzuna] 503 (tentative {attempt}/{MAX_RETRIES}), "
                      f"nouvelle tentative dans {wait}s...")
                time.sleep(wait)
                continue
        return resp
    return resp


def fetch_offers(keywords=None, max_pages=None, results_per_page=None, max_hours_old=None):
    """max_hours_old : converti en jours pour l'API Adzuna (granularité
    minimale = 1 jour). Par défaut FETCH_MAX_HOURS_OLD (ex: 24h -> 1 jour)."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise RuntimeError(
            "ADZUNA_APP_ID / ADZUNA_APP_KEY manquants. "
            "Voir les instructions en tête de sources/adzuna.py"
        )
    keywords = keywords or PROFILE["titre_recherche"]
    max_pages = ADZUNA_MAX_PAGES if max_pages is None else max_pages
    results_per_page = ADZUNA_RESULTS_PER_PAGE if results_per_page is None else results_per_page
    max_hours_old = FETCH_MAX_HOURS_OLD if max_hours_old is None else max_hours_old
    max_days_old = max(1, round(max_hours_old / 24)) if max_hours_old else None
    all_offers = []

    for kw in keywords:
        # Adzuna n'a pas de filtre "type de contrat = alternance" dédié :
        # on ajoute donc le mot directement à la requête pour cette source.
        query = f"{kw} alternance"
        for page in range(1, max_pages + 1):
            url = BASE_URL.format(country=ADZUNA_COUNTRY, page=page)
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "what": query,
                "results_per_page": results_per_page,
                "content-type": "application/json",
                "sort_by": "date",
            }
            if max_days_old:
                params["max_days_old"] = max_days_old

            time.sleep(REQUEST_DELAY_SECONDS)  # laisse respirer l'API entre 2 appels
            resp = _get_with_retry(url, params)

            if resp.status_code != 200:
                print(f"[adzuna] Erreur {resp.status_code} pour '{query}' p{page} "
                      f"(abandon après {MAX_RETRIES} tentatives) : {resp.text[:150]}")
                break
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            for o in results:
                all_offers.append({
                    "id": f"adzuna_{o['id']}",
                    "source": "adzuna",
                    "title": o.get("title", ""),
                    "company": o.get("company", {}).get("display_name", "Entreprise non précisée"),
                    "location": o.get("location", {}).get("display_name", ""),
                    "url": o.get("redirect_url", ""),
                    "description": o.get("description", ""),
                    "start_date_raw": o.get("created", ""),
                    "raw": o,
                })
    return all_offers


if __name__ == "__main__":
    offers = fetch_offers()
    print(f"{len(offers)} offres récupérées depuis Adzuna")
    for o in offers[:3]:
        print("-", o["title"], "|", o["company"], "|", o["url"])
