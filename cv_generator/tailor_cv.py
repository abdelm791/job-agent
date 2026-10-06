"""
Génère un CV PDF adapté à une offre, en suivant EXACTEMENT la maquette de
référence fournie par l'utilisateur :

  [Titre du poste] ([rythme alternance])
  NOM PRÉNOM
  Tél | Email | LinkedIn | GitHub

  PROFIL
  <paragraphe d'accroche adapté à l'offre>

  COMPÉTENCES TECHNIQUES
  • Catégorie : description

  EXPÉRIENCE PROFESSIONNELLE
  Titre du poste
  Entreprise | Dates | Lieu
  • bullet (méthode XYZ)
  (répété pour chaque expérience, ordre antéchronologique)

  FORMATION / CERTIFICATIONS / LANGUES

Règles de contenu :
- Accords masculins uniquement, jamais de "(e)"
- Profil rédigé à la 1ère personne ("je")
- Le LLM reformule/priorise mais n'invente jamais de compétence ou de fait :
  il choisit parmi competences_pool et experiences[]["faits"] uniquement.
- Bullets d'expérience au format XYZ (Google/Laszlo Bock) :
  "[Résultat] mesuré par [preuve], en [méthode]" — jamais de chiffre inventé.
- Nom de fichier : n'inclut le nom de l'entreprise QUE si elle est connue.
"""
import sys
import os
import re
import json
import unicodedata
import ollama
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (PROFILE, OLLAMA_HOST, OLLAMA_LLM_MODEL, CV_OUTPUT_DIR,
                     MAX_DESCRIPTION_CHARS_FOR_LLM, LLM_NUM_PREDICT_CV_CONTENT)

NAVY = HexColor("#1B2A4A")
BLUE = HexColor("#2E5AAC")
GREY = HexColor("#5A5A5A")

_client = ollama.Client(host=OLLAMA_HOST)

STYLES = getSampleStyleSheet()
STYLE_JOB_TITLE = ParagraphStyle("JobTitle", parent=STYLES["Normal"], fontSize=14.5,
                                   textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=2, leading=16.5)
STYLE_NAME = ParagraphStyle("Name", parent=STYLES["Normal"], fontSize=12,
                              textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=2)
STYLE_CONTACT = ParagraphStyle("Contact", parent=STYLES["Normal"], fontSize=8.5,
                                 textColor=GREY, spaceAfter=7)
STYLE_SECTION = ParagraphStyle("Section", parent=STYLES["Normal"], fontSize=11.5,
                                 textColor=NAVY, fontName="Helvetica-Bold",
                                 spaceBefore=5, spaceAfter=2)
STYLE_BODY = ParagraphStyle("Body", parent=STYLES["Normal"], fontSize=9.1,
                              textColor=HexColor("#222222"), alignment=TA_JUSTIFY,
                              leading=11.5, spaceAfter=3)
STYLE_BULLET = ParagraphStyle("Bullet", parent=STYLES["Normal"], fontSize=9.1,
                                textColor=HexColor("#222222"), leftIndent=10,
                                leading=11.5, spaceAfter=1.5)
STYLE_ENTRY_TITLE = ParagraphStyle("EntryTitle", parent=STYLES["Normal"], fontSize=10,
                                     fontName="Helvetica-Bold", textColor=NAVY, spaceAfter=0.5)
STYLE_ENTRY_META = ParagraphStyle("EntryMeta", parent=STYLES["Normal"], fontSize=8.7,
                                    textColor=BLUE, fontName="Helvetica-Oblique", spaceAfter=2)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def build_cv_filename(offer: dict, anonymize: bool = False) -> str:
    """N'inclut le nom de l'entreprise que si elle est réellement connue."""
    base = f"CV_{slugify(offer['title'])}"
    company = (offer.get("company") or "").strip()
    is_known = company and company.lower() not in (
        "n/a", "none", "non précisée", "entreprise non précisée", "non renseigné",
    )
    if company and is_known and not anonymize:
        base += f"_{slugify(company)}"
    return base + ".pdf"


