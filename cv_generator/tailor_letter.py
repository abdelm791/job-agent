"""
Génère une lettre de motivation PDF adaptée à une offre spécifique.
Contrairement au CV, ce n'est PAS automatique : appelée uniquement à la
demande (via generate_letter.py ou --with-letter dans add_offer.py).
"""
import sys
import os
import re
import json
from datetime import date
import ollama
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROFILE, OLLAMA_HOST, OLLAMA_LLM_MODEL, CV_OUTPUT_DIR
from cv_generator.tailor_cv import slugify

NAVY = HexColor("#1B2A4A")
GREY = HexColor("#5A5A5A")

_client = ollama.Client(host=OLLAMA_HOST)

STYLES = getSampleStyleSheet()
STYLE_NAME = ParagraphStyle("LName", parent=STYLES["Normal"], fontSize=13,
                              textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=2)
STYLE_CONTACT = ParagraphStyle("LContact", parent=STYLES["Normal"], fontSize=9,
                                 textColor=GREY, spaceAfter=14)
STYLE_DATE = ParagraphStyle("LDate", parent=STYLES["Normal"], fontSize=9.5,
                              textColor=GREY, alignment=TA_RIGHT, spaceAfter=16)
STYLE_OBJECT = ParagraphStyle("LObject", parent=STYLES["Normal"], fontSize=10.5,
                                textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=12)
STYLE_BODY = ParagraphStyle("LBody", parent=STYLES["Normal"], fontSize=10.5,
                              textColor=HexColor("#222222"), alignment=TA_JUSTIFY,
                              leading=15, spaceAfter=10)
STYLE_SIGN = ParagraphStyle("LSign", parent=STYLES["Normal"], fontSize=10.5,
                              textColor=NAVY, spaceBefore=20)

PROMPT_TEMPLATE = """Tu rédiges une lettre de motivation en français, sincère et sans emphase excessive,
pour un candidat HOMME (accords masculins uniquement, jamais de tournures neutres du type "motivé(e)").

PROFIL DU CANDIDAT (n'invente rien, reformule uniquement ce qui suit) :
{resume_profil}
Compétences : {competences}
Rythme d'alternance : {rythme} (à mentionner naturellement si l'offre est une alternance)
Disponible à partir du : {date_debut}

OFFRE :
Titre : {titre}
Entreprise : {entreprise}
Description : {description}

Écris UNIQUEMENT un JSON avec ces clés, sans texte autour :
{{
  "objet": "<une ligne, ex: Candidature au poste de X en alternance>",
  "paragraphe_accroche": "<2-3 phrases, pourquoi ce poste/cette entreprise>",
  "paragraphe_competences": "<3-4 phrases reliant le profil réel aux besoins de l'offre, honnête sur les points forts>",
  "paragraphe_motivation": "<2-3 phrases sur la motivation concrète, le rythme d'alternance, la disponibilité>",
  "formule_conclusion": "<1 phrase de clôture avant la formule de politesse>"
}}"""


def generate_letter_content(offer: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        resume_profil=PROFILE["resume_profil"],
        competences=", ".join(PROFILE["competences_cles"]),
        rythme=PROFILE["rythme_alternance"],
        date_debut=PROFILE["date_debut_disponible"],
        titre=offer["title"],
        entreprise=offer.get("company", "l'entreprise"),
        description=offer.get("description", "")[:2500],
    )
    resp = _client.chat(
        model=OLLAMA_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.4},
    )
    raw = re.sub(r"^```(?:json)?|```$", "", resp["message"]["content"].strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(match.group(0) if match else raw)


def build_letter_pdf(offer: dict, output_path: str = None, anonymize_filename: bool = False) -> str:
    content = generate_letter_content(offer)

    if output_path is None:
        fname = f"LM_{slugify(offer['title'])}.pdf" if anonymize_filename else \
                f"LM_{slugify(offer['title'])}_{slugify(offer.get('company',''))}.pdf"
        output_path = os.path.join(CV_OUTPUT_DIR, fname)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             topMargin=25 * mm, bottomMargin=20 * mm,
                             leftMargin=25 * mm, rightMargin=25 * mm)
    story = []

    story.append(Paragraph(PROFILE["nom"], STYLE_NAME))
    story.append(Paragraph(
        f"{PROFILE['localisation']} · {' / '.join(PROFILE['langues'])}", STYLE_CONTACT))

    story.append(Paragraph(
        f"{offer.get('company', '')}<br/>{offer.get('location', '')}", STYLE_CONTACT))
    story.append(Paragraph(date.today().strftime("Le %d/%m/%Y"), STYLE_DATE))

    story.append(Paragraph(content.get("objet", f"Candidature — {offer['title']}"), STYLE_OBJECT))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=14))

    story.append(Paragraph("Madame, Monsieur,", STYLE_BODY))
    for key in ["paragraphe_accroche", "paragraphe_competences",
                "paragraphe_motivation", "formule_conclusion"]:
        text = content.get(key, "")
        if text:
            story.append(Paragraph(text, STYLE_BODY))

    story.append(Paragraph(
        "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
        STYLE_BODY))
    story.append(Paragraph(PROFILE["nom"], STYLE_SIGN))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    test_offer = {
        "title": "Alternant Data Engineer H/F",
        "company": "TestCorp",
        "location": "Paris",
        "description": "Recherche alternant Python, Spark, dbt, Airflow.",
    }
    path = build_letter_pdf(test_offer)
    print("Lettre générée :", path)
