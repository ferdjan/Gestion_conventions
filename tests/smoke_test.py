"""Test de fumée : parcourt toutes les pages et les parcours métier principaux.

Lancement :
    python tests/smoke_test.py

Aucune dépendance externe (``flask.test_client``) ; la base et les fichiers sont
créés dans un dossier temporaire puis supprimés.
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openpyxl import Workbook  # noqa: E402

import app.config as cfg  # noqa: E402
from app import create_app  # noqa: E402
from app import security  # noqa: E402
from app.services import documents as documents_service  # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        FAILURES.append(label)


def csrf_of(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not match:
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    if not match:
        raise AssertionError("jeton CSRF introuvable dans la page")
    return match.group(1)


def form_xml(payload: bytes) -> str:
    """``word/document.xml`` d'un formulaire Word produit par l'application."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert archive.testzip() is None, "archive docx corrompue"
        return archive.read("word/document.xml").decode("utf-8")


def form_text(payload: bytes) -> str:
    """Texte des formulaires, paragraphe par paragraphe (runs joints)."""
    import xml.etree.ElementTree as ET

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(form_xml(payload).encode("utf-8"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.iter(namespace + "t"))
        for paragraph in root.iter(namespace + "p")
    )


def form_data_rows(xml: str) -> int:
    """Nombre de lignes de données (1ʳᵉ cellule = rang numérique)."""
    import xml.etree.ElementTree as ET

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(xml)
    count = 0
    for row in root.iter(namespace + "tr"):
        cells = row.findall(namespace + "tc")
        if not cells:
            continue
        text = "".join(
            node.text or "" for node in cells[0].iter(namespace + "t")
        ).strip()
        if text.isdigit():
            count += 1
    return count


def duplicated_para_ids(xml: str) -> set[str]:
    """Identifiants de paragraphe ``w14:paraId`` présents plusieurs fois."""
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in re.findall(r'w14:paraId="([0-9A-F]+)"', xml):
        (duplicated if value in seen else seen).add(value)
    return duplicated


def table_properties(xml: str) -> list[list[str]]:
    """Enfants de chaque ``w:tblPr`` (ordre du schéma, par tableau)."""
    import xml.etree.ElementTree as ET

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(xml)
    return [
        [child.tag.split("}")[1] for child in properties]
        for properties in root.iter(namespace + "tblPr")
    ]


