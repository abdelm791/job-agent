"""
Calcule des embeddings locaux (via Ollama) et la similarité cosinus
entre le profil du candidat et chaque offre. Sert de premier filtre
rapide avant d'envoyer les offres prometteuses au LLM (plus coûteux en temps).
"""
import sys
import os
import numpy as np
import ollama

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OLLAMA_HOST, OLLAMA_EMBED_MODEL, PROFILE

_client = ollama.Client(host=OLLAMA_HOST)


def _profile_text():
    return (
        f"{PROFILE['resume_profil']} "
        f"Compétences : {', '.join(PROFILE['competences_cles'])}. "
        f"Recherche : {', '.join(PROFILE['titre_recherche'])}."
    )


def embed_text(text: str) -> np.ndarray:
    resp = _client.embeddings(model=OLLAMA_EMBED_MODEL, prompt=text[:4000])
    return np.array(resp["embedding"])


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def score_offer_embedding(offer_description: str, profile_embedding: np.ndarray = None) -> float:
    if profile_embedding is None:
        profile_embedding = embed_text(_profile_text())
    offer_embedding = embed_text(offer_description)
    return cosine_similarity(profile_embedding, offer_embedding)


def get_profile_embedding() -> np.ndarray:
    return embed_text(_profile_text())


if __name__ == "__main__":
    pe = get_profile_embedding()
    test = "Recherche alternant Data Engineer, stack Python/Spark/Airflow, Paris."
    print("Similarité test :", score_offer_embedding(test, pe))
