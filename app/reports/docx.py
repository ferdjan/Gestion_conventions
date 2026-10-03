"""Remplissage des formulaires Word du dossier ``Model/`` à partir d'une commande.

Les trois modèles sont des fichiers `.docx` **conservés en lecture seule** : on en
relit le contenu en mémoire, on modifie uniquement ``word/document.xml``
(``xml.etree.ElementTree``, même technique que ``app/importer.py`` pour les
classeurs) et on renvoie un nouveau `.docx`. Aucune dépendance externe, aucun
écrit dans ``Model/``, 100 % hors-ligne.

Formulaires disponibles :

======  ==========================================================
Kind    Modèle
======  ==========================================================
``2``   Demande de matières, fournitures et matériels
``3``   Demande d'achat
``4``   Demande d'approvisionnement du magasin
======  ==========================================================

**Pagination** : chaque page contient un formulaire **complet** (en-tête, champs
libres, tableau de ``LINES_PER_PAGE`` lignes, observations et signatures).
Au-delà, une nouvelle page commence — même numéro de commande, avec la mention
« Page x/y » sur une ligne sous le N°. La note de bas de page du modèle 2 n'est
reproduite que sur la première page.

Champs remplis automatiquement : n° (numéro de commande), date, service
demandeur, référence de la demande de matières, n° de convention commerciale et
les lignes d'articles. Les zones d'observation, d'avis et de signature restent
**intactes** (à compléter à la main ou par les responsables).
"""
from __future__ import annotations

import copy
import io
import re
import zipfile
from pathlib import Path
from typing import NamedTuple

import xml.etree.ElementTree as ET

from app.config import MODEL_DIR

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ELLIPSIS = "\u2026"

# Nombre de lignes d'articles par page : les trois modèles sont normalisés à
# cette capacité (le modèle 2 perd 3 lignes vierges, le modèle 3 en gagne 3).
LINES_PER_PAGE = 10

# Clés app_meta des valeurs par défaut saisies dans Paramètres.
META_SERVICE = "form_service_demandeur"
META_REFERENCE = "form_ref_demande"
META_CONVENTION = "form_convention"
META_KEYS = {"service": META_SERVICE, "reference": META_REFERENCE, "convention": META_CONVENTION}


def qn(tag: str) -> str:
    """Clé XML ``{namespace}localname`` (le préfixe ``w:`` est accepté)."""
    return f"{{{W_NS}}}{tag.split(':')[-1]}"


class FormSpec(NamedTuple):
    """Description d'un modèle de formulaire."""

    pattern: str                 # glob résolu dans MODEL_DIR (noms irréguliers)
    columns: tuple[str, ...]     # colonnes des lignes de données, dans l'ordre
    has_service: bool = True     # champ « Service demandeur »
    has_reference: bool = False  # champ « Référence de la demande de matières… »
    has_convention: bool = False # champ « Convention commerciale du centre N° »


FORMS: dict[str, FormSpec] = {
    "2": FormSpec(
        pattern="2-*.docx",
        columns=("number", "designation", "quantity", "observation"),
        has_service=True,
    ),
    "3": FormSpec(
        pattern="3-*.docx",
        columns=("number", "designation", "quantity", "observation"),
        has_service=True,
        has_reference=True,
    ),
    "4": FormSpec(
        pattern="4-*.docx",
        columns=("number", "designation", "reference", "unit", "quantity"),
        has_service=False,
        has_convention=True,
    ),
}

FORM_KINDS = tuple(sorted(FORMS))
# Libellés complets (titre du dialogue de téléchargement).
FORM_LABELS = {
    "2": "Demande de matières, fournitures et matériels",
    "3": "Demande d'achat",
    "4": "Demande d'approvisionnement du magasin",
}
# Libellés courts affichés sur les boutons (fiche commande et historique).
FORM_BUTTONS = {
    "2": "D.M/F/M",
    "3": "D.Achat",
    "4": "D.A.Mag",
}
MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


# ------------------------------------------------------------------ lecture


