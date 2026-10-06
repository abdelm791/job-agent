"""
Ajoute manuellement une offre trouvée sur HelloWork, LinkedIn (ou tout autre
site) en copiant-collant son contenu. Aucun scraping : c'est toi qui fournis
les infos, l'agent se charge du scoring + génération de CV, exactement comme
pour les offres automatiques de France Travail/Adzuna.

Usage interactif :
    python add_offer.py

Usage scripté :
    python add_offer.py --source linkedin \
        --title "Alternant Data Engineer H/F" \
        --company "Acme Corp" \
        --location "Paris" \
        --url "https://www.linkedin.com/jobs/view/123456" \
        --description-file /tmp/offre.txt
"""
import argparse
import hashlib
import sys

from db.models import init_db, upsert_offer, update_score, set_cv_path, set_letter_path, get_conn
from matching.embed import get_profile_embedding, score_offer_embedding
from matching.score import score_offer
from cv_generator.tailor_cv import build_cv_pdf
from cv_generator.tailor_letter import build_letter_pdf
from report.build_report import build_report
from filters import is_excluded_company
import config


def read_multiline(prompt: str) -> str:
    print(prompt)
    print("(colle le texte de l'offre, puis termine par une ligne contenant seulement FIN)")
    lines = []
    while True:
        line = input()
        if line.strip() == "FIN":
            break
        lines.append(line)
    return "\n".join(lines)


def make_offer_id(source: str, url: str) -> str:
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    return f"{source}_{h}"


def process_single_offer(offer: dict, with_letter: bool = False):
    """Passe l'offre par le même pipeline que les offres automatiques :
    embedding -> score LLM -> CV si pertinent -> rapport mis à jour.
    La lettre de motivation reste optionnelle (with_letter=True ou --with-letter)."""
    profile_emb = get_profile_embedding()
    text = f"{offer['title']} {offer.get('description', '')}"
    emb_score = score_offer_embedding(text, profile_emb)
    update_score(offer["id"], embed_score=emb_score, status="scored")
    print(f"Similarité sémantique : {emb_score:.2f}")

    result = score_offer(offer)
    update_score(
        offer["id"], llm_score=result["score"],
        llm_justification=result["justification"],
        date_conflict=int(result["date_conflict"]),
        status="scored",
    )
    print(f"Score LLM : {result['score']}/100")
    print(f"Justification : {result['justification']}")
    if result["date_conflict"]:
        print("⚠ Conflit de date de démarrage détecté")
    if result.get("competences_manquantes"):
        print(f"Compétences manquantes : {', '.join(result['competences_manquantes'])}")

    if result["score"] >= config.SCORE_THRESHOLD_FOR_CV:
        cv_path = build_cv_pdf(offer)
        set_cv_path(offer["id"], cv_path)
        print(f"\n✅ CV généré : {cv_path}")
    else:
        print(f"\nScore sous le seuil ({config.SCORE_THRESHOLD_FOR_CV}), pas de CV généré."
              f" Tu peux forcer avec --force-cv.")

    if with_letter:
        letter_path = build_letter_pdf(offer)
        set_letter_path(offer["id"], letter_path)
        print(f"✅ Lettre de motivation générée : {letter_path}")
    else:
        print("(Pas de lettre de motivation générée — relance avec --with-letter "
              "ou utilise generate_letter.py plus tard si besoin.)")

    report_path = build_report(min_score=0)
    print(f"Rapport mis à jour : file://{report_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["hellowork", "linkedin", "autre"])
    parser.add_argument("--title")
    parser.add_argument("--company")
    parser.add_argument("--location")
    parser.add_argument("--url")
    parser.add_argument("--description-file", help="Fichier texte contenant la description de l'offre")
    parser.add_argument("--force-cv", action="store_true", help="Générer le CV même sous le seuil")
    parser.add_argument("--with-letter", action="store_true",
                         help="Générer aussi la lettre de motivation (optionnel, désactivé par défaut)")
    args = parser.parse_args()

    init_db()

    source = args.source or input("Source (hellowork / linkedin / autre) : ").strip().lower()
    title = args.title or input("Titre du poste : ").strip()
    company = args.company or input("Entreprise : ").strip()
    location = args.location or input("Lieu : ").strip()
    url = args.url or input("URL de l'offre (pour le bouton Postuler) : ").strip()

    if is_excluded_company(company):
        confirm = input(f"⚠ '{company}' ressemble à un centre de formation connu. "
                         f"Continuer quand même ? (o/n) : ").strip().lower()
        if confirm != "o":
            print("Annulé.")
            return

    if args.description_file:
        with open(args.description_file, encoding="utf-8") as f:
            description = f.read()
    else:
        description = read_multiline("Description de l'offre :")

    offer = {
        "id": make_offer_id(source, url),
        "source": source,
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
        "start_date_raw": "",
        "raw": {},
    }

    is_new = upsert_offer(offer)
    if not is_new:
        print("Cette offre (même URL) est déjà en base — traitement quand même en cours.")
        conn = get_conn()
        conn.execute("UPDATE offers SET status='new' WHERE id=?", (offer["id"],))
        conn.commit()
        conn.close()

    if args.force_cv:
        config.SCORE_THRESHOLD_FOR_CV = 0

    process_single_offer(offer, with_letter=args.with_letter)


if __name__ == "__main__":
    sys.exit(main())