def generate_adaptive_content(offer: dict) -> dict:
    """Demande au LLM de choisir/prioriser/reformuler, SANS inventer, à partir
    du pool réel de compétences et des faits réels de chaque expérience."""
    competences_pool_txt = "\n".join(
        f"- {cat} : {desc}" for cat, desc in PROFILE["competences_pool"].items()
    )
    experiences_txt = "\n\n".join(
        f"[{e['titre']} chez {e['entreprise']}]\n" +
        "\n".join(f"  - {f}" for f in e["faits"])
        for e in PROFILE["experiences"]
    )

    prompt = f"""Tu prépares le contenu d'un CV en français pour cette offre :
Titre : {offer['title']}
Description : {offer.get('description', '')[:MAX_DESCRIPTION_CHARS_FOR_LLM]}

RÈGLE ABSOLUE : tu ne dois RIEN inventer. Tu choisis, priorises et reformules
UNIQUEMENT parmi les compétences et faits réels ci-dessous. N'ajoute aucun
outil, résultat chiffré ou compétence qui n'y figure pas. N'invente JAMAIS
un chiffre qui n'est pas déjà présent dans les faits fournis.

RÈGLE DE RÉDACTION (profil) : le paragraphe "profil_accroche" doit être
écrit à la 1ère personne ("je"), avec des accords strictement masculins (le
candidat est un homme) — jamais de tournures neutres ou féminines.

RÈGLE DE RÉDACTION (bullets d'expérience) : rédige chaque bullet selon la
méthode XYZ (popularisée par Google/Laszlo Bock) :
  "[Résultat/accompli] mesuré par [preuve chiffrée], en [action/méthode/outil]"
Concrètement : mène avec le résultat obtenu, prouve-le avec une donnée
mesurable, termine par comment tu l'as fait (méthode, outil, compétence).
- Si le fait fourni contient DÉJÀ un chiffre (ex: "réduisant le temps de
  traitement de 30 %"), utilise ce chiffre tel quel comme preuve [Y].
- Si le fait ne contient AUCUN chiffre, NE JAMAIS EN INVENTER UN : utilise
  une preuve qualitative honnête à la place (portée, fréquence, complexité,
  évolution avant/après en mots).
- Un bullet reste toujours ancré dans un fait réel fourni ; XYZ change
  uniquement l'ORDRE et la CLARTÉ de la formulation, jamais le contenu.

POOL DE COMPÉTENCES RÉELLES (catégorie : description) :
{competences_pool_txt}

FAITS RÉELS PAR EXPÉRIENCE :
{experiences_txt}

Réponds UNIQUEMENT en JSON avec ce format exact :
{{
  "profil_accroche": "<3-4 phrases en français, à la 1ère personne ('je'), rédigées au masculin (candidat homme, jamais d'accords féminins ni de tournures neutres type '(e)'), présentant le candidat pour CETTE offre précise ; s'appuie uniquement sur les faits fournis>",
  "competences_choisies": [
    {{"categorie": "<une des catégories du pool, éventuellement reformulée légèrement>", "description": "<reformulation courte de la description du pool, adaptée à l'offre>"}}
  ],
  "experiences_bullets": {{
    "<Titre exact de l'expérience tel que fourni>": ["<bullet au format XYZ, 1 à 3 par expérience>"]
  }}
}}
Sélectionne 4 à 6 catégories de compétences (les plus pertinentes pour l'offre, dans cet ordre de priorité).
Pour experiences_bullets, garde toutes les expériences mais adapte le nombre de bullets selon leur pertinence (l'expérience la plus pertinente peut avoir jusqu'à 5 bullets au format XYZ, les moins pertinentes 1 seul bullet factuel)."""

    resp = _client.chat(
        model=OLLAMA_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.25, "num_predict": LLM_NUM_PREDICT_CV_CONTENT},
    )
    raw = re.sub(r"^```(?:json)?|```$", "", resp["message"]["content"].strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(match.group(0) if match else raw)


def build_cv_pdf(offer: dict, output_path: str = None, anonymize_filename: bool = False) -> str:
    content = generate_adaptive_content(offer)

    if output_path is None:
        output_path = os.path.join(CV_OUTPUT_DIR, build_cv_filename(offer, anonymize_filename))

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             topMargin=7 * mm, bottomMargin=6 * mm,
                             leftMargin=17 * mm, rightMargin=17 * mm)
    story = []

    # --- Header : titre (rythme) / NOM / contact ---
    story.append(Paragraph(f"{offer['title']} ({PROFILE['rythme_alternance']})", STYLE_JOB_TITLE))
    story.append(Paragraph(PROFILE["nom_affiche"], STYLE_NAME))
    c = PROFILE["contact"]
    story.append(Paragraph(
        f"Tél : {c['telephone']} | Email : {c['email']} | "
        f"LinkedIn : {c['linkedin']} | GitHub : {c['github']}", STYLE_CONTACT))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))

    # --- PROFIL ---
    story.append(Paragraph("PROFIL", STYLE_SECTION))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))
    story.append(Paragraph(content.get("profil_accroche", ""), STYLE_BODY))

    # --- COMPÉTENCES TECHNIQUES ---
    story.append(Paragraph("COMPÉTENCES TECHNIQUES", STYLE_SECTION))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))
    for comp in content.get("competences_choisies", []):
        story.append(Paragraph(
            f"• <b>{comp.get('categorie','')}</b> : {comp.get('description','')}", STYLE_BULLET))

    # --- EXPÉRIENCE PROFESSIONNELLE ---
    story.append(Paragraph("EXPÉRIENCE PROFESSIONNELLE", STYLE_SECTION))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))
    bullets_map = content.get("experiences_bullets", {})
    for exp in PROFILE["experiences"]:
        story.append(Paragraph(exp["titre"], STYLE_ENTRY_TITLE))
        story.append(Paragraph(f"{exp['entreprise']} | {exp['dates']} | {exp['lieu']}", STYLE_ENTRY_META))
        bullets = bullets_map.get(exp["titre"]) or exp["faits"][:2]
        for b in bullets:
            story.append(Paragraph(f"• {b}", STYLE_BULLET))
        story.append(Spacer(1, 1))

    # --- FORMATION ---
    story.append(Paragraph("FORMATION", STYLE_SECTION))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))
    for f in PROFILE["formations"]:
        story.append(Paragraph(f["titre"], STYLE_ENTRY_TITLE))
        meta = f["etablissement"] + (f" | {f['dates']}" if f["dates"] else "")
        story.append(Paragraph(meta, STYLE_ENTRY_META))
        for d in f["details"]:
            story.append(Paragraph(f"• {d}", STYLE_BULLET))
        story.append(Spacer(1, 1.5))

    # --- CERTIFICATIONS ---
    story.append(Paragraph("CERTIFICATIONS", STYLE_SECTION))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))
    for cert in PROFILE["certifications"]:
        story.append(Paragraph(f"• {cert}", STYLE_BULLET))

    # --- LANGUES ---
    story.append(Paragraph("LANGUES", STYLE_SECTION))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=2.5))
    story.append(Paragraph(PROFILE["langues_detail"], STYLE_BULLET))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    test_offer = {
        "title": "Alternant Data Engineer H/F",
        "company": "TestCorp",
        "description": "Recherche alternant maîtrisant Python, SQL, Spark, dbt, Airflow, PostgreSQL.",
    }
    path = build_cv_pdf(test_offer)
    print("CV généré :", path)
