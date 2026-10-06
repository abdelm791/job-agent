"""
Configuration centrale de l'agent de recherche d'emploi.
Modifie ce fichier pour ajuster ton profil, tes filtres et tes clés API.
"""
import os
from datetime import date

# ============================================================
# 1. PROFIL CANDIDAT — utilisé pour le matching et la génération de CV
# ============================================================
PROFILE = {
    "nom": "Abdelmounim Chajia",
    "nom_affiche": "ABDELMOUNIM CHAJIA",  # tel qu'affiché en majuscules dans le header du CV

    # Mots-clés larges (pas des intitulés de poste précis) : le type de
    # contrat "alternance" est renforcé à deux niveaux côté France Travail
    # (alternance=true + mot ajouté à la recherche + revérification du
    # résultat) ; côté Adzuna, "alternance" est simplement ajouté à la requête.
    "titre_recherche": [
        "IA",
        "intelligence artificielle",
        "dev",
        "développement",
        "data",
    ],

    "contact": {
        "telephone": "+212 706 821 359",
        "email": "dev.chajia@gmail.com",
        "linkedin": "linkedin.com/in/abdelmounim-chajia",
        "github": "github.com/abdelm791",
    },

    # Pool de compétences réelles, catégorisées. Le LLM choisit et priorise
    # les catégories pertinentes par offre mais n'invente jamais de contenu :
    # il reformule/sélectionne uniquement ce qui est listé ici.
    "competences_pool": {
        "Indicateurs & actions correctives": (
            "suivi d'indicateurs de performance, animation de réunions de suivi, "
            "mise en place de plans d'actions correctives"
        ),
        "Chiffres & données": (
            "SQL avancé (PostgreSQL, MySQL, Oracle), aisance avec les chiffres "
            "et les statistiques, création de rapports"
        ),
        "Communication & rédaction": (
            "rédaction de recommandations claires, communication de résultats "
            "à des interlocuteurs internes variés, excellentes qualités rédactionnelles"
        ),
        "IA générative (pratique)": (
            "évaluation de modèles d'IA générative, analyse comparative, "
            "détection d'anomalies, prompt engineering"
        ),
        "Développement": "Java, Spring Boot, PHP, JavaScript, TypeScript, Angular, Node.js, Docker, Kafka, Python",
        "Posture": (
            "organisation, autonomie, force de proposition, aisance relationnelle, "
            "Agile/Scrum (PSM I certifié)"
        ),
    },

    # Résumé court, utilisé par la lettre de motivation (matching, etc.)
    "resume_profil": (
        "Software Engineer AI chez G2i (évaluation de modèles génératifs, "
        "prompt engineering), ex Full Stack Java/PHP chez Tessi (4+ ans). "
        "Plus de 4 ans d'expérience en environnement industriel (Responsable "
        "Qualité, gestion de stock) avant reconversion vers le développement. "
        "Reconversion depuis un parcours ingénierie mécanique."
    ),
    "competences_cles": [  # gardé pour compatibilité avec le générateur de lettre
        "Java", "Spring Boot", "PHP", "Angular", "Node.js",
        "Docker", "Kafka", "Python", "PostgreSQL", "SQL avancé",
        "IA générative", "prompt engineering", "évaluation de modèles",
    ],

    # Expériences réelles, ordre antéchronologique. "faits" = éléments vrais
    # et fixes ; le LLM peut reformuler/prioriser mais jamais en inventer.
    "experiences": [
        {
            "titre": "Software Engineer AI – Évaluation de modèles d'IA générative",
            "entreprise": "G2i",
            "dates": "Avril 2026 – aujourd'hui",
            "lieu": "Remote – Maroc",
            "faits": [
                "Analyse comparative des sorties de plusieurs modèles d'IA générative : "
                "détection d'anomalies et évaluation de la qualité des résultats",
                "Prompt engineering et revue de code produit par des LLM",
                "Rédaction de recommandations structurées et vulgarisées pour présenter "
                "simplement des conclusions à partir de données complexes",
            ],
        },
        {
            "titre": "Développeur Full Stack Java/PHP",
            "entreprise": "Tessi",
            "dates": "Septembre 2022 – Avril 2026",
            "lieu": "Oujda, Maroc",
            "faits": [
                "Prise en charge en autonomie de lots fonctionnels complets, de l'analyse "
                "des besoins à la mise en production, sur des applications métier complexes",
                "Conception et intégration d'API REST documentées (Swagger/OpenAPI) pour "
                "la communication entre systèmes internes et externes",
                "Gestion de bases de données PostgreSQL et MySQL : modélisation, requêtes "
                "SQL optimisées, intégrité des données",
                "Rédaction de spécifications techniques et échanges réguliers avec les "
                "utilisateurs métier",
                "Optimisation du code, réduisant le temps de traitement de 30 %",
            ],
        },
        {
            "titre": "Développeur Full Stack Java/Angular – Marketplace B2C",
            "entreprise": "Xfantome",
            "dates": "Septembre 2021 – Janvier 2022",
            "lieu": "Casablanca, Maroc",
            "faits": [
                "Conception et développement d'une application complète : backend Spring "
                "Boot, frontend Angular, base de données MySQL",
            ],
        },
        {
            "titre": "Gestionnaire de Stock",
            "entreprise": "G3c",
            "dates": "Septembre 2018 – Septembre 2019",
            "lieu": "Casablanca, Maroc",
            "faits": [
                "Conception d'un système de gestion de stock et suivi des commandes à "
                "l'aide d'indicateurs de suivi, en environnement industriel",
            ],
        },
        {
            "titre": "Responsable Qualité",
            "entreprise": "Atlas Fabrication",
            "dates": "Avril 2018 – Septembre 2018",
            "lieu": "Casablanca, Maroc",
            "faits": [
                "Mise en place et suivi du Système de Management de la Qualité (SMQ) : "
                "contrôles qualité et traçabilité des données de production",
                "Présence terrain en atelier, documentation des processus et animation "
                "de réunions de suivi des plans d'actions",
            ],
        },
    ],

    # Formation, ordre antéchronologique
    "formations": [
        {
            "titre": "Mastère Intelligence Artificielle, Développement & Data (alternance)",
            "etablissement": "Ipssi, France",
            "dates": "Rentrée le 30 novembre 2026",
            "details": [
                "Cursus Bac+5 : algorithmique, science des données, machine learning, "
                "deep learning, développement logiciel",
            ],
        },
        {
            "titre": "Maîtrise en Génie Mécanique (Bac+4)",
            "etablissement": "Faculté des Sciences et Techniques, Béni Mellal, Maroc",
            "dates": "",
            "details": [
                "Formation scientifique et technique rigoureuse : analyse de données "
                "expérimentales, modélisation, méthode scientifique",
            ],
        },
        {
            "titre": "Formation Développement Full Stack",
            "etablissement": "SUPEMIR, Casablanca, Maroc",
            "dates": "",
            "details": ["Java J2EE, PHP/Laravel, .NET, architectures n-tiers, API REST"],
        },
        {
            "titre": "Formation Full Stack Java/J2EE – Angular",
            "etablissement": "MindTech, Casablanca, Maroc",
            "dates": "",
            "details": [
                "Java J2EE, Hibernate/JPA, Spring MVC, API REST, Angular, bases de "
                "données relationnelles",
            ],
        },
    ],
    "certifications": [
        "Professional Scrum Master I (PSM I) – Scrum.org",
        "Training Certificate in Secure Development – Cyber Defence (OWASP, sécurité applicative)",
    ],
    # NOTE : niveau d'anglais à confirmer (B1 vs C1 selon les sources) —
    # ajuste cette ligne une fois tranché.
    "langues_detail": (
        "Arabe : langue maternelle | Français : C1 – maîtrise professionnelle complète "
        "| Anglais : C1 – maîtrise professionnelle"
    ),
    "langues": ["Arabe (natif)", "Français (C1)", "Anglais (C1)"],
    "localisation": "Kasba Tadla, Maroc",
    "date_debut_disponible": date(2026, 11, 30),  # début du Mastère IA
    "rythme_alternance": "3 semaines entreprise / 1 semaine école",
    "sexe": "masculin",  # pour accords grammaticaux dans les CV/LM générés
}