def model_path(kind: str) -> Path:
    """Chemin du modèle Word correspondant (résolu par préfixe de nom)."""
    spec = FORMS.get(str(kind))
    if spec is None:
        raise ValueError(f"Formulaire inconnu : {kind!r}.")
    matches = sorted(MODEL_DIR.glob(spec.pattern))
    if not matches:
        raise ValueError(f"Modèle introuvable dans {MODEL_DIR} ({spec.pattern}).")
    return matches[0]


def read_form_defaults(db) -> dict[str, str]:
    """Valeurs par défaut des champs libres, lues dans ``app_meta``."""
    return {
        name: (db.get_meta(key) or "").strip()
        for name, key in META_KEYS.items()
    }


def write_form_defaults(db, values: dict[str, str]) -> None:
    """Écrit les valeurs par défaut des champs libres dans ``app_meta``."""
    for name, key in META_KEYS.items():
        db.set_meta(key, str(values.get(name) or "").strip())


# --------------------------------------------------------------- remplissage


def fill_form(
    kind: str,
    *,
    number: str,
    date_text: str,
    lines: list[dict],
    service: str = "",
    reference: str = "",
    convention: str = "",
) -> bytes:
    """Renvoie le `.docx` rempli (binaire), sans toucher au modèle d'origine.

    Une page = un formulaire complet de ``LINES_PER_PAGE`` lignes ; les articles
    suivants déclenchent une nouvelle page (même N° + « Page x/y »).
    """
    spec = FORMS.get(str(kind))
    if spec is None:
        raise ValueError(f"Formulaire inconnu : {kind!r}.")

    raw = model_path(kind).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        document_xml = archive.read("word/document.xml")
    root, decls, declaration = _parse(document_xml)

    body = root.find(".//" + qn("w:body"))
    table = body.find(qn("w:tbl")) if body is not None else None
    if body is None or table is None:
        raise ValueError("Modèle illisible : aucun tableau trouvé.")

    rows = table.findall(qn("w:tr"))
    header_index = _header_index(rows)
    if header_index is None:
        raise ValueError("Modèle illisible : en-tête de tableau introuvable.")

    # Modèle normalisé à LINES_PER_PAGE lignes, puis cloné une fois par page
    # **avant** tout remplissage (chaque page est remplie indépendamment).
    _normalize(table, _data_rows(rows, header_index, len(spec.columns)), LINES_PER_PAGE)
    _repeat_header(rows[header_index])

    chunks = [
        lines[start : start + LINES_PER_PAGE]
        for start in range(0, len(lines), LINES_PER_PAGE)
    ] or [[]]
    total = len(chunks)
    pages = [table] + [_clone_table(table) for _ in range(total - 1)]

    for index, page_table in enumerate(pages):
        _fill_page(
            page_table,
            spec,
            number=number,
            date_text=date_text,
            service=service,
            reference=reference,
            convention=convention,
            page_text=f"Page {index + 1}/{total}",
            lines=chunks[index],
        )

    _rebuild_body(body, table, pages)
    document = declaration + _serialize(root, decls)
    return _repack(raw, document)


def _fill_page(
    table: ET.Element,
    spec: FormSpec,
    *,
    number: str,
    date_text: str,
    service: str,
    reference: str,
    convention: str,
    page_text: str,
    lines: list[dict],
) -> None:
    rows = table.findall(qn("w:tr"))
    header_index = _header_index(rows)
    if header_index is None:
        raise ValueError("Modèle illisible : en-tête de tableau introuvable.")
    data_rows = _data_rows(rows, header_index, len(spec.columns))

    _fill_labels(
        rows[:header_index], number, date_text, spec, service, reference, page_text
    )
    if spec.has_convention:
        _fill_convention(rows[header_index + len(data_rows) :], convention)
    for index, line in enumerate(lines):
        _fill_data_row(data_rows[index], spec.columns, index, line)


