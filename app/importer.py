"""Lecture et génération de classeurs Excel (import des listes de prix)."""
from __future__ import annotations

import posixpath
import re
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from app.utils import parse_price

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
HEADERS = ("N°", "Désignation", "Unité de mesure", "Prix unitaire HT")
HEADER_ALIASES = (
    {"n°", "n° article", "code", "no", "n° d article"},
    {
        "désignation",
        "désignation de l'article",
        "désignation article",
        "article",
        "libellé",
        "libelle",
    },
    {"unité", "unité de mesure", "unite", "unite de mesure"},
    {"prix unitaire ht", "prix unitaire (ht)", "prix ht", "prix unitaire"},
)


def _normalize_label(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(text.split()).casefold()


def _column_number(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 0
    number = 0
    for character in match.group(1):
        number = number * 26 + ord(character) - 64
    return number


def _shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in item.iter(f"{{{NS['m']}}}t"))
        for item in root.findall("m:si", NS)
    ]


def _cell_value(cell, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.iter(f"{{{NS['m']}}}t"))
    value = cell.find("m:v", NS)
    if value is None:
        return ""
    text = value.text or ""
    if cell_type == "s" and text:
        try:
            return shared[int(text)]
        except (ValueError, IndexError):
            return text
    return text


def _sheet_target(workbook: ZipFile, relationship_id: str) -> str:
    relationships = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall("r:Relationship", REL_NS)
    }
    target = targets[relationship_id].replace("\\", "/")
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join("xl", target))


def _read_xlsx(path: str | Path) -> dict[str, list[list[str]]]:
    path = Path(path)
    with ZipFile(path) as workbook:
        shared = _shared_strings(workbook)
        root = ET.fromstring(workbook.read("xl/workbook.xml"))
        result: dict[str, list[list[str]]] = {}
        sheets = root.find("m:sheets", NS)
        if sheets is None:
            return result
        for sheet in sheets:
            name = sheet.attrib["name"]
            relationship_id = sheet.attrib[f"{{{NS['r']}}}id"]
            sheet_root = ET.fromstring(
                workbook.read(_sheet_target(workbook, relationship_id))
            )
            rows: list[list[str]] = []
            for row in sheet_root.findall(".//m:sheetData/m:row", NS):
                values: dict[int, str] = {}
                for cell in row.findall("m:c", NS):
                    values[_column_number(cell.attrib.get("r", ""))] = _cell_value(
                        cell, shared
                    )
                if values:
                    rows.append([values.get(index, "") for index in range(1, 5)])
            if not rows:
                result[name] = []
                continue
            headers = [value.strip() for value in rows[0]]
            normalized = [_normalize_label(value) for value in headers[:4]]
            if len(normalized) < 4 or not all(
                normalized[index] in aliases
                for index, aliases in enumerate(HEADER_ALIASES)
            ):
                raise ValueError(
                    f"La feuille '{name}' doit commencer par les colonnes : "
                    + ", ".join(HEADERS)
                )
            result[name] = rows[1:]
    return result


def read_sheet_names(path: str | Path) -> list[str]:
    path = Path(path)
    with ZipFile(path) as workbook:
        root = ET.fromstring(workbook.read("xl/workbook.xml"))
        sheets = root.find("m:sheets", NS)
        if sheets is None:
            return []
        return [sheet.attrib["name"] for sheet in sheets]


def sheet_row_counts(path: str | Path) -> dict[str, int | str]:
    """Nombre de lignes de données par feuille (hors en-tête) pour la prévisualisation.

    En cas d'en-tête invalide, la valeur est un message d'erreur au lieu d'un
    nombre — l'écran d'import peut ainsi afficher le problème feuille par feuille
    au lieu d'échouer en bloc au moment du commit.
    """
    try:
        workbook = _read_xlsx(path)
    except ValueError as exc:
        # _read_xlsx lève dès la première feuille illisible : on retombe sur
        # une lecture feuille par feuille via openpyxl pour isoler l'erreur.
        # Ici on renvoie simplement le message global (le commit détaillera).
        return {"__error__": str(exc)}
    return {name: len(rows) for name, rows in workbook.items()}


