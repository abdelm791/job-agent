"""
Envoie chaque offre pré-filtrée (par similarité d'embedding) au LLM local
pour un scoring fin : compatibilité réelle du profil, compétences manquantes,
et détection de conflit avec la date de début disponible (30/11/2026).

Le LLM répond en JSON structuré, parsé directement.
"""
import sys
import os
import json
import re
import ollama

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (OLLAMA_HOST, OLLAMA_LLM_MODEL, PROFILE,
                     MAX_DESCRIPTION_CHARS_FOR_LLM, LLM_NUM_PREDICT_SCORE)

_client = ollama.Client(host=OLLAMA_HOST)

SYSTEM_PROMPT = """Tu es un assistant de recrutement rigoureux et honnête.
Tu évalues l'adéquation entre le profil d'un candidat et une offre d'emploi/alternance.
Tu dois être HONNÊTE sur les écarts de compétences, pas complaisant.
Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après, format exact :
{
  "score": <entier 0-100>,
  "justification": "<2-3 phrases en français expliquant le score, mentionnant les compétences qui matchent et celles qui manquent>",
  "date_conflict": <true ou false, true si l'offre demande un démarrage clairement incompatible avec le 30 novembre 2026>,
  "competences_manquantes": ["<liste des compétences demandées que le candidat n'a pas>"]
}"""


def score_offer(offer: dict) -> dict:
    user_prompt = f"""PROFIL CANDIDAT :
{PROFILE['resume_profil']}
Compétences : {', '.join(PROFILE['competences_cles'])}
Contrainte : disponible uniquement à partir du {PROFILE['date_debut_disponible']} (rythme {PROFILE['rythme_alternance']})

OFFRE :
Titre : {offer['title']}
Entreprise : {offer.get('company', 'N/A')}
Lieu : {offer.get('location', 'N/A')}
Description : {offer.get('description', '')[:MAX_DESCRIPTION_CHARS_FOR_LLM]}
Date/info de publication ou démarrage brute : {offer.get('start_date_raw', 'N/A')}

Évalue la compatibilité et réponds en JSON selon le format demandé."""

    resp = _client.chat(
        model=OLLAMA_LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.2, "num_predict": LLM_NUM_PREDICT_SCORE},
    )
    raw = resp["message"]["content"].strip()

    # Le LLM peut parfois entourer le JSON de ```json ... ``` malgré la consigne
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback : tente d'extraire le premier bloc {...}
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
        else:
            raise ValueError(f"Réponse LLM non parsable : {raw[:300]}")

    return {
        "score": int(parsed.get("score", 0)),
        "justification": parsed.get("justification", ""),
        "date_conflict": bool(parsed.get("date_conflict", False)),
        "competences_manquantes": parsed.get("competences_manquantes", []),
    }


if __name__ == "__main__":
    test_offer = {
        "title": "Alternant Data Engineer H/F",
        "company": "TestCorp",
        "location": "Paris",
        "description": "Recherche alternant maîtrisant Python, Spark, Airflow, dbt. Démarrage septembre 2026.",
        "start_date_raw": "Démarrage septembre 2026",
    }
    print(json.dumps(score_offer(test_offer), indent=2, ensure_ascii=False))