def _rebuild_body(body: ET.Element, first_table: ET.Element, pages: list[ET.Element]) -> None:
    """Recompose le corps : page 1 (éléments d'origine) puis une page par clone."""
    children = list(body)
    section = next(
        (child for child in children if child.tag == qn("w:sectPr")), None
    )
    # Page 1 = le tableau d'origine + tout ce qui le suit (note éventuelle).
    tail = []
    seen_table = False
    for child in children:
        if child is section:
            continue
        if child is first_table:
            seen_table = True
            continue
        if seen_table:
            tail.append(child)

    sequence: list[ET.Element] = [first_table, *tail]
    for page in pages[1:]:
        sequence.append(_page_break_paragraph())
        sequence.append(page)
        sequence.append(ET.Element(qn("w:p")))

    for child in list(body):
        body.remove(child)
    for child in sequence:
        body.append(child)
    if section is not None:
        body.append(section)


def _page_break_paragraph() -> ET.Element:
    paragraph = ET.Element(qn("w:p"))
    run = ET.SubElement(paragraph, qn("w:r"))
    br = ET.SubElement(run, qn("w:br"))
    br.set(qn("w:type"), "page")
    return paragraph


def _clone_table(table: ET.Element) -> ET.Element:
    """Copie d'un tableau pour une page suivante : hors d'ancrage, centrée.

    Le modèle est un tableau *flottant* (``w:tblpPr``) ancré au texte : copié tel
    quel après un saut de page, il se retrouverait en fin de page précédente. Les
    pages 2+ passent donc en tableau normal, centré par ``w:jc`` (même position
    horizontale, début de page déterministe).
    """
    clone = copy.deepcopy(table)
    _strip_ids(clone)
    properties = clone.find(qn("w:tblPr"))
    if properties is not None:
        floating = properties.find(qn("w:tblpPr"))
        if floating is not None:
            properties.remove(floating)
        if properties.find(qn("w:jc")) is None:
            alignment = ET.Element(qn("w:jc"))
            alignment.set(qn("w:val"), "center")
            # Ordre du schéma : jc vient après w:tblW, avant w:tblCellMar.
            anchor = properties.find(qn("w:tblCellMar"))
            position = list(properties).index(anchor) if anchor is not None else len(properties)
            properties.insert(position, alignment)
    return clone


def _parse(raw: bytes) -> tuple[ET.Element, dict[str, str], str]:
    text = raw.decode("utf-8")
    declaration = text.splitlines()[0] + "\n" if text.startswith("<?xml") else ""
    head_end = text.find(">", text.find("<w:document"))
    head = text[: head_end + 1]
    decls = dict(re.findall(r'xmlns:([A-Za-z0-9]+)="([^"]+)"', head))
    for prefix, uri in decls.items():
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:  # préfixe réservé (« xml »)
            continue
    return ET.fromstring(raw), decls, declaration


def _serialize(root: ET.Element, decls: dict[str, str]) -> str:
    out = ET.tostring(root, encoding="unicode")
    # ElementTree omet les déclarations d'espace de nom inutilisées alors que
    # ``mc:Ignorable`` les référence : Word refuserait le fichier.
    start = out.find("<w:document")
    end = out.find(">", start)
    if start >= 0 and end > start:
        tag = out[start:end]
        missing = [
            f'xmlns:{prefix}="{uri}"'
            for prefix, uri in decls.items()
            if f'xmlns:{prefix}=' not in tag
        ]
        if missing:
            out = out[:end] + " " + " ".join(missing) + out[end:]
    return out


