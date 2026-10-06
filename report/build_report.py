"""
Construit un tableau de bord HTML simple listant les offres retenues,
triées par score, avec lien direct "Postuler" et lien vers le CV généré.
S'ouvre dans n'importe quel navigateur, aucune dépendance externe.
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REPORT_OUTPUT_PATH, REPORT_MAX_HOURS_OLD
from db.models import get_top_offers

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport candidatures - {date}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; background:#f4f6f9; margin:0; padding:30px; color:#1B2A4A; }}
  h1 {{ font-size: 22px; }}
  .card {{ background:#fff; border-radius:10px; padding:18px 22px; margin-bottom:14px;
           box-shadow:0 1px 4px rgba(0,0,0,0.08); border-left:5px solid #2E5AAC; }}
  .card.conflict {{ border-left-color:#c0392b; }}
  .title {{ font-size:16px; font-weight:600; margin:0 0 4px; }}
  .meta {{ color:#5A5A5A; font-size:13px; margin-bottom:8px; }}
  .score {{ display:inline-block; background:#1B2A4A; color:#fff; border-radius:6px;
            padding:2px 10px; font-size:13px; font-weight:600; margin-right:8px; }}
  .justif {{ font-size:13px; color:#333; margin:8px 0; }}
  .conflict-badge {{ background:#c0392b; color:#fff; border-radius:6px; padding:2px 10px; font-size:12px; }}
  .actions a {{ display:inline-block; margin-right:10px; padding:6px 14px; border-radius:6px;
                text-decoration:none; font-size:13px; font-weight:600; }}
  .apply {{ background:#2E5AAC; color:#fff; }}
  .cv {{ background:#EDEDED; color:#1B2A4A; }}
</style>
</head>
<body>
<h1>📋 Offres retenues — {date}</h1>
<p style="color:#5A5A5A">{count} offres au-dessus du seuil de pertinence.</p>
{cards}
</body>
</html>"""

CARD_TEMPLATE = """
<div class="card{conflict_class}">
  <div class="title">{title} — {company}</div>
  <div class="meta">{location} · source : {source}</div>
  <span class="score">Score : {score}/100</span>
  {conflict_badge}
  <div class="justif">{justification}</div>
  <div class="actions">
    <a class="apply" href="{url}" target="_blank">🔗 Postuler</a>
    {cv_link}
  </div>
</div>
"""


def build_report(min_score=50, max_hours_old=None):
    """max_hours_old : ne montre que les offres récupérées dans cette
    fenêtre (par défaut REPORT_MAX_HOURS_OLD, ex: 24h). Passe 0/None pour
    voir tout l'historique en base."""
    max_hours_old = REPORT_MAX_HOURS_OLD if max_hours_old is None else max_hours_old
    offers = get_top_offers(min_score=min_score, max_hours_old=max_hours_old or None)
    cards_html = []
    for o in offers:
        conflict = bool(o.get("date_conflict"))
        cv_link = (f'<a class="cv" href="file://{o["cv_path"]}" target="_blank">📄 Voir le CV</a>'
                   if o.get("cv_path") else "")
        letter_link = (f'<a class="cv" href="file://{o["letter_path"]}" target="_blank">✉️ Voir la LM</a>'
                        if o.get("letter_path") else "")
        cv_link = cv_link + letter_link
        cards_html.append(CARD_TEMPLATE.format(
            title=o["title"], company=o.get("company") or "N/A",
            location=o.get("location") or "N/A", source=o["source"],
            score=o.get("llm_score", 0),
            conflict_class=" conflict" if conflict else "",
            conflict_badge='<span class="conflict-badge">⚠ conflit de date</span>' if conflict else "",
            justification=o.get("llm_justification") or "",
            url=o["url"], cv_link=cv_link,
        ))

    html = TEMPLATE.format(
        date=datetime.now().strftime("%d/%m/%Y %H:%M"),
        count=len(offers),
        cards="".join(cards_html) or "<p>Aucune offre ne dépasse le seuil pour l'instant.</p>",
    )
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    return REPORT_OUTPUT_PATH


if __name__ == "__main__":
    path = build_report()
    print("Rapport généré :", path)
