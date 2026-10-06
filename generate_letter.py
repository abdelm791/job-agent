"""
Génère une lettre de motivation pour une offre déjà en base — À LA DEMANDE
uniquement (pas d'automatisation, contrairement au CV qui se génère seul
au-dessus du seuil de score).

Usage :
    python generate_letter.py                 # liste les offres, choix interactif
    python generate_letter.py --offer-id ft_123456
    python generate_letter.py --offer-id ft_123456 --anonymize
"""
import argparse
import sys

from db.models import init_db, get_all_offers_summary, get_offer_by_id, set_letter_path
from cv_generator.tailor_letter import build_letter_pdf


def pick_offer_interactively():
    offers = get_all_offers_summary()
    if not offers:
        print("Aucune offre scorée en base. Lance d'abord main.py ou add_offer.py.")
        sys.exit(1)

    print("\nOffres disponibles :\n")
    for i, o in enumerate(offers, 1):
        letter_flag = " [LM déjà générée]" if o.get("letter_path") else ""
        print(f"  {i}. [{o['llm_score']:>3}/100] {o['title']} — {o.get('company') or 'N/A'}{letter_flag}")

    choice = input("\nNuméro de l'offre pour laquelle générer la lettre : ").strip()
    try:
        idx = int(choice) - 1
        return offers[idx]["id"]
    except (ValueError, IndexError):
        print("Choix invalide.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer-id", help="ID de l'offre (voir db/offers.db ou le rapport HTML)")
    parser.add_argument("--anonymize", action="store_true",
                         help="Ne pas inclure le nom de l'entreprise dans le nom du fichier")
    args = parser.parse_args()

    init_db()

    offer_id = args.offer_id or pick_offer_interactively()
    offer = get_offer_by_id(offer_id)
    if not offer:
        print(f"Offre '{offer_id}' introuvable en base.")
        sys.exit(1)

    print(f"\nGénération de la lettre pour : {offer['title']} — {offer.get('company')}")
    letter_path = build_letter_pdf(offer, anonymize_filename=args.anonymize)
    set_letter_path(offer_id, letter_path)
    print(f"✅ Lettre générée : {letter_path}")


if __name__ == "__main__":
    sys.exit(main())
