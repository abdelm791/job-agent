"""
Détecte les offres postées par des centres de formation / organismes de
formation (OFA) plutôt que par l'entreprise employeuse réelle — fréquent
sur les offres "alternance" (ISCOD, EPSI, CESI, etc.), qui servent souvent
à vendre leur propre cursus plutôt qu'à représenter un poste réel.
"""
import sys
import os
import re
import unicodedata

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import EXCLUDE_COMPANIES, EXCLUDE_DESCRIPTION_PATTERNS


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def is_excluded_company(company: str) -> bool:
    """True si le nom d'entreprise correspond à un centre de formation connu
    (ISCOD, EPSI, etc.) qui republie des offres pour compte de tiers."""
    if not company:
        return False
    norm = _normalize(company)
    return any(_normalize(excl) in norm for excl in EXCLUDE_COMPANIES)


def is_training_org_description(description: str) -> bool:
    """True si le début de la description trahit une offre postée par un
    centre de formation (recrutement pour sa propre promo), même quand le
    nom d'entreprise en lui-même ne le laisse pas deviner."""
    if not description:
        return False
    norm = _normalize(description[:400])
    return any(_normalize(pat) in norm for pat in EXCLUDE_DESCRIPTION_PATTERNS)


def is_training_org_offer(offer: dict) -> bool:
    """Vérifie à la fois le nom d'entreprise et le début de la description."""
    return (is_excluded_company(offer.get("company", ""))
            or is_training_org_description(offer.get("description", "")))


def filter_offers(offers: list) -> tuple:
    """Sépare une liste d'offres en (gardées, exclues) selon le nom
    d'entreprise ET le contenu de la description."""
    kept, excluded = [], []
    for o in offers:
        if is_training_org_offer(o):
            excluded.append(o)
        else:
            kept.append(o)
    return kept, excluded
