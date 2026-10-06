"""
Connecteur API France Travail (ex Pôle Emploi) - "Offres d'emploi v2".
Doc : https://francetravail.io/produits-partages/catalogue/offres-emploi

Inscription :
1. https://francetravail.io/inscription
2. Créer une application, souscrire à l'API "Offres d'emploi v2"
3. Récupérer client_id / client_secret -> variables d'environnement
   FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET
"""
import requests
import sys
import os
import time
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (FRANCE_TRAVAIL_CLIENT_ID, FRANCE_TRAVAIL_CLIENT_SECRET, PROFILE,
                     FETCH_MAX_HOURS_OLD, FRANCE_TRAVAIL_MAX_RESULTS)

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

REQUEST_DELAY_SECONDS = 0.8
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 4

# Termes qui doivent apparaître dans l'offre pour confirmer qu'il s'agit
# bien d'une alternance — filtre de sécurité en plus de alternance=true,
# qui s'avère pas toujours fiable côté France Travail.
ALTERNANCE_TERMS = ["alternance", "alternant", "apprenti", "apprentissage", "apprenticeship"]


def _is_alternance(offer_title: str, offer_desc: str) -> bool:
    text = f"{offer_title} {offer_desc[:300]}".lower()
    return any(term in text for term in ALTERNANCE_TERMS)


def _get_with_retry(headers, params):
    """GET avec reprise automatique sur erreur réseau (connexion réinitialisée,
    timeout...) — n'insiste PAS sur les erreurs 4xx (paramètres invalides),
    qui ne se résoudront pas en réessayant."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return requests.get(SEARCH_URL, headers=headers, params=params, timeout=20)
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                print(f"[france_travail] Erreur réseau (tentative {attempt}/{MAX_RETRIES}), "
                      f"nouvelle tentative dans {wait}s...")
                time.sleep(wait)
    raise last_exc


def _get_token():
    if not FRANCE_TRAVAIL_CLIENT_ID or not FRANCE_TRAVAIL_CLIENT_SECRET:
        raise RuntimeError(
            "FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET manquants. "
            "Voir les instructions en tête de sources/france_travail.py"
        )
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": FRANCE_TRAVAIL_CLIENT_ID,
            "client_secret": FRANCE_TRAVAIL_CLIENT_SECRET,
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_offers(keywords=None, max_results=None, max_hours_old=None):
    """Retourne une liste d'offres normalisées pour la base de données.
    max_hours_old : ne récupère que les offres publiées/actualisées dans
    cette fenêtre (par défaut FETCH_MAX_HOURS_OLD, ex: 24h)."""
    keywords = keywords or PROFILE["titre_recherche"]
    max_results = FRANCE_TRAVAIL_MAX_RESULTS if max_results is None else max_results
    max_hours_old = FETCH_MAX_HOURS_OLD if max_hours_old is None else max_hours_old
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"}

    min_creation_date = None
    max_creation_date = None
    if max_hours_old:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_hours_old)
        min_creation_date = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        max_creation_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_offers = []
    for kw in keywords:
        params = {
            "motsCles": f"{kw} alternance",  # renforce la recherche elle-même
            "range": f"0-{min(max_results, 149)}",
            "sort": "1",  # tri par date décroissante
            "alternance": "true",  # filtre officiel : contrats d'alternance uniquement
        }
        if min_creation_date:
            params["minCreationDate"] = min_creation_date
            params["maxCreationDate"] = max_creation_date

        time.sleep(REQUEST_DELAY_SECONDS)  # laisse respirer l'API entre 2 appels
        try:
            resp = _get_with_retry(headers, params)
        except requests.exceptions.RequestException as e:
            print(f"[france_travail] Échec réseau persistant pour '{kw}', abandon : {e}")
            continue

        if resp.status_code not in (200, 206):
            print(f"[france_travail] Erreur {resp.status_code} pour '{kw}': {resp.text[:200]}")
            continue
        data = resp.json()
        for o in data.get("resultats", []):
            title = o.get("intitule", "")
            description = o.get("description", "")
            if not _is_alternance(title, description):
                continue  # filet de sécurité : écarte ce qui n'est visiblement pas de l'alternance
            all_offers.append({
                "id": f"ft_{o['id']}",
                "source": "france_travail",
                "title": title,
                "company": o.get("entreprise", {}).get("nom", "Entreprise non précisée"),
                "location": o.get("lieuTravail", {}).get("libelle", ""),
                "url": f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
                "description": description,
                "start_date_raw": o.get("dateActualisation", ""),
                "raw": o,
            })
    return all_offers


if __name__ == "__main__":
    offers = fetch_offers()
    print(f"{len(offers)} offres récupérées depuis France Travail")
    for o in offers[:3]:
        print("-", o["title"], "|", o["company"], "|", o["url"])