# Mots-clés à exclure des offres (bruit fréquent)
EXCLUDE_KEYWORDS = ["stage", "CDI senior", "10 ans d'expérience", "confirmé senior"]

# Tolérance sur la date de début (en jours) avant de flaguer un conflit
DATE_CONFLICT_TOLERANCE_DAYS = 30

# ============================================================
# 5. EXCLUSION DES CENTRES DE FORMATION / ORGANISMES DE FORMATION (OFA)
# ============================================================
# Beaucoup d'offres "alternance" sont postées par des écoles/CFA qui
# recrutent en réalité pour VENDRE leur propre cursus (souvent payant),
# pas par l'entreprise employeuse réelle. Exclues automatiquement si le nom
# d'entreprise correspond (comparaison insensible à la casse/accents, simple
# présence de la chaîne). Liste à compléter librement au fil des découvertes.
EXCLUDE_COMPANIES = [
    "iscod", "epsi", "cesi", "studi", "3il", "3is", "digital campus",
    "ecema", "ipac", "idrac", "esup", "groupe igs", "igs-rh",
    "walter learning", "openclassrooms", "groupe alternance",
    "wis", "web@cademie", "webacademie", "wshop", "esgi", "ynov",
    "esaip", "skillandyou", "skill and you", "sup de vente", "sup de vinci",
    "efab", "ifag", "isefac", "ipag", "cnam", "greta", "ionis",
    "ionis education", "iim", "itic paris", "aftec", "esi business school",
    "ipi", "skema", "cyberecole", "ecole 42", "simplon", "3wacademy",
    "eskemi", "pigier", "ifocop", "afpa", "webforce3", "institut f2i",
    "mydigitalschool", "icademie", "efficom", "eduservices",
    "galileo global education", "man'agir", "ecole de formation",
    "campus digital", "adisci", "eductive", "ecole 2600", "sciences-u",
    "iseg", "formasup", "cci campus", "learn5", "efficience", "efficience rh",
    "myway", "elyfec", "eemi", "institut g4", "digital college",
    "ecole multimedia", "school of ia",
]