def model_xml(kind: str) -> str:
    """``word/document.xml`` du modèle Word d'origine (lecture seule)."""
    import io

    from app.reports import docx as docx_report

    raw = docx_report.model_path(kind).read_bytes()
    return zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml").decode("utf-8")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ga-smoke-"))
    export_dir = tmp / "exports"
    upload_dir = tmp / "uploads"
    export_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Les chemins d'export sont figés à l'import : on les redirige vers le test.
    cfg.EXPORT_DIR = export_dir
    cfg.UPLOAD_DIR = upload_dir
    cfg.DB_PATH = tmp / "web_app.db"
    documents_service.EXPORT_DIR = export_dir
    documents_service.TMP_DIR = export_dir / ".tmp"

    app = create_app(
        {"DB_PATH": cfg.DB_PATH, "TESTING": True, "SECRET_KEY": "x" * 32}
    )
    db = app.extensions["db"]
    db.init_schema()

    print("\n[1] Jeu de données")
    db.replace_articles_by_category(
        [
            ("Liste Test", "A1", "Article un", "pièce", 100.0),
            ("Liste Test", "A2", "Article deux", "mètre", 250.5),
        ]
    )
    categories = db.list_categories()
    cat = next((row for row in categories if row["name"] == "Liste Test"), None)
    check(cat is not None, "convention créée", repr([r["name"] for r in categories]))
    db.create_exercice("Liste Test", "2026-2027", "2026-01-01", "2026-12-31", 1000.0)
    exercice = db.get_active_exercice("Liste Test")
    check(exercice is not None, "exercice actif créé")

    client = app.test_client()

    print("\n[2] Pages publiques")
    pages = [
        ("/", "Tableau de bord"),
        ("/documents/new", "Nouvelle commande"),
        ("/history", "Historique"),
        ("/conventions", "Conventions"),
        ("/reports", "Rapport"),
        ("/settings", "Paramètres"),
        ("/inexistant", None),
    ]
    home = None
    for path, marker in pages:
        response = client.get(path)
        if marker is None:
            check(response.status_code == 404, f"GET {path} → 404")
            continue
        html = response.get_data(as_text=True)
        check(
            response.status_code == 200 and marker in html and "Traceback" not in html,
            f"GET {path} → 200",
            f"status={response.status_code}",
        )
        if path == "/":
            home = html
    check(home is not None and csrf_of(home), "jeton CSRF présent")

    token = csrf_of(home or "")

    print("\n[3] En-têtes de sécurité")
    response = client.get("/")
    check("Content-Security-Policy" in response.headers, "CSP présent")
    check(response.headers.get("X-Content-Type-Options") == "nosniff", "nosniff")
    check(response.headers.get("X-Frame-Options") == "DENY", "X-Frame-Options")

    print("\n[4] CSRF refusé sans jeton")
    response = client.post(
        "/api/documents/preview",
        json={"category": "Liste Test", "items": []},
    )
    check(response.status_code == 400, "preview sans jeton → 400", str(response.status_code))
    response = client.post("/conventions/import/seed")
    check(response.status_code == 400, "formulaire sans jeton → 400", str(response.status_code))

    print("\n[5] API : articles, budget, prévisualisation")
    articles = client.get("/api/articles?category=Liste Test&q=article").get_json()
    check(len(articles) == 2, "recherche d'articles")
    article_a1 = next(a for a in articles if a["code"] == "A1")
    a2 = next(a for a in articles if a["code"] == "A2")
    response = client.get("/api/budget?category=Liste Test&amount=0")
    budget = response.get_json()
    check(budget["has_exercice"] and budget["plafond"] == 1000.0, "budget initial")

    payload = {
        "csrf_token": token,
        "category": "Liste Test",
        "items": [{"article_id": article_a1["id"], "quantity": 1}],
    }
    response = client.post("/api/documents/preview", json=payload)
    check(response.status_code == 200, "prévisualisation", str(response.status_code))
    preview = response.get_json()
    check(preview["total_ht"] == 100.0, "total HT = 100", str(preview.get("total_ht")))
    check(str(preview["number"]).endswith("-0001"), "numéro proposé", str(preview.get("number")))

    print("\n[6] Création d'une commande (PDF + Excel)")
    response = client.post("/documents", json=payload)
    check(response.status_code == 201, "création → 201", str(response.status_code))
    created = response.get_json()
    doc_id = created["id"]
    check(created["total_ht"] == 100.0 and created["total_ttc"] == 119.0, "totaux TTC")
    check((export_dir / f"{created['number']}.pdf").is_file(), "PDF généré")
    check((export_dir / f"{created['number']}.xlsx").is_file(), "Excel généré")

    print("\n[7] Historique, détail, téléchargements")
    response = client.get(f"/history?doc={doc_id}")
    html = response.get_data(as_text=True)
    check(response.status_code == 200 and created["number"] in html, "aperçu historique")
    response = client.get(f"/documents/{doc_id}")
    check(response.status_code == 200, "détail document")
    for kind, marker in (("pdf", b"%PDF"), ("xlsx", b"PK")):
        response = client.get(f"/files/{doc_id}/{kind}")
        check(
            response.status_code == 200 and response.data.startswith(marker),
            f"téléchargement {kind}",
            f"status={response.status_code} head={response.data[:6]!r}",
        )
    response = client.get(f"/documents/{doc_id}/export")
    check(
        response.status_code == 200
        and response.headers["Content-Type"].endswith("spreadsheetml.sheet"),
        "export Excel à la volée",
    )
    response = client.get("/files/1/..%2f..%2fweb_app.db")
    check(response.status_code in (400, 404), "traversée de chemin refusée", str(response.status_code))
    check(
        security.safe_export_path(export_dir, "../web_app.db") is None,
        "safe_export_path refuse ../",
    )
    check(
        security.safe_export_path(export_dir, "/etc/passwd") is None,
        "safe_export_path refuse les absolus",
    )

    print("\n[7bis] Formulaires Word (dossier Model/)")
    detail_html = client.get(f"/documents/{doc_id}").get_data(as_text=True)
    check(detail_html.count("data-form-kind=") == 3, "3 boutons sur la fiche")
    preview_html = client.get(f"/history?doc={doc_id}").get_data(as_text=True)
    check(preview_html.count("data-form-kind=") == 3, "3 boutons dans l'historique")
    check("form_dialog.js" in detail_html and "form_dialog.js" in preview_html,
          "script du dialogue chargé")
    for short in ("D.M/F/M", "D.Achat", "D.A.Mag"):
        check(short in detail_html, f"bouton fiche « {short} »", short)
        check(short in preview_html, f"bouton historique « {short} »", short)

    for kind in ("2", "3", "4"):
        response = client.get(f"/documents/{doc_id}/form/{kind}")
        ok = response.status_code == 200 and response.data[:2] == b"PK"
        check(ok, f"formulaire {kind} → docx",
              f"status={response.status_code} head={response.data[:4]!r}")
        check(
            response.headers["Content-Type"].endswith("wordprocessingml.document"),
            f"formulaire {kind} → mimetype docx",
            response.headers.get("Content-Type", ""),
        )
        if not ok:
            continue
        xml = form_xml(response.data)
        check(created["number"] in xml, f"formulaire {kind} : n° de commande")
        check("Article un" in xml, f"formulaire {kind} : désignation")
        check("Page 1/1" in xml, f"formulaire {kind} : mention Page 1/1")
        check(
            form_data_rows(xml) == 10,
            f"formulaire {kind} : 10 lignes normalisées",
            str(form_data_rows(xml)),
        )
        check(
            xml.count("<w:br w:type=\"page\"") == 0,
            f"formulaire {kind} : pas de saut de page (une seule page)",
            str(xml.count("<w:br w:type=\"page\"")),
        )
    xml3 = form_text(client.get(f"/documents/{doc_id}/form/3").data)
    check("Référence de la demande de matières" in xml3, "formulaire 3 : champ référence")

    response = client.get(f"/documents/{doc_id}/form/2?service=Service%20Essai")
    check(
        response.status_code == 200 and "Service Essai" in form_xml(response.data),
        "champ service saisi dans l'URL",
        str(response.status_code),
    )
    response = client.get(f"/documents/{doc_id}/form/9")
    check(response.status_code == 404, "formulaire inconnu → 404", str(response.status_code))
    response = client.get("/documents/99999/form/2")
    check(response.status_code == 404, "commande inexistante → 404", str(response.status_code))

    response = client.post(
        "/settings/defaults",
        data={
            "csrf_token": token,
            "service": "Service par défaut",
            "reference": "REF-0009",
            "convention": "CC-0009",
        },
    )
    check(response.status_code == 302, "défauts des formulaires → 302", str(response.status_code))
    check(
        "Service par défaut" in form_xml(client.get(f"/documents/{doc_id}/form/2").data),
        "défaut service appliqué",
    )
    check(
        "REF-0009" in form_xml(client.get(f"/documents/{doc_id}/form/3").data),
        "défaut référence appliqué",
    )
    check(
        "CC-0009" in form_xml(client.get(f"/documents/{doc_id}/form/4").data),
        "défaut convention appliqué",
    )
    check(
        "Service par défaut"
        not in form_xml(client.get(f"/documents/{doc_id}/form/4").data),
        "formulaire 4 sans service demandeur",
    )

    from app.reports import docx as docx_report

    many = [
        {"code": f"C{i}", "designation": f"Désignation {i}", "unit": "pce", "quantity": i}
        for i in range(1, 17)
    ]
    grown = docx_report.fill_form(
        "2", number="LISTE-0001", date_text="01/01/2026", lines=many, service="S"
    )
    grown_xml = form_xml(grown)
    check(
        form_data_rows(grown_xml) == 20,
        "2 tableaux de 10 lignes au-delà de 10 articles",
        str(form_data_rows(grown_xml)),
    )
    check(grown_xml.count("<w:tblpPr") == 1, "tableau flottant réservé à la page 1",
          str(grown_xml.count("<w:tblpPr")))
    properties = table_properties(grown_xml)
    second = properties[1] if len(properties) == 2 else []
    check(
        len(properties) >= 1
        and "tblpPr" in properties[0]
        and "tblpPr" not in second
        and "jc" in second
        and "tblW" in second
        and second.index("jc") == second.index("tblW") + 1,
        "page 2 : tableau en flux centré (w:jc après w:tblW)",
        str(properties),
    )
    check(
        grown_xml.count('<w:br w:type="page"') == 1,
        "un seul saut de page",
        str(grown_xml.count('<w:br w:type="page"')),
    )
    grown_text = form_text(grown)
    check("Page 1/2" in grown_text, "mention Page 1/2")
    check("Page 2/2" in grown_text, "mention Page 2/2")
    check(grown_text.count("LISTE-0001") == 2, "N° repris sur chaque page",
          str(grown_text.count("LISTE-0001")))
    check(
        grown_text.count("Le service demandeur doit")
        == form_text(
            docx_report.fill_form(
                "2",
                number="LISTE-0001",
                date_text="01/01/2026",
                lines=many[:1],
                service="S",
            )
        ).count("Le service demandeur doit"),
        "note (1)/(2) du modèle 2 : page 1 seulement",
        str(grown_text.count("Le service demandeur doit")),
    )
    check(
        grown_text.count("Observation Gestionnaire des stocks") == 2,
        "zone signature présente sur chaque page",
        str(grown_text.count("Observation Gestionnaire des stocks")),
    )
    check("Désignation 10" in grown_xml, "page 1 : 10 lignes")
    check("Désignation 16" in grown_xml, "page 2 : dernière ligne remplie")
    check("Désignation 11" in grown_xml, "page 2 : première ligne")
    check("Désignation 17" not in grown_xml, "aucune ligne 17")
    check(
        duplicated_para_ids(grown_xml) <= duplicated_para_ids(model_xml("2")),
        "aucun paraId dupliqué ajouté par les clones",
        str(sorted(duplicated_para_ids(grown_xml) - duplicated_para_ids(model_xml("2")))),
    )

    print("\n[8] Blocage de plafond")
    too_much = {
        "csrf_token": token,
        "category": "Liste Test",
        "items": [{"article_id": a2["id"], "quantity": 4}],  # 1002 > 1000
    }
    response = client.post("/api/documents/preview", json=too_much)
    check(response.status_code == 409, "dépassement → 409", str(response.status_code))
    check(response.get_json().get("type") == "budget_block", "type d'erreur plafond")
    response = client.post("/documents", json=too_much)
    check(response.status_code == 409, "création bloquée → 409", str(response.status_code))

    ok_items = {
        "csrf_token": token,
        "category": "Liste Test",
        "items": [{"article_id": a2["id"], "quantity": 1}],  # 250.5
    }
    response = client.post("/documents", json=ok_items)
    check(response.status_code == 201, "commande dans le plafond → 201", str(response.status_code))
    doc2_id = response.get_json()["id"]

    print("\n[9] Modification du document")
    response = client.get(f"/documents/{doc_id}/edit")
    html = response.get_data(as_text=True)
    check(
        response.status_code == 200 and created["number"] in html,
        "écran de modification",
        str(response.status_code),
    )
    edit = {
        "csrf_token": token,
        "items": [
            {"article_id": article_a1["id"], "quantity": 2},
            {"article_id": a2["id"], "quantity": 1},
        ],
    }
    response = client.post(f"/documents/{doc_id}", json=edit)
    check(response.status_code == 200, "modification → 200", str(response.status_code))
    check(response.get_json()["total_ht"] == 450.5, "nouveaux totaux", str(response.get_json().get("total_ht")))

    print("\n[10] Clôture d'exercice et interdiction de saisie")
    ex_id = exercice["id"]
    response = client.post(
        f"/conventions/exercices/{ex_id}/close", data={"csrf_token": token}
    )
    check(response.status_code == 302, "clôture → redirection")
    response = client.post("/documents", json=ok_items)
    check(response.status_code == 409, "saisie après clôture → 409", str(response.status_code))
    response = client.get("/conventions")
    html = response.get_data(as_text=True)
    check("Clôturé" in html, "statut clôturé affiché")

    print("\n[11] Rapports, sauvegarde, modèle")
    response = client.get("/reports")
    check(response.status_code == 200, "page rapports")
    response = client.get("/reports/download?label=2026-2027")
    check(response.status_code == 200, "rapport Excel")
    response = client.get("/settings/backup")
    check(response.status_code == 200, "sauvegarde SQLite")
    response = client.get("/conventions/template")
    check(response.status_code == 200, "modèle Excel vierge")

    print("\n[11bis] Formulaires conventions")
    inf = next(
        (row for row in db.list_categories() if row["name"] == "Informatique"), None
    )
    check(inf is not None, "convention par défaut présente")
    response = client.post(
        f"/conventions/{inf['id']}/exercices",
        data={
            "csrf_token": token,
            "label": "2026-2027",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "plafond": "5 000,00",
        },
    )
    check(response.status_code == 302, "ouverture d'exercice → 302")
    check(
        db.get_active_exercice("Informatique") is not None,
        "exercice actif pour Informatique",
    )
    response = client.post(
        f"/conventions/{inf['id']}/status",
        data={"csrf_token": token, "status": "closed", "expiry_date": "2027-06-30"},
    )
    check(response.status_code == 302, "changement de statut → 302")
    refreshed = next(
        row for row in db.list_categories() if row["name"] == "Informatique"
    )
    check(refreshed["status"] == "closed", "statut clôturé en base")
    response = client.get("/conventions?category=Informatique")
    html_conv = response.get_data(as_text=True)
    check(
        "Clôturé" in html_conv,
        "statut affiché côté interface",
    )
    check(
        'enctype="multipart/form-data"' in html_conv
        and 'form="import-form"' in html_conv
        and 'name="file"' in html_conv,
        "formulaire d'import multipart + fichier associé",
    )
    response = client.get("/documents/new?category=Informatique")
    html = response.get_data(as_text=True)
    check('name="convention"' in html, "assistant : choix de convention")
    check("Aucun exercice actif" in html, "convention sans exercice signalée")
    check("Informatique" not in html, "convention clôturée non proposée")

    print("\n[12] Import Excel")
    source = tmp / "modeles.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Import Test"
    sheet.append(["N°", "Désignation", "Unité de mesure", "Prix unitaire HT"])
    sheet.append(["X1", "Article importé", "pièce", "12,50"])
    workbook.save(source)

    with open(source, "rb") as handle:
        response = client.post(
            "/conventions/import",
            data={"csrf_token": token, "file": (handle, "modeles.xlsx")},
            content_type="multipart/form-data",
        )
    check(response.status_code == 200, "upload analysé", str(response.status_code))
    check("Import Test" in response.get_data(as_text=True), "feuille listée")
    response = client.post(
        "/conventions/import/commit",
        data={
            "csrf_token": token,
            "selected": "0",
            "sheet_0": "Import Test",
            "target_0": "Import Renommé",
        },
    )
    check(response.status_code == 302, "import commité", str(response.status_code))
    check(db.article_count("Import Renommé") == 1, "articles importés sous la cible")

    print("\n[13] Suppression")
    response = client.post(
        f"/documents/{doc2_id}/delete", data={"csrf_token": token}
    )
    check(response.status_code == 302, "suppression → redirection")
    check(db.get_document(doc2_id) is None, "commande retirée de la base")
    response = client.post(
        f"/conventions/{cat['id']}/delete",
        data={"csrf_token": token, "confirm": "Liste Test"},
    )
    check(response.status_code == 302, "suppression de liste → redirection")
    check("Liste Test" not in db.category_names(), "liste supprimée")

    print("\n[14] Erreurs métier parlantes + garde-fou JS")
    app_js = (ROOT / "app" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    check(
        re.search(r"method\s*[:=]\s*[\"']?POST", app_js) is not None,
        "gaFetch impose POST dès qu'il y a un corps",
    )

    # a) convention sans exercice actif : blocage explicite et localisé
    db.replace_articles_by_category(
        [("Sans Exercice", "Z1", "Article sans exercice", "pièce", 10.0)]
    )
    budget0 = client.get("/api/budget?category=Sans Exercice&amount=10").get_json()
    check(budget0["has_exercice"] is False, "budget sans exercice → has_exercice=false")
    zero_articles = client.get("/api/articles?category=Sans Exercice").get_json()
    response = client.post(
        "/api/documents/preview",
        json={
            "csrf_token": token,
            "category": "Sans Exercice",
            "items": [{"article_id": zero_articles[0]["id"], "quantity": 1}],
        },
    )
    check(
        response.status_code == 409, "création sans exercice → 409",
        str(response.status_code),
    )
    payload0 = response.get_json() or {}
    check(
        payload0.get("type") == "missing_exercice",
        "type missing_exercice remonté",
        str(payload0.get("type")),
    )
    check(
        payload0.get("category") == "Sans Exercice",
        "convention portée par l'erreur",
        str(payload0.get("category")),
    )

    # b) convention ouverte et saisissable : prix divergent envoyé par le client
    db.replace_articles_by_category(
        [("Expirée Test", "E1", "Article de test", "pièce", 5.0)]
    )
    db.create_exercice("Expirée Test", "2026", "2026-01-01", "2026-12-31", 1000.0)
    open_articles = client.get("/api/articles?category=Expirée Test").get_json()
    wrong = open_articles[0]
    response = client.post(
        "/api/documents/preview",
        json={
            "csrf_token": token,
            "category": "Expirée Test",
            "items": [
                {
                    "article_id": wrong["id"],
                    "quantity": 1,
                    "unit_price_ht": round(float(wrong["unit_price_ht"]) + 7, 2),
                }
            ],
        },
    )
    check(
        response.status_code == 409
        and (response.get_json() or {}).get("type") == "price_conflict",
        "prix divergent → price_conflict",
        str(response.status_code),
    )

    # c) article qui n'existe pas
    response = client.post(
        "/api/documents/preview",
        json={
            "csrf_token": token,
            "category": "Expirée Test",
            "items": [{"article_id": 99999999, "quantity": 1}],
        },
    )
    check(
        response.status_code == 409
        and (response.get_json() or {}).get("type") == "missing_articles",
        "article inconnu → missing_articles",
        str(response.status_code),
    )

    # d) convention expirée refusée par la base
    db.set_category_status("Expirée Test", "active", "2020-01-01")
    response = client.post(
        "/api/documents/preview",
        json={
            "csrf_token": token,
            "category": "Expirée Test",
            "items": [{"article_id": wrong["id"], "quantity": 1}],
        },
    )
    check(
        response.status_code == 409
        and "expirée" in (response.get_json() or {}).get("message", ""),
        "convention expirée → 409",
        str(response.status_code),
    )

    # e) même convention réactivée : la saisie redevient possible
    db.set_category_status("Expirée Test", "active", None)
    response = client.post(
        "/api/documents/preview",
        json={
            "csrf_token": token,
            "category": "Expirée Test",
            "items": [{"article_id": wrong["id"], "quantity": 1}],
        },
    )
    check(response.status_code == 200, "convention réactivée → preview 200",
          str(response.status_code))

    print("\n[15] Suivi : fiche, année civile, assistant, CSP")
    inf_row = next(row for row in db.list_categories() if row["name"] == "Informatique")
    response = client.get(f"/conventions/{inf_row['id']}")
    check(
        response.status_code == 200 and "Informatique" in response.get_data(as_text=True),
        "fiche convention → 200",
        str(response.status_code),
    )
    response = client.get("/conventions/999999")
    check(response.status_code == 404, "fiche inconnue → 404")

    response = client.get("/reports?mode=civil&year=2026")
    html_civil = response.get_data(as_text=True)
    check(
        response.status_code == 200 and "Année civile" in html_civil,
        "rapport année civile → 200",
        str(response.status_code),
    )
    response = client.get("/reports/download?mode=civil&year=2026")
    check(
        response.status_code == 200
        and response.headers["Content-Type"].endswith("spreadsheetml.sheet"),
        "rapport civil Excel → 200",
        str(response.status_code),
    )
    response = client.get("/reports/download?mode=civil&year=1900")
    check(response.status_code == 404, "année inconnue → 404")

    response = client.get("/documents/new")
    html_new = response.get_data(as_text=True)
    check(
        'data-step-panel="3"' in html_new and 'data-step-nav="1"' in html_new,
        "assistant 3 étapes présent",
    )
    check('name="convention"' in html_new, "choix de convention en étape 1")

    response = client.get("/")
    check(
        "Exercices en cours" in response.get_data(as_text=True),
        "tableau de bord segmenté",
    )

    from app import security as security_mod

    base_html = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    inline = re.search(r"<script>(.*?)</script>", base_html, re.S).group(1)
    digest = "sha256-" + base64.b64encode(
        hashlib.sha256(inline.encode("utf-8")).digest()
    ).decode()
    check(digest == security_mod.THEME_INIT_HASH, "hash CSP du script inline à jour")
    csp = client.get("/").headers.get("Content-Security-Policy", "")
    check(security_mod.THEME_INIT_HASH in csp, "CSP autorise le script inline")

    print(f"\n{CHECKS} vérifications, {len(FAILURES)} échec(s).")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