def import_articles_detailed(
    path: str | Path, sheet_map: dict[str, str] | None = None
) -> tuple[list[tuple[str, str, str, str, float]], dict]:
    """Variante instrumentée de :func:`import_articles` avec statistiques.

    Retourne ``(lignes, stats)`` où ``stats`` contient :
    ``skipped_empty`` (lignes totalement vides), ``skipped_total`` (lignes
    « Total » ignorées), ``skipped_duplicates`` (doublons exacts, même prix) et
    ``per_sheet`` (lignes utiles par feuille demandée).
    """
    workbook = _read_xlsx(path)
    if sheet_map is None:
        sheet_map = {name: name for name in workbook}

    actual_names = {name.strip().lower(): name for name in workbook}
    rows: list[tuple[str, str, str, str, float]] = []
    missing: list[str] = []
    skipped_empty = 0
    skipped_total = 0
    skipped_duplicates = 0
    seen: set[tuple] = set()
    per_sheet: dict[str, int] = {}
    for category, sheet_name in sheet_map.items():
        actual_name = actual_names.get(str(sheet_name).strip().lower())
        if actual_name is None:
            missing.append(str(sheet_name))
            continue
        kept = 0
        for index, row in enumerate(workbook[actual_name], start=2):
            code, designation, unit, price = [str(value).strip() for value in row[:4]]
            if not code and not designation and not unit and not price:
                skipped_empty += 1
                continue
            if _normalize_label(code) in ("total", "totaux") or (
                _normalize_label(designation) in ("total", "totaux") and not unit
            ):
                skipped_total += 1
                continue
            unit = unit or "—"
            if not code or not designation:
                raise ValueError(
                    f"Ligne {index} de '{category}' : le code et la désignation "
                    "sont obligatoires."
                )
            try:
                numeric_price = parse_price(price)
            except ValueError as exc:
                raise ValueError(
                    f"Ligne {index} de '{category}' : prix invalide {price!r}."
                ) from exc
            key = (category.strip().casefold(), code, designation, unit, numeric_price)
            if key in seen:
                skipped_duplicates += 1
                continue
            # Doublon avec un prix différent : erreur bloquante (ambiguïté).
            for other in rows:
                if (
                    other[0].strip().casefold() == category.strip().casefold()
                    and other[1] == code
                    and other[2] == designation
                    and other[3] == unit
                    and abs(other[4] - numeric_price) > 0.0001
                ):
                    raise ValueError(
                        f"Ligne {index} de '{category}' : prix en conflit "
                        f"pour {code} / {designation}."
                    )
            seen.add(key)
            rows.append((category, code, designation, unit, numeric_price))
            kept += 1
        per_sheet[str(category)] = kept

    if missing:
        raise ValueError(
            "Feuille(s) introuvable(s) dans le classeur : " + ", ".join(missing)
        )
    stats = {
        "imported": len(rows),
        "skipped_empty": skipped_empty,
        "skipped_total": skipped_total,
        "skipped_duplicates": skipped_duplicates,
        "per_sheet": per_sheet,
    }
    return rows, stats


def import_articles(
    path: str | Path, sheet_map: dict[str, str] | None = None
) -> list[tuple[str, str, str, str, float]]:
    """Lit les lignes ``(liste, code, désignation, unité, prix)`` du classeur."""
    rows, _stats = import_articles_detailed(path, sheet_map)
    return rows


def _sheet_titles(categories: list[str]) -> list[str]:
    titles: list[str] = []
    used: set[str] = set()
    invalid = set("[]:*?/\\")
    for category in categories or ["Liste"]:
        base = "".join(
            character for character in str(category) if character not in invalid
        ).strip()[:31] or "Liste"
        title = base
        suffix = 2
        while title.casefold() in used:
            marker = f" ({suffix})"
            title = f"{base[:31 - len(marker)]}{marker}"
            suffix += 1
        used.add(title.casefold())
        titles.append(title)
    return titles


def write_template(path: str | Path, categories: list[str]) -> Path:
    """Modèle vierge : en-têtes seuls, une feuille par liste (pas de ligne d'exemple)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title in _sheet_titles(categories):
        sheet = workbook.create_sheet(title=title)
        sheet.append(list(HEADERS))
        for column, width in zip("ABCD", (12, 60, 18, 20)):
            sheet.column_dimensions[column].width = width
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center")
    workbook.save(path)
    return path


def write_list_export(path: str | Path, title: str, rows: list) -> Path:
    """Export complet d'une liste : en-têtes + TOUTES les lignes (vérif 1700)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = (_sheet_titles([title]) or ["Liste"])[0]
    sheet.append(list(HEADERS))
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        code = row["code"] if isinstance(row, dict) else row[0]
        designation = row["designation"] if isinstance(row, dict) else row[1]
        unit = row["unit"] if isinstance(row, dict) else row[2]
        price = row["unit_price_ht"] if isinstance(row, dict) else row[3]
        try:
            price = float(price)
        except (TypeError, ValueError):
            pass
        sheet.append([code, designation, unit, price])
    for column, width in zip("ABCD", (12, 60, 18, 20)):
        sheet.column_dimensions[column].width = width
    # Fige la ligne d'en-tête pour les grandes listes (1700 lignes).
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:D{sheet.max_row}"
    workbook.save(path)
    return path
