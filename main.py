"""
Orchestrateur principal de l'agent.

Usage :
    python main.py                    # cycle complet
    python main.py --skip-fetch       # ne pas rappeler les APIs, traiter la base existante
    python main.py --limit 5          # ne scorer/générer les CV que pour 5 offres, puis s'arrêter
    python main.py --min-score 70     # seuil de score pour le rapport final
    python main.py --no-cleanup       # ne pas supprimer les vieilles offres ce lancement

PAUSE :
    Tu peux interrompre à tout moment avec Ctrl+C — l'offre en cours de
    traitement sera juste perdue (quelques secondes), mais TOUT ce qui a été
    scoré avant reste sauvegardé en base. Relance simplement `python main.py`
    (ou `--skip-fetch` pour ne pas rappeler les APIs inutilement) : les
    offres non terminées reprennent automatiquement là où ça s'est arrêté.

PERFORMANCE :
    L'embedding et le scoring LLM sont parallélisés (EMBED_WORKERS /
    SCORE_WORKERS dans config.py). La génération de CV reste séquentielle
    (étape la plus lourde). Ajuste ces réglages selon ta machine.

Prérequis avant lancement (voir README.md) :
    - Ollama installé et lancé (`ollama serve`)
    - Modèles tirés : `ollama pull qwen2.5:14b-instruct` et `ollama pull nomic-embed-text`
    - Clés API définies (variables d'environnement ou fichier .env)
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from db.models import (init_db, upsert_offer, get_new_offers,
                        get_offers_pending_llm_score, update_score, set_cv_path,
                        delete_offers_older_than)
from matching.embed import get_profile_embedding, score_offer_embedding
from matching.score import score_offer
from cv_generator.tailor_cv import build_cv_pdf
from report.build_report import build_report
from filters import filter_offers
from config import (EMBED_SIMILARITY_THRESHOLD, SCORE_THRESHOLD_FOR_CV,
                     DB_RETENTION_HOURS, EMBED_WORKERS, SCORE_WORKERS)


def fetch_all_sources():
    total_new = 0
    total_excluded = 0
    try:
        from sources import france_travail
        offers = france_travail.fetch_offers()
        offers, excluded = filter_offers(offers)
        total_excluded += len(excluded)
        total_new += sum(upsert_offer(o) for o in offers)
        print(f"[fetch] France Travail : {len(offers)} récupérées"
              + (f" ({len(excluded)} centres de formation exclus)" if excluded else ""))
    except Exception as e:
        print(f"[fetch] France Travail indisponible : {e}")

    try:
        from sources import adzuna
        offers = adzuna.fetch_offers()
        offers, excluded = filter_offers(offers)
        total_excluded += len(excluded)
        total_new += sum(upsert_offer(o) for o in offers)
        print(f"[fetch] Adzuna : {len(offers)} récupérées"
              + (f" ({len(excluded)} centres de formation exclus)" if excluded else ""))
    except Exception as e:
        print(f"[fetch] Adzuna indisponible : {e}")

    print(f"[fetch] {total_new} nouvelles offres ajoutées en base"
          + (f", {total_excluded} exclues (centres de formation)" if total_excluded else ""))


def embed_and_filter_new_offers():
    """Étape rapide : calcule l'embedding de chaque offre 'new' EN PARALLÈLE
    (EMBED_WORKERS threads) et la classe en 'ignored' (hors sujet) ou
    'embedded' (prête pour le scoring LLM). Chaque offre est commitée
    individuellement dès son résultat reçu, donc un Ctrl+C ici ne perd que
    les calculs strictement en cours."""
    offers = get_new_offers()
    if not offers:
        return
    print(f"[filtre] {len(offers)} nouvelles offres à évaluer par similarité "
          f"({EMBED_WORKERS} en parallèle)")
    profile_emb = get_profile_embedding()

    def _process(o):
        text = f"{o['title']} {o.get('description','')}"
        emb_score = score_offer_embedding(text, profile_emb)
        return o["id"], emb_score

    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as pool:
        futures = {pool.submit(_process, o): o for o in offers}
        for future in as_completed(futures):
            try:
                offer_id, emb_score = future.result()
            except Exception as e:
                o = futures[future]
                print(f"      Erreur embedding pour '{o['title'][:40]}' : {e}")
                continue
            status = "embedded" if emb_score >= EMBED_SIMILARITY_THRESHOLD else "ignored"
            update_score(offer_id, embed_score=emb_score, status=status)
    print("[filtre] terminé")


def score_and_generate(limit: int = None):
    """Étape longue : scoring LLM EN PARALLÈLE (SCORE_WORKERS threads) pour
    les offres 'embedded' qui n'ont pas encore de llm_score, puis génération
    de CV en séquentiel (étape la plus lourde, pour ne pas saturer la
    machine). Reprend automatiquement les offres laissées en plan par une
    interruption précédente."""
    offers = get_offers_pending_llm_score()
    if not offers:
        print("[score] Aucune offre en attente de scoring")
        return

    if limit:
        offers = offers[:limit]
        print(f"[score] {len(offers)} offres à traiter ce lot "
              f"(--limit {limit}, {SCORE_WORKERS} en parallèle)")
    else:
        print(f"[score] {len(offers)} offres à traiter ({SCORE_WORKERS} en parallèle)")

    def _score(o):
        return o, score_offer(o)

    scored_results = []
    with ThreadPoolExecutor(max_workers=SCORE_WORKERS) as pool:
        futures = {pool.submit(_score, o): o for o in offers}
        done_count = 0
        for future in as_completed(futures):
            o = futures[future]
            done_count += 1
            try:
                offer, result = future.result()
            except Exception as e:
                print(f"  [{done_count}/{len(offers)}] Erreur scoring LLM "
                      f"pour '{o['title'][:40]}' : {e}")
                continue

            update_score(
                offer["id"], llm_score=result["score"],
                llm_justification=result["justification"],
                date_conflict=int(result["date_conflict"]),
                status="scored",
            )
            print(f"  [{done_count}/{len(offers)}] {offer['title'][:50]:50s} "
                  f"score={result['score']}/100"
                  f"{' ⚠ conflit date' if result['date_conflict'] else ''}")

            if result["score"] >= SCORE_THRESHOLD_FOR_CV:
                scored_results.append(offer)

    # Génération des CV en séquentiel : étape la plus lourde, on évite de
    # lancer plusieurs générations complètes en même temps sur la même machine.
    if scored_results:
        print(f"[cv] Génération de {len(scored_results)} CV...")
    for offer in scored_results:
        try:
            cv_path = build_cv_pdf(offer)
            set_cv_path(offer["id"], cv_path)
            print(f"      -> CV généré : {cv_path}")
        except Exception as e:
            print(f"      -> Erreur génération CV pour '{offer['title'][:40]}' : {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-fetch", action="store_true",
                         help="Ne pas re-fetch les APIs, traiter seulement la base existante")
    parser.add_argument("--limit", type=int, default=None,
                         help="Traiter au maximum N offres (scoring+CV) ce lancement, puis s'arrêter")
    parser.add_argument("--min-score", type=int, default=50,
                         help="Score minimum pour apparaître dans le rapport final")
    parser.add_argument("--no-cleanup", action="store_true",
                         help="Ne pas supprimer les vieilles offres de la base ce lancement")
    args = parser.parse_args()

    init_db()

    if not args.no_cleanup and DB_RETENTION_HOURS:
        deleted = delete_offers_older_than(DB_RETENTION_HOURS)
        if deleted:
            print(f"[nettoyage] {deleted} offre(s) de plus de {DB_RETENTION_HOURS}h supprimée(s) de la base")

    try:
        if not args.skip_fetch:
            fetch_all_sources()

        embed_and_filter_new_offers()
        score_and_generate(limit=args.limit)

    except KeyboardInterrupt:
        print("\n\n⏸  Pause demandée (Ctrl+C). Tout ce qui a été scoré est déjà "
              "sauvegardé en base.")
        print("   Relance `python main.py --skip-fetch` pour reprendre exactement "
              "là où tu t'es arrêté.")
        report_path = build_report(min_score=args.min_score)
        print(f"   Rapport (partiel) mis à jour : file://{report_path}")
        sys.exit(0)

    report_path = build_report(min_score=args.min_score)
    print(f"\n✅ Rapport généré : {report_path}")
    print(f"   Ouvre-le dans un navigateur : file://{report_path}")


if __name__ == "__main__":
    sys.exit(main())
