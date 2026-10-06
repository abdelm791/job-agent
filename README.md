# Job Agent — recherche d'offres + génération de CV adaptés (100% local)

Agent qui tourne entièrement sur ta machine : il cherche des offres
d'alternance via des APIs officielles (France Travail, Adzuna), les évalue
avec un LLM local (Ollama — aucune donnée envoyée à un service tiers pour
l'analyse), génère un CV PDF adapté à chaque offre pertinente, et produit un
rapport HTML avec des liens directs pour postuler.

---

## 1. Installer Ollama et les modèles

```bash
# Installer Ollama : https://ollama.com/download
ollama serve &                       # lance le serveur local (laisse-le tourner)
ollama pull qwen2.5:14b-instruct     # modèle de scoring/rédaction (~9 Go)
ollama pull nomic-embed-text         # modèle d'embeddings (~270 Mo)
```

Si ta machine peine avec le modèle 14b (RAM/VRAM limitée), remplace dans
`config.py` → `OLLAMA_LLM_MODEL` par `"llama3.1:8b-instruct-q4_K_M"`.

Vérifie qu'Ollama tourne avec `ollama list` — tu dois voir les deux modèles.

## 2. Installer les dépendances Python

```bash
cd job-agent
python -m venv venv
```

Active le venv :
- **Windows PowerShell** : `venv\Scripts\Activate.ps1`
  (si erreur de politique d'exécution : `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)
- **Windows cmd** : `venv\Scripts\activate.bat`
- **Mac/Linux** : `source venv/bin/activate`

Puis installe les dépendances :
```bash
pip install -r requirements.txt
```

## 3. Obtenir les clés API (gratuites)

**France Travail** (officielle, recommandée)
1. https://francetravail.io/inscription
2. Créer une application → souscrire à l'API "Offres d'emploi v2"
3. Récupérer `client_id` et `client_secret` (validation possible sous 24-48h)

**Adzuna** (complète la couverture, inscription instantanée)
1. https://developer.adzuna.com/signup
2. Récupérer `app_id` et `app_key` dans le Dashboard

Définis les 4 variables d'environnement :

```bash
# Mac/Linux
export FRANCE_TRAVAIL_CLIENT_ID="..."
export FRANCE_TRAVAIL_CLIENT_SECRET="..."
export ADZUNA_APP_ID="..."
export ADZUNA_APP_KEY="..."
```

```powershell
# Windows PowerShell (une commande à la fois, puis rouvre le terminal)
setx FRANCE_TRAVAIL_CLIENT_ID "..."
setx FRANCE_TRAVAIL_CLIENT_SECRET "..."
setx ADZUNA_APP_ID "..."
setx ADZUNA_APP_KEY "..."
```

Vérifie avec `echo $env:ADZUNA_APP_ID` (PowerShell) ou `echo $ADZUNA_APP_ID`
(Mac/Linux) que la valeur s'affiche bien.

## 4. Personnaliser ton profil (déjà pré-rempli)

Ouvre `config.py`, section `PROFILE` : mots-clés de recherche, compétences,
expériences, formations, date de disponibilité (30/11/2026 par défaut) —
tout est déjà renseigné avec le profil d'Abdou, à ajuster si besoin.

## 5. Lancer

```bash
python main.py
```

Ce que fait ce cycle, dans l'ordre :

1. **Récupération** — interroge France Travail (filtre officiel
   `alternance=true` + mot-clé renforcé + revérification) et Adzuna (mot-clé
   "alternance" ajouté), uniquement les offres des **dernières 24h**
2. **Exclusion automatique** des offres postées par des centres de formation
   (ISCOD, EPSI, CESI, etc. — liste dans `config.py` → `EXCLUDE_COMPANIES`)
3. **Filtre rapide** par similarité sémantique (embeddings locaux, **en
   parallèle** — 4 offres à la fois par défaut)
4. **Scoring fin** par le LLM local (**en parallèle**, 2 à la fois) : score
   0-100, justification, détection de conflit de date de démarrage
5. **Génération automatique du CV** (méthode XYZ pour les bullets
   d'expérience) pour chaque offre au-dessus de 65/100
6. **Rapport HTML** (`assets/rapport.html`) — cartes avec score, bouton
   "Postuler" vers l'URL exacte, lien vers le CV généré

Ouvre `assets/rapport.html` dans ton navigateur une fois terminé.

## Pause et reprise

**Ctrl+C à tout moment** — tout ce qui a été scoré reste sauvegardé en base.
Relance `python main.py --skip-fetch` pour reprendre exactement où tu t'es
arrêté (pas besoin de rappeler les APIs).

**Par petits lots**, si tu préfères garder le contrôle :
```bash
python main.py --limit 5
```
Traite 5 offres puis s'arrête proprement ; relance pour continuer.

## Performance

Réglages dans `config.py` (section PERFORMANCE) si le traitement te semble
lent :

```python
EMBED_WORKERS = 4      # offres traitées en parallèle à l'étape embedding
SCORE_WORKERS = 2      # offres scorées en parallèle par le LLM (baisse à 1
                        # si ça ralentit, monte si tu as un bon GPU)
MAX_DESCRIPTION_CHARS_FOR_LLM = 1200   # texte envoyé au LLM par offre
```

## Ajout manuel — HelloWork / LinkedIn

Ni l'un ni l'autre n'a d'API publique ; pas de scraping (ToS + risque de
ban). À la place, ajout manuel qui passe par le même pipeline complet :

```bash
python add_offer.py
```
Renseigne source / titre / entreprise / lieu / URL, colle la description,
termine par une ligne `FIN`. Score, CV, et rapport mis à jour automatiquement.
Ajoute `--with-letter` pour générer aussi la lettre de motivation.

## Lettre de motivation — à la demande uniquement

Contrairement au CV (automatique), la lettre ne se génère jamais toute seule :

```bash
python generate_letter.py
```
Liste les offres déjà scorées, choisis un numéro. Le rapport HTML affiche
ensuite un bouton "Voir la LM" pour cette offre.

## Nettoyage automatique

À chaque lancement, les offres en base depuis plus de 24h sont supprimées
(`DB_RETENTION_HOURS` dans `config.py`) et le rapport ne montre que les
dernières 24h (`REPORT_MAX_HOURS_OLD`). Désactive ponctuellement avec
`--no-cleanup` si tu veux garder l'historique pour un lancement.

## Automatiser (optionnel)

**Linux/Mac (cron)** :
```bash
crontab -e
# ajouter :
0 9 * * * cd /chemin/vers/job-agent && ./venv/bin/python main.py >> logs.txt 2>&1
```

**Windows** : Planificateur de tâches → nouvelle tâche → déclencheur
quotidien → action `python main.py` dans le dossier `job-agent` (avec le
venv activé, ou en appelant directement `venv\Scripts\python.exe main.py`).

## Notes importantes

- **Pas de scraping LinkedIn/Indeed/HelloWork** : viole leurs CGU, risque de
  ban IP. Seules des APIs officielles sont utilisées pour l'automatique.
- Le contenu généré par le LLM (CV et lettres) **doit être relu** avant tout
  envoi — le modèle reformule/priorise mais peut mal interpréter le contexte.
- Le LLM ne peut **jamais inventer** une compétence, un fait ou un chiffre
  absent de `config.py` → `PROFILE` : il choisit et reformule uniquement ce
  qui y est écrit.
- Relancer `python main.py` ne retraite jamais une offre déjà vue (par URL) —
  dédoublonnage automatique en base.

## Structure

```
job-agent/
├── config.py              # profil, clés API, seuils, réglages performance
├── main.py                # orchestrateur (point d'entrée)
├── add_offer.py           # ajout manuel HelloWork/LinkedIn
├── generate_letter.py     # génération lettre à la demande
├── filters.py             # exclusion centres de formation
├── requirements.txt
├── sources/
│   ├── france_travail.py  # API officielle + filtre alternance renforcé
│   └── adzuna.py          # API officielle + retry anti-throttling
├── matching/
│   ├── embed.py           # filtre rapide par similarité sémantique
│   └── score.py           # scoring fin + justification par LLM local
├── cv_generator/
│   ├── tailor_cv.py       # génération CV (maquette exacte, méthode XYZ)
│   └── tailor_letter.py   # génération lettre de motivation
├── db/
│   └── models.py          # SQLite (offres, scores, statut candidature)
├── report/
│   └── build_report.py    # tableau de bord HTML final
└── assets/
    ├── cv_generes/         # CV et lettres PDF générés
    └── rapport.html        # rapport final (généré à chaque lancement)
```