# Expressions dans les ~300 premiers caractères de la description qui
# trahissent une offre "recrutement pour notre propre formation" plutôt
# qu'une vraie offre d'alternance en entreprise
EXCLUDE_DESCRIPTION_PATTERNS = [
    "notre centre de formation", "notre organisme de formation",
    "en tant qu'organisme de formation", "intégrer notre formation",
    "en amont de votre formation", "financement de votre formation",
    "rejoignez notre école", "intégrer notre école", "rejoindre notre école",
    "en partenariat avec notre cfa",
    "recrutons pour le compte de nos entreprises partenaires",
]

# ============================================================
# 2. SOURCES D'OFFRES — clés API (définis-les en variables d'environnement)
# ============================================================
# France Travail (ex Pôle Emploi) — https://francetravail.io/inscription
# Crée une application "Offres d'emploi v2" pour obtenir client_id / client_secret
FRANCE_TRAVAIL_CLIENT_ID = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID", "")
FRANCE_TRAVAIL_CLIENT_SECRET = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET", "")

# Adzuna — https://developer.adzuna.com/ (inscription gratuite, quota généreux)
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = "fr"

# ============================================================
# 3. MOTEUR IA LOCAL (Ollama)
# ============================================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_LLM_MODEL = "qwen2.5:14b-instruct"   # génération / re-ranking / rédaction
OLLAMA_EMBED_MODEL = "nomic-embed-text"      # matching sémantique

# ============================================================
# PERFORMANCE — réglages pour accélérer le traitement
# ============================================================
# Nombre d'offres traitées EN PARALLÈLE à l'étape d'embedding (rapide,
# léger, la parallélisation apporte un vrai gain ici).
EMBED_WORKERS = 4

# Nombre d'offres scorées EN PARALLÈLE par le LLM local (étape lourde).
# Sur un seul GPU/CPU, au-delà de 2 le gain devient marginal voire négatif.
# Passe à 1 si tu observes des ralentissements, augmente si GPU puissant.
SCORE_WORKERS = 2

# Longueur max (en caractères) de la description d'offre envoyée au LLM.
MAX_DESCRIPTION_CHARS_FOR_LLM = 1200

# Limite le nombre de tokens générés par le LLM (scoring JSON court, CV plus long)
LLM_NUM_PREDICT_SCORE = 300
LLM_NUM_PREDICT_CV_CONTENT = 900

# Volume d'offres récupérées par mot-clé et par source.
FRANCE_TRAVAIL_MAX_RESULTS = 30
ADZUNA_MAX_PAGES = 1
ADZUNA_RESULTS_PER_PAGE = 20

# Seuil de similarité cosinus (0-1) au-dessus duquel une offre est envoyée
# au LLM pour scoring fin
EMBED_SIMILARITY_THRESHOLD = 0.55

# Score final (0-100, donné par le LLM) au-dessus duquel un CV est généré
SCORE_THRESHOLD_FOR_CV = 65

# Ne récupérer que les offres publiées dans les X dernières heures
FETCH_MAX_HOURS_OLD = 24

# Le rapport HTML ne montre que les offres récupérées dans cette fenêtre
REPORT_MAX_HOURS_OLD = 24

# Les offres en base depuis plus longtemps que ça sont supprimées
# automatiquement à chaque lancement de main.py (nettoyage silencieux).
DB_RETENTION_HOURS = 24

# ============================================================
# 4. CHEMINS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "offers.db")
CV_OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "cv_generes")
REPORT_OUTPUT_PATH = os.path.join(BASE_DIR, "assets", "rapport.html")

os.makedirs(CV_OUTPUT_DIR, exist_ok=True)