def _repack(raw: bytes, document_xml: str) -> bytes:
    source = io.BytesIO(raw)
    target = io.BytesIO()
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(
        target, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            data = (
                document_xml.encode("utf-8")
                if info.filename == "word/document.xml"
                else zin.read(info.filename)
            )
            zout.writestr(info, data)
    return target.getvalue()


# ------------------------------------------------------------- structure


def _cell_text(cell: ET.Element) -> str:
    return "".join(node.text or "" for node in cell.iter(qn("w:t")))


def _row_cells(row: ET.Element) -> list[ET.Element]:
    return row.findall(qn("w:tc"))


def _header_index(rows: list[ET.Element]) -> int | None:
    for index, row in enumerate(rows):
        cells = _row_cells(row)
        if cells and _cell_text(cells[0]).strip() == "N°":
            return index
    return None


def _data_rows(rows: list[ET.Element], header_index: int, columns: int) -> list[ET.Element]:
    """Lignes de données contiguës juste après l'en-tête (1ʳᵉ cellule = rang)."""
    out: list[ET.Element] = []
    for row in rows[header_index + 1 :]:
        cells = _row_cells(row)
        if len(cells) != columns or not _cell_text(cells[0]).strip().isdigit():
            break
        out.append(row)
    return out


def _normalize(
    table: ET.Element, data_rows: list[ET.Element], target: int
) -> list[ET.Element]:
    """Ramène le tableau à exactement ``target`` lignes de données (10 par page)."""
    if not data_rows:
        raise ValueError("Modèle illisible : aucune ligne de données.")
    if len(data_rows) > target:
        for row in data_rows[target:]:
            table.remove(row)
        data_rows = data_rows[:target]
    elif len(data_rows) < target:
        data_rows = _grow(table, data_rows, target)
    _renumber(data_rows)
    return data_rows


def _renumber(data_rows: list[ET.Element]) -> None:
    """Réattribue les rangs 1..n (utile après clonage de lignes vierges)."""
    for index, row in enumerate(data_rows):
        cells = _row_cells(row)
        if cells:
            _set_cell_text(cells[0], str(index + 1))


def _grow(table: ET.Element, data_rows: list[ET.Element], needed: int) -> list[ET.Element]:
    """Clone la dernière ligne de données jusqu'à atteindre ``needed`` lignes."""
    if not data_rows or needed <= len(data_rows):
        return data_rows
    model = data_rows[-1]
    extra: list[ET.Element] = []
    anchor = list(table).index(model)
    for _ in range(needed - len(data_rows)):
        clone = _clone_row(model)
        anchor += 1
        table.insert(anchor, clone)
        extra.append(clone)
    return data_rows + extra


def _strip_ids(node: ET.Element) -> None:
    """Supprime les marqueurs et identifiants non réutilisables d'une copie.

    Les ``w14:paraId``/``textId`` et les signets doivent être uniques dans un
    fichier Word : une copie qui les reprend tels quels déclenche « Le contenu
    de ce document comporte des erreurs » à l'ouverture.
    """
    for parent in node.iter():
        for child in list(parent):
            if child.tag in (qn("w:bookmarkStart"), qn("w:bookmarkEnd")):
                parent.remove(child)
    for element in node.iter():
        for attribute in list(element.attrib):
            if attribute.endswith("}paraId") or attribute.endswith("}textId"):
                del element.attrib[attribute]


def _clone_row(row: ET.Element) -> ET.Element:
    clone = copy.deepcopy(row)
    _strip_ids(clone)
    return clone


def _repeat_header(row: ET.Element) -> None:
    """Répète la ligne d'en-tête sur chaque page (pagination des formulaires)."""
    if row.find(qn("w:tblHeader")) is not None:
        return
    properties = row.find(qn("w:trPr"))
    if properties is None:
        properties = ET.Element(qn("w:trPr"))
        row.insert(0, properties)
    ET.SubElement(properties, qn("w:tblHeader"))


# ------------------------------------------------------------- remplissage


def _set_run_text(run: ET.Element, text: str) -> None:
    for child in list(run):
        if child.tag != qn("w:rPr"):
            run.remove(child)
    node = ET.SubElement(run, qn("w:t"))
    node.text = text
    if text != text.strip():
        node.set(f"{{{XML_NS}}}space", "preserve")


def _set_cell_text(cell: ET.Element, text: str) -> None:
    """Écrit ``text`` dans une cellule de données en conservant la mise en forme."""
    paragraphs = cell.findall(qn("w:p"))
    if not paragraphs:
        paragraphs = [ET.SubElement(cell, qn("w:p"))]
    paragraph = paragraphs[0]
    for extra in paragraphs[1:]:
        cell.remove(extra)
    runs = [child for child in paragraph if child.tag == qn("w:r")]
    if runs:
        _set_run_text(runs[0], str(text))
        for extra in runs[1:]:
            paragraph.remove(extra)
    else:
        run = ET.SubElement(paragraph, qn("w:r"))
        _set_run_text(run, str(text))


def _ellipsis_index(text: str) -> int | None:
    position = text.find(ELLIPSIS)
    if position >= 0:
        return position
    match = re.search(r"\.{3,}", text)
    return match.start() if match else None


def _fill_paragraph(paragraph: ET.Element, value: str) -> bool:
    """Remplace le libellé pointillé d'un paragraphe (« N° : ……/2025 » → valeur).

    Certains modèles n'ont plus de pointillés après le libellé (« N° : ») : la
    valeur est alors simplement ajoutée en fin de ligne.
    """
    runs = [child for child in paragraph if child.tag == qn("w:r")]
    if not runs:
        return False
    texts = ["".join(node.text or "" for node in run.iter(qn("w:t"))) for run in runs]
    index = _ellipsis_index("".join(texts))
    if index is None:
        _set_run_text(runs[-1], texts[-1] + str(value))
        return True

    position = 0
    target = -1
    offset = 0
    for i, text in enumerate(texts):
        if index < position + len(text):
            target, offset = i, index - position
            break
        position += len(text)
    if target < 0:
        return False

    _set_run_text(runs[target], texts[target][:offset] + str(value))
    for extra in runs[target + 1 :]:
        paragraph.remove(extra)
    return True


def _fill_labels(
    rows: list[ET.Element],
    number: str,
    date_text: str,
    spec: FormSpec,
    service: str,
    reference: str,
    page_text: str = "",
) -> None:
    values = {"N°": number, "Date": date_text}
    if spec.has_service:
        values["Service demandeur"] = service
    if spec.has_reference:
        values["Référence de la demande"] = reference

    paged = False
    for row in rows:
        for cell in _row_cells(row):
            for paragraph in cell.findall(qn("w:p")):
                text = "".join(
                    node.text or "" for node in paragraph.iter(qn("w:t"))
                )
                for label, value in values.items():
                    if not text.startswith(label):
                        continue
                    if not _fill_paragraph(paragraph, value):
                        break
                    if label == "N°" and page_text and not paged:
                        # Ligne « Page x/y » sous le N°, même cellule.
                        _insert_page_line(cell, paragraph, page_text)
                        paged = True
                    break


def _insert_page_line(cell: ET.Element, paragraph: ET.Element, text: str) -> None:
    """Insère juste sous ``paragraph`` une copie formatée « Page x/y »."""
    page_paragraph = copy.deepcopy(paragraph)
    _strip_ids(page_paragraph)
    _set_paragraph_text(page_paragraph, text)
    cell.insert(list(cell).index(paragraph) + 1, page_paragraph)


def _set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    runs = [child for child in paragraph if child.tag == qn("w:r")]
    if runs:
        _set_run_text(runs[0], text)
        for extra in runs[1:]:
            paragraph.remove(extra)
    else:
        run = ET.SubElement(paragraph, qn("w:r"))
        _set_run_text(run, text)


def _fill_convention(rows: list[ET.Element], convention: str) -> None:
    for row in rows:
        for cell in _row_cells(row):
            for paragraph in cell.findall(qn("w:p")):
                text = "".join(node.text or "" for node in paragraph.iter(qn("w:t")))
                if "Convention commerciale du centre" in text:
                    _fill_paragraph(paragraph, convention)


def _quantity(value) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _fill_data_row(row: ET.Element, columns: tuple[str, ...], index: int, line: dict) -> None:
    cells = _row_cells(row)
    if len(cells) < len(columns):
        raise ValueError("Modèle illisible : ligne de données incomplète.")
    values = {
        "number": str(index + 1),
        "designation": str(line.get("designation") or ""),
        "reference": str(line.get("code") or ""),
        "unit": str(line.get("unit") or ""),
        "quantity": _quantity(line.get("quantity")),
        "observation": "",
    }
    for cell, column in zip(cells, columns):
        if column == "observation":
            continue  # zone réservée au gestionnaire de stocks
        _set_cell_text(cell, values[column])
