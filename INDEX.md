# INDEX — Gestion Articles (édition web)

> **Index technique** du projet `D:\Gestion_convetion` — généré le **03/10/2026**.
> Carte des fichiers, des modules, des routes, du schéma de base et de l'état des
> données. Pour le contexte narratif, voir [`CONTEXTE.md`](CONTEXTE.md) ; pour
> l'utilisateur final, voir [`README.md`](README.md).

## 0. Fiche d'identité

| Élément | Valeur |
| --- | --- |
| Nom | `Gestion Articles` — *Conventions & commandes — édition web* |
| Version | `2.0-web` (`app/config.py` → `VERSION`) |
| Racine | `D:\Gestion_convetion` |
| Nature | Application **Flask** monoposte, **100 % hors-ligne** (aucun CDN, aucun build npm) |
| Serveur | `http://127.0.0.1:8765` (port suivant libre, `PORT_SEARCH_LIMIT = 20`) |
| Base | SQLite `web_app.db` (schéma `version 1`) |
| Sorties | `documents_pdf/web/` (PDF + Excel) |
| Fichiers | 133 fichiers (dont 24 wheels + caches `__pycache__`) — 66 hors wheels/caches, 2,51 Mo |
| Contrôle de version | **aucun dépôt Git** dans ce dossier |

---

## 1. Environnement et contrôles (vérifiés le 03/10/2026)

### Interpréteur détecté

| Élément | Valeur |
| --- | --- |
| Python | `C:\Python314\python.exe` → **3.14.3** |
| `run.bat` cherche dans l'ordre | `C:\Python314\python.exe` → `where python` → `py -3` |
| Python retenu par `run.bat` | `C:\Python314\python.exe` (1er candidat, existe) |

### Bibliothèques installées (interpréteur 3.14)

| Paquet | Version installée | Contrainte `requirements.txt` |
| --- | --- | --- |
| Flask | **3.1.3** | `>=3.0` |
| Jinja2 | **3.1.6** | `>=3.1` |
| Werkzeug | (installé, `__version__` absente en 3.1+) | `>=3.0` |
| itsdangerous | (via Flask) | `>=2.1` |
| openpyxl | **3.1.5** | `>=3.1` |
| reportlab | **4.5.1** | `>=4.0` |

> Les wheels livrées dans `wheels/` couvrent **CPython 3.10 → 3.14** (`win_amd64`)
> et embarquent `reportlab 5.0.1` (au lieu de 4.5.1) : les deux versions sont
> testées vertes.

### Résultats des contrôles (exécutés pour cet index)

| Contrôle | Commande | Résultat |
| --- | --- | --- |
| Compilation | `python -m compileall -q app serve.py tests` | **exit 0** (aucune erreur de syntaxe) |
| Analyse statique | `python -m pyflakes app serve.py tests` | **exit 0** (aucun avertissement) |
| Test de fumée | `python tests\smoke_test.py` | **136 vérifications, 0 échec** |
| Table des routes | `python -m flask --app app routes` | **34 routes** (33 applicatives + `static`) |

---

## 2. Arborescence indexée

```
D:\Gestion_convetion\
├── app\                        # package applicatif Flask
│   ├── __init__.py             # fabrique create_app, filtres Jinja, erreurs, CLI
│   ├── config.py               # constantes, chemins, TVA, seuils, thèmes
│   ├── database.py             # couche SQLite + règles métier  (1477 l., 64 Ko)
│   ├── importer.py             # lecture/écriture .xlsx sans dépendance externe
│   ├── security.py             # CSRF, en-têtes HTTP, anti-traversée de chemin
│   ├── utils.py                # parsing nombres/quantités, formats FR, totaux
│   ├── reports\                # générateurs de sortie
│   │   ├── annual.py           #   rapport de consommation (exercice / année civile)
│   │   ├── docx.py             #   formulaires Word (498 l., zipfile + ElementTree)
│   │   ├── excel.py            #   classeur Excel d'une commande
│   │   └── pdf.py              #   PDF d'une commande (reportlab)
│   ├── routes\                 # blueprints HTTP (7 fichiers)
│   │   ├── api.py              #   API JSON (articles, budget, exercices, preview)
│   │   ├── conventions.py      #   conventions, exercices, imports Excel
│   │   ├── dashboard.py        #   tableau de bord
│   │   ├── documents.py        #   saisie / édition / suppression de commande
│   │   ├── files.py            #   téléchargement PDF / Excel
│   │   ├── history.py          #   historique
│   │   ├── reports.py          #   rapports + export
│   │   └── settings.py         #   paramètres, défauts Word, sauvegarde
│   ├── services\documents.py   # orchestration : numérotation, fichiers, écriture
│   ├── static\
│   │   ├── css\app.css         # 833 l. — styles principaux
│   │   ├── css\themes.css      #  69 l. — variables des 2 thèmes (généré)
│   │   ├── js\                 # 11 fichiers, ~1 200 l. au total
│   │   └── img\favicon.svg
│   └── templates\              # 13 gabarits Jinja (base + 12 écrans/partiels)
├── Model\                      # 3 modèles Word en lecture seule (D.M/F/M, D.Achat, D.A.Mag)
├── documents_pdf\web\          # sorties produites (1 PDF + 1 Excel)
├── uploads\                    # 2 classeurs d'import déposés
├── wheels\                     # 25 wheels pour l'installation hors-ligne
├── tests\smoke_test.py         # 660 l. — test de fumée (aucune dépendance)
├── tools\gen_themes.py         # régénère static\css\themes.css
├── serve.py                    # point d'entrée (port libre, --open, --dev)
├── run.bat                     # installateur + démarreur (détection Python)
├── CONTEXTE.md                 # contexte projet / historique des phases
├── README.md                   # documentation utilisateur
├── LISEZ-MOI.txt               # notice pour le collègue (distribution)
├── requirements.txt            # 6 dépendances
├── source_listes.xlsx          # classeur source (5 feuilles, 194 Ko)
├── web_app.db                  # base SQLite (1,14 Mo)
└── .session.key                # clé de signature des sessions (locale)
```

### Fichiers d'environnement à ne jamais diffuser

`web_app.db`, `.session.key`, `documents_pdf\`, `uploads\` — exclus de
`GestionArticles-v2.0.zip` par `fabriquer_archive.ps1`.

---

## 3. Carte des modules Python

| Fichier | Lignes | Rôle | Points d'entrée |
| --- | ---: | --- | --- |
| `serve.py` | 70 | Lancement local | `main()`, `free_port()` |
| `app/__init__.py` | 196 | Fabrique Flask | `create_app()`, `get_db()`, `_register_filters/_errors/_commands` |
| `app/config.py` | 103 | Constantes | `BASE_DIR`, `DB_PATH`, `EXPORT_DIR`, `TVA_RATE`, `THEMES`, `seed_xlsx()` |
| `app/database.py` | 1477 | Données + métier | classe `Database` + exceptions `PlafondAtteint`, `ConflitPrix`, `ArticlesManquants`, `ExerciceManquant` |
| `app/importer.py` | 284 | Excel sans dépendance | `import_articles[_detailed]()`, `read_sheet_names()`, `write_template()` |
| `app/security.py` | 125 | Garde-fous | `install_security()`, `csrf_token()`, `safe_export_path()`, `filename_safe()` |
| `app/utils.py` | 106 | Utilitaires | `parse_price()`, `parse_quantity()`, `compute_totals()`, `money_short()` |
| `app/services/documents.py` | 303 | Orchestration | `create_document()`, `update_document()`, `export_*()` |
| `app/reports/pdf.py` | 89 | PDF commande | `build_pdf()` |
| `app/reports/excel.py` | 99 | Excel commande | `build_excel()` |
| `app/reports/annual.py` | 167 | Rapport annuel | `build_exercice_report()` |
| `app/reports/docx.py` | 498 | Formulaires Word | `fill_form()`, `FormSpec`, `read_form_defaults()`, `FORM_KINDS/FORM_LABELS/FORM_BUTTONS` |
| `app/routes/*.py` | 28–361 | Blueprints HTTP | voir § 4 |

### Points clés de `app/database.py`

| Groupe | Méthodes |
| --- | --- |
| Schéma / migration | `init_schema()`, `_migrate()`, `_execute_script()`, `_column_exists()` |
| Listes (conventions) | `list_categories()`, `category_row()`, `set_category_status()`, `delete_category()`, `category_prefix()`, `_ensure_categories()` |
| Exercices | `create_exercice()`, `update_exercice()`, `close_exercice()`, `_close_active_exercice()`, `get_active_exercice()`, `_validate_exercice_dates()` |
| Budget | `budget_status()`, `exercice_summary()`, `exercice_consumed()`, `exercice_would_exceed()`, `_assert_within_plafond()` |
| Articles | `search_articles()`, `get_article()`, `list_all_articles()`, `replace_articles_by_category()`, `article_count()` |
| Commandes | `next_document_number()`, `preview_document()`, `save_document()`, `update_document()`, `delete_document()`, `document_editable()`, `list_documents()` |
| Rapports | `exercice_consumption_report()`, `civil_year_report()`, `civil_years()`, `civil_year_documents()` |
| Divers | `get_meta()`, `set_meta()`, `resolve_category_name()`, `connect()` |

---

## 4. Table des routes (34 entrées)

### Écrans HTML

| URL | Endpoint | Rôle |
| --- | --- | --- |
| `/` | `dashboard.index` | Tableau de bord (jauges, alertes 80/90 %) |
| `/documents/new` | `documents.new_document` | Assistant de saisie en 3 étapes |
| `/documents/<id>` | `documents.document_detail` | Fiche commande |
| `/documents/<id>/edit` | `documents.edit_document` | Édition d'une commande |
| `/documents/<id>/form/<kind>` | `documents.document_form` | Formulaire Word rempli (`mf` / `achat` / `mag`) |
| `/history` | `history.index` | Historique + aperçu (`?text=&category=&exercice=&doc=`) |
| `/conventions` | `conventions.index` | Liste des conventions |
| `/conventions/<cat_id>` | `conventions.detail` | Fiche convention |
| `/reports` | `reports.index` | Rapport exercice/année civile (`?mode=&label=&year=`) |
| `/settings` | `settings.index` | Paramètres (compteurs, thème, sauvegarde) |

### Mutations (formulaires / JSON — CSRF obligatoire)

| URL | Endpoint | Méthode | Rôle |
| --- | --- | --- | --- |
| `/documents` | `documents.create_document` | POST | Création (JSON) → 201 |
| `/documents/<id>` | `documents.update_document` | POST | Modification (JSON) |
| `/documents/<id>/delete` | `documents.delete_document` | POST | Suppression |
| `/conventions/<cat_id>/status` | `conventions.set_status` | POST | Ouvrir / clôturer une liste |
| `/conventions/<cat_id>/delete` | `conventions.delete_list` | POST | Supprimer une liste |
| `/conventions/<cat_id>/exercices` | `conventions.create_exercice` | POST | Ouvrir un exercice |
| `/conventions/exercices/<ex_id>/close` | `conventions.close_exercice` | POST | Clôturer (archive consommé/reste) |
| `/conventions/exercices/<ex_id>/update` | `conventions.update_exercice` | POST | Modifier dates / plafond |
| `/conventions/import` | `conventions.import_upload` | POST | Analyser un classeur (prévisualisation) |
| `/conventions/import/commit` | `conventions.import_commit` | POST | Valider l'import (feuille → liste) |
| `/conventions/import/seed` | `conventions.import_seed` | POST | Import direct de `source_listes.xlsx` |
| `/settings/defaults` | `settings.save_defaults` | POST | Défauts des formulaires Word |

### Téléchargements et API JSON

| URL | Endpoint | Méthode | Rôle |
| --- | --- | --- | --- |
| `/files/<id>/pdf` | `files.document_file` | GET | PDF (`?inline=1` pour l'affichage dans l'onglet) |
| `/files/<id>/xlsx` | `files.document_file` | GET | Excel de la commande |
| `/documents/<id>/export` | `documents.export_document` | GET | Export Excel à la volée |
| `/conventions/template` | `conventions.template` | GET | Modèle Excel vierge |
| `/conventions/<cat_id>/export` | `conventions.export_list` | GET | Export d'une liste d'articles |
| `/reports/download` | `reports.download` | GET | Rapport Excel (exercice ou année civile) |
| `/settings/backup` | `settings.backup` | GET | Sauvegarde SQLite (`VACUUM INTO`) |
| `/api/categories` | `api.categories` | GET | Listes disponibles |
| `/api/articles` | `api.articles` | GET | Recherche d'articles (`?category=&text=`) |
| `/api/budget` | `api.budget` | GET | État du plafond |
| `/api/exercices` | `api.exercices` | GET | Exercices d'une liste |
| `/api/documents/<id>` | `api.document` | GET | Détail d'une commande |
| `/api/documents/preview` | `api.preview_document` | POST | Prévisualisation / récapitulatif |
| `/static/<path:filename>` | `static` | GET | CSS, JS, images |

### Gestionnaires d'erreurs (`app/__init__.py`)

`404`, `400`, `413` (> 20 Mo), `500`, plus une famille **métier** renvoyée en
**409** avec un champ `type` :

| Exception | `type` JSON | Signification |
| --- | --- | --- |
| `PlafondAtteint` | `budget_block` | `consommé + commande >= plafond` |
| `ConflitPrix` | `price_conflict` | Les prix en base ont changé (`conflicts[]`) |
| `ArticlesManquants` | `missing_articles` | Article absent ou hors liste (`missing[]`) |
| `ExerciceManquant` | `missing_exercice` | Aucun exercice actif (`category`, `exercice_label`) |
| `ValueError` | `business` | Erreur de validation générique |

---

## 5. Schéma de la base (`app/database.py`, `SCHEMA_VERSION = 1`)

### `categories` — les « conventions »

| Colonne | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK AUTOINCREMENT | |
| `name` | TEXT NOT NULL `COLLATE NOCASE` UNIQUE | nom de la liste/convention |
| `sheet_name` | TEXT | feuille Excel d'origine |
| `prefix` | TEXT | préfixe de numérotation (3 car. max) |
| `status` | TEXT NOT NULL DEFAULT `active` | `active` / `closed` |
| `expiry_date` | TEXT | échéance ; peut rendre le statut `expiree` |

### `app_meta` — métadonnées clé/valeur

`key` (PK) · `value`. Utilisé pour `schema_version`, `defaults_seeded`, et les
valeurs par défaut des formulaires Word (`form_*`).

### `exercices` — exercices budgétaires

| Colonne | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `category` | TEXT NOT NULL | nom de la liste |
| `label` | TEXT NOT NULL | ex. `2026-2027` — `UNIQUE(category, label)` |
| `start_date` / `end_date` | TEXT NOT NULL | dates ISO |
| `plafond` | REAL NULL | `NULL` = illimité |
| `status` | TEXT NOT NULL DEFAULT `active` | `active` / `closed` |
| `consumed_at_close` / `remaining_at_close` | REAL | archive posée à la clôture |
| `closed_at` | TEXT | horodatage de clôture |

### `articles` — listes de prix

| Colonne | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `category` | TEXT NOT NULL | liste d'appartenance |
| `code` | TEXT NOT NULL | |
| `designation` | TEXT NOT NULL | |
| `unit` | TEXT NOT NULL | |
| `unit_price_ht` | REAL NOT NULL `CHECK >= 0` | prix **figé** au moment de la commande |

`UNIQUE(category, code, designation, unit)`.

### `documents` — les commandes

| Colonne | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `number` | TEXT NOT NULL **UNIQUE** | `PRÉFIXE-EXERCICE-0001` |
| `created_at` | TEXT NOT NULL | ISO |
| `category` | TEXT NOT NULL | **valeur libre** (pas de FK — voir § 11) |
| `total_ht` | REAL NOT NULL | somme des totaux de ligne arrondis |
| `tva_rate` / `tva_amount` / `total_ttc` | REAL | TVA 19 % |
| `pdf_path` / `excel_path` | TEXT | **chemins relatifs** à `documents_pdf/web/` |
| `exercice_label` | TEXT | exercice de rattachement |

### `document_items` — lignes de commande

`id` PK · `document_id` · `article_id` (nullable, `SET NULL`) ·
`code` · `designation` · `unit` · `unit_price_ht` · `quantity`
(`CHECK > 0`) · `total_ht`.

### Index déclarés

`idx_exercices_category`, `idx_exercices_status`, `idx_articles_category`,
`idx_articles_search`, `idx_documents_created_at`, `idx_documents_exercice`,
`idx_document_items_document`.

> `connect()` active **WAL**, `foreign_keys = ON` et un `busy_timeout` ; toutes
> les requêtes sont **paramétrées**.

---

## 6. État des données (`web_app.db`, 1,14 Mo, relevé le 03/10/2026)

### Volumétrie

| Table | Lignes |
| --- | ---: |
| `articles` | **5 607** |
| `categories` | 5 |
| `exercices` | 2 |
| `documents` | 1 |
| `document_items` | 8 |
| `app_meta` | 2 (`schema_version = 1`, `defaults_seeded = 1`) |

### Listes (conventions) et articles

| id | Nom | Feuille | Préfixe | Statut | Échéance | Articles |
| ---: | --- | --- | --- | --- | --- | ---: |
| 12 | `Informatique` | Informatique | `INF` | active | — | 218 |
| 13 | `Bureautique` | Bureautique | `BUR` | active | — | 175 |
| 14 | `Infor` | Infor | `IN1` | active | — | 2 398 |
| 15 | `Bure` | Bure | `BU1` | active | — | 350 |
| 16 | `Drog` | Drog | `DRO` | active | — | 2 466 |

> Les 5 lignes correspondent **exactement** aux 5 feuilles de
> `source_listes.xlsx` (feuilles : `Informatique`, `Bureautique`, `Infor`,
> `Bure`, `Drog`). `Informatique` et `Bureautique` sont aussi les deux listes
> créées par défaut (`DEFAULT_CATEGORIES`) : elles ont simplement été peuplées
> par l'import. **Attention** : `Infor` ⊃ contenu de `Informatique` et
> `Bure` ⊃ contenu de `Bureautique` — le même article existe donc dans
> plusieurs listes (voir § 11).

### Exercices ouverts

| id | Liste | Libellé | Période | Plafond | Statut |
| ---: | --- | --- | --- | ---: | --- |
| 5 | `Bure` | `2026-2027` | 01/01/2026 → 30/12/2026 | 2 500 000,00 DA | active |
| 6 | `Drog` | `2026-2027` | 01/02/2026 → 30/01/2027 | 3 000 000,00 DA | active |

> Aucun exercice pour `Informatique`, `Bureautique` et `Infor` → ces listes
> apparaissent dans le bloc « sans exercice » du tableau de bord et refusent
> toute saisie (409 `missing_exercice`).

### Commandes enregistrées

| id | Numéro | Liste | Créé le | Total HT | TVA | Total TTC | Exercice |
| ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | `BU1-2026-2027-0001` | `Bur` ⚠ | 30/09/2026 15:21 | 17 470,78 DA | 3 319,45 DA | 20 790,23 DA | `2026-2027` |

8 lignes d'articles (plastifieuse, massicot, boîtes de classement, chemises,
trombone…). Fichiers produits :

- `documents_pdf\web\BU1-2026-2027-0001.pdf`
- `documents_pdf\web\BU1-2026-2027-0001.xlsx`

### Imports déposés (`uploads\`)

| Fichier | Taille |
| --- | ---: |
| `import-3e309e7148794375b17a5c68fff60a12.xlsx` | 116 679 o |
| `import-63f34ca583324aecba8c3228033ac24e.xlsx` | 27 048 o |

---

## 7. Front-end (aucun CDN, aucun build)

### Templates Jinja (`app/templates/`)

| Fichier | Lignes | Rôle |
| --- | ---: | --- |
| `base.html` | 72 | Gabarit maître — blocs `title`, `page`, `heading`, `subtitle`, `actions`, `content`, `scripts` ; script inline d'init du thème (autorisé par **hash CSP**) |
| `_icons.html` | 62 | Bibliothèque d'icônes SVG en `{% macro %}` |
| `_form_dialog.html` | 41 | Dialogue `<dialog>` de saisie des champs libres Word |
| `dashboard.html` | 157 | Tableau de bord et segments `active` / `no_exercice` / `expired` / `closed` |
| `document_form.html` | 236 | Assistant de saisie en 3 étapes (le plus riche en JS) |
| `document_detail.html` | 70 | Fiche commande + boutons formulaires Word |
| `history.html` | 173 | Historique filtrable + panneau d'aperçu |
| `conventions.html` | 249 | Listes, statuts, exercices, import, modèle Excel |
| `convention_detail.html` | 131 | Fiche d'une convention |
| `import_preview.html` | 81 | Correspondance feuille → liste avant validation |
| `reports.html` | 153 | Rapports (exercice / année civile) + export |
| `settings.html` | 120 | Paramètres, compteurs, thème, sauvegarde |
| `error.html` | 19 | Page d'erreur générique |

### JavaScript (`app/static/js/`, 9 fichiers)

| Fichier | Lignes | Rôle |
| --- | ---: | --- |
| `app.js` | 142 | Socle : `toast()`, **`window.gaFetch`** (CSRF + retry + POST forcé dès qu'il y a un corps), `readCsrf()`, `refreshCsrf()`, `syncTheme()` |
| `document.js` | 701 | Cœur de la saisie : étapes, recherche, panier, totaux, budget, dialogue de conflit de prix, prévisualisation, enregistrement |
| `conventions.js` | 142 | Dialogues conventions/exercices, `suggestLabel(start, end)` |
| `theme.js` | 57 | `window.GATheme` (clair/sombre), `preferred()`, `read()`, `apply()` |
| `form_dialog.js` | 35 | Dialogue des champs de formulaires Word |
| `history.js` | 32 | Filtres et prévisualisation de l'historique |
| `settings.js` | 30 | Marquage des modifications + enregistrement des défauts |
| `import_preview.js` | 23 | « Tout cocher / tout décocher » à l'import |
| `reports.js` | 9 | Rechargement au changement de mode/année |

### CSS (`app/static/css/`)

| Fichier | Lignes | Rôle |
| --- | ---: | --- |
| `app.css` | 833 | Styles de l'application (grilles, tableaux, dialogues, a11y) |
| `themes.css` | 69 | Variables CSS des **2 thèmes** — **généré** par `tools/gen_themes.py` |

Thèmes définis dans `app/config.py` → `THEMES` : `clair` (défaut) et `sombre`,
plus une table `budget` par thème (ok / warn / critical / over / none).

---

## 8. Règles métier invariantes

Ces règles sont implémentées **dans la base** (`app/database.py`), pas seulement
dans l'interface :

| Règle | Implémentation |
| --- | --- |
| **Prix figés** | `_resolve_items()` relit toujours `articles.unit_price_ht` ; un écart > 0,0001 lève `ConflitPrix` (sauf `accept_new_prices`) |
| **Plafond bloquant** | `_assert_within_plafond()` — `consommé [+ projection] >= plafond` → `PlafondAtteint` (égalité incluse) |
| **Alertes budgétaires** | 80 % (`BUDGET_WARN`) et 90 % (`BUDGET_CRITICAL`) |
| **Exercice actif unique** | `_close_active_exercice()` clôture l'exercice précédent avant d'en ouvrir un |
| **Clôture d'exercice** | Archive `consumed_at_close` / `remaining_at_close` / `closed_at` |
| **Convention fermée ou expirée** | `_validate_category_open()` refuse **côté serveur** (pas seulement UI) |
| **Numérotation** | `next_document_number()` → `PRÉFIXE-EXERCICE-NNNN`, unicité vérifiée en base **et** sur disque (`free_number()` / `_files_exist()`) |
| **Articles manquants** | `ArticlesManquants` — un article d'une autre liste est refusé |
| **Quantité** | strictement > 0, finie |
| **TVA** | 19 % (`TVA_RATE`) |
| **Totaux** | `compute_totals()` : total HT = **somme des totaux de ligne arrondis** → identique à l'affichage, au PDF, à l'Excel et en base |
| **Fichiers** | chemins **relatifs** en base, résolus par `safe_export_path()` (refus de `..`, des chemins absolus) |

---

## 9. Sécurité (`app/security.py`)

| Mesure | Détail |
| --- | --- |
| Écoute locale | `serve.py` refuse tout hôte ≠ `127.0.0.1` / `localhost` / `::1` |
| **CSRF** | Obligatoire sur toute mutation ; jeton en session, exposé par `<meta name="csrf-token">` et `csrf_token()` (context processor) ; lu depuis `X-CSRF-Token` (en-tête), le corps JSON (`csrf_token`) ou le formulaire ; comparaison `hmac.compare_digest` |
| CSP | `default-src 'self'`, `script-src 'self' '<hash>'` (script inline du thème autorisé par **`THEME_INIT_HASH`**), `frame-ancestors 'none'`, `form-action 'self'` |
| Autres en-têtes | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cross-Origin-Opener-Policy: same-origin` |
| Cache | `Cache-Control: no-store` sur `/api/*` et les réponses JSON |
| Fichiers | `safe_export_path()` — refus des chemins absolus, des lettres de lecteur et de `..` ; `filename_safe()` nettoie le `Content-Disposition` |
| Session | Clé locale `.session.key` (64 car. hex, `secrets.token_hex(32)`), jamais versionnée ; cookies `HttpOnly` + `SameSite=Lax` |
| Upload | `MAX_CONTENT_LENGTH = 20 Mo` → 413 |
| SQL | 100 % de requêtes paramétrées |

> ⚠️ Un mot de passe **n'est pas** demandé : l'accès est physique (la machine).
> Modifier le script inline de `base.html` **invalide le hash CSP** → il faut
> recalculer `THEME_INIT_HASH` (mode opératoire commenté dans `security.py`) et
> le test de fumée échouera explicitement si ce n'est pas fait.

---

## 10. Scripts d'exploitation

### CLI Flask (déclarés dans `app/__init__.py`)

| Commande | Effet |
| --- | --- |
| `python -m flask --app app init-db` | Crée le schéma + 2 listes par défaut (`Informatique`, `Bureautique`) |
| `python -m flask --app app import-seed` | Importe `source_listes.xlsx` (regroupe par catégorie) |
| `python -m flask --app app backup` | Crée `web_app-backup-AAAAMMJJ-HHMMSS.db` à la racine |

### Lancement

```bat
run.bat                                   :: installateur + démarreur complet
python serve.py                           :: port 8765, sinon les 20 suivants
python serve.py --port 8080 --open --dev
```

### Distribution

```bat
powershell -ExecutionPolicy Bypass -File fabriquer_archive.ps1   :: ..\GestionArticles-v2.0.zip
python -m pip download -r requirements.txt -d wheels --only-binary=:all: --platform win_amd64 --implementation cp --python-version 3.11
```

### Front-end utilitaire

```bat
python tools\gen_themes.py    :: régénère app\static\css\themes.css depuis config.THEMES
```

---

## 11. Anomalies et points d'attention détectés

Classés par gravité. Aucun ne casse le fonctionnement actuel, mais trois méritent
une décision de votre part.

### A. Donnée orpheline : `documents.category = 'Bur'` ⚠ (moyen)

- La commande `BU1-2026-2027-0001` référence la liste **`Bur`**, qui
  **n'existe pas** dans `categories` (les listes sont `Bure`, `Bureautique`,
  `Infor`, `Informatique`, `Drog`).
- **Cause** : `documents.category` est un `TEXT` **sans clé étrangère** → la
  valeur n'est pas contrainte par la table des listes. Le document a donc été
  créé à une époque où une liste nommée `Bur` existait (ou avec un nom saisi
  différemment), puis la liste a été remplacée/re-importée sous `Bure`.
- **Ce n'est pas un bug de code** : `_resolve_category_name()` fait une
  correspondance `COLLATE NOCASE` **exacte**, et `_validate_category_open()`
  refuserait aujourd'hui toute création avec `Bur` (« Convention inconnue »).
- **Impact** : le PDF/Excel et la fiche restent lisibles, mais la commande
  n'apparaît pas dans les rapports d'exercice de `Bure` (le filtre se fait sur
  `category = 'Bure'`), donc le plafond consommé est **sous-estimé de
  17 470,78 DA**.
- **Remède possible** (à faire les yeux ouverts, serveur arrêté) :
  ```sql
  UPDATE documents SET category = 'Bure' WHERE category = 'Bur';
  ```
  La numérotation `BU1-2026-2027-0001` reste cohérente (préfixe `BU1` = `Bure`).
  **Sauvegardez d'abord** (`python -m flask --app app backup`).

### B. Listes qui se recouvrent : `Infor` / `Informatique`, `Bure` / `Bureautique`

- `Infor` (2 398 art.) et `Bure` (350 art.) contiennent en grande partie les
  articles de `Informatique` (218 art.) et `Bureautique` (175 art.).
- Preuve : `COMPRESSEUR D’AIR POUR NETTOYER LE CLAVIER`, `GRAVEUR CD. DVD`,
  `LINGETTE NETTOYANTE`… existent dans **les 5 listes**.
- **Conséquence** : le même article peut être commandé sur plusieurs
  conventions, ce qui fausse l'analyse des consommations et permet de contourner
  un plafond en changeant de liste.
- **Décision attendue** : conserver `Infor`/`Bure`/`Drog` **ou**
  `Informatique`/`Bureautique`/`Drog` — puis supprimer les listes en double
  (Conventions → *Supprimer la liste*, ou `delete_category()`).

### C. Articles partagés entre listes (même racine que B)

- 15 désignations au moins apparaissent dans 3 à 5 listes différentes.
- À noter : plusieurs lignes de `Infor` ont une unité **`—`** (tiret cadratin)
  au lieu d'une vraie unité (`PINCE À RÉSEAUX`, `FICHE RJ 45` par ex.), ce qui
  vient de la feuille Excel source.

### D. Points non validés (repris de `CONTEXTE.md`)

| Point | État |
| --- | --- |
| Rendu visuel / navigation clavier / dialogues `<dialog>` | **non testé à l'écran** |
| Ouverture réelle des `.docx` dans Word/LibreOffice | **non testée** (vérification structurelle seulement) |
| Machine sans Python installé | message d'erreur relu, **pas exécuté** |

### E. Réserves techniques mineures

- `serve.py` en `--dev` active `debug=True` : à ne pas utiliser pour la
  distribution (le mode par défaut est correct).
- Le code de `run.bat` utilise `errorlevel` avec `setlocal EnableExtensions`
  (pas `EnableDelayedExpansion`) : correct ici, mais fragile si on y ajoute des
  variables modifiées dans une boucle `for`.
- Aucun dépôt Git : **aucun historique** des modifications, aucune possibilité
  de `diff`. Une initialisation `git init` + `.gitignore` (`web_app.db`,
  `.session.key`, `uploads/`, `documents_pdf/`, `__pycache__/`, `wheels/`)
  est recommandée avant toute intervention.

---

## 12. Guide « où modifier quoi »

| Je veux… | Fichier(s) à modifier |
| --- | --- |
| Changer le taux de TVA, les seuils d'alerte, le port, les thèmes | `app/config.py` |
| Changer une règle métier (plafond, prix, statuts, numérotation) | `app/database.py` |
| Ajouter une route ou une page | `app/routes/<écran>.py` + blueprint dans `app/__init__.py` + gabarit |
| Modifier l'apparence | `app/static/css/app.css` |
| Ajouter un thème / une couleur | `app/config.py` → `THEMES`, puis `python tools\gen_themes.py` |
| Modifier la saisie (panier, étapes, conflits de prix) | `app/static/js/document.js` |
| Modifier les rapports (colonnes, totaux) | `app/reports/annual.py`, `app/reports/excel.py` |
| Modifier les formulaires Word | `app/reports/docx.py` (modèles dans `Model/`, **lecture seule**) |
| Modifier la lecture Excel | `app/importer.py` |
| Ajouter une vérification | `tests/smoke_test.py` (`check(...)`) |
| Modifier le lancement / l'installation | `serve.py`, `run.bat` |

---

## 13. Reproductibilité des vérifications de cet index

```bat
cd /d D:\Gestion_convetion
C:\Python314\python.exe -m compileall -q app serve.py tests      :: -> exit 0
C:\Python314\python.exe -m pyflakes app serve.py tests           :: -> exit 0
C:\Python314\python.exe tests\smoke_test.py                      :: -> 136 vérifications, 0 échec
C:\Python314\python.exe -m flask --app app routes                :: -> 34 routes
```

État des automatismes front-end (non lancés ici, `node` non requis pour
l'index) :

```bat
node --check app\static\js\*.js      :: 9 fichiers (à relancer après modif JS)
```

---

## 14. Synthèse

- Projet **sain et vérifié** : `compileall` et `pyflakes` propres, test de fumée
  **136/136**, 34 routes, 5 607 articles, 1 commande réelle.
- Architecture **lisible** : `config → database → services → routes → templates`,
  sorties isolées dans `reports/`, aucune dépendance réseau.
- Trois actions recommandées, dans l'ordre :
  1. **Sauvegarder** puis corriger la donnée orpheline `Bur` → `Bure` (§ 11-A).
  2. **Trancher** sur les listes en double `Infor`/`Informatique` et
     `Bure`/`Bureautique` (§ 11-B).
  3. **Initialiser un dépôt Git** pour tracer les prochaines modifications
     (§ 11-E).


---

## 15. Provenance et copies existantes du projet

Cet index a été établi sur `D:\Gestion_convetion`. Il existe **deux autres
emplacements** liés au même projet — à connaître pour éviter de modifier la
mauvaise copie.

| Emplacement | Nature | Dernière modification | Verdict |
| --- | --- | --- | --- |
| `D:\Gestion_convetion` | **Édition web** — version la plus récente | `INDEX.md` (03/10/2026), sources jusqu'au 30/09/2026 | **référence actuelle** |
| `C:\Users\FERDJANI\Desktop\convention\web-app` | Édition web — **copie antérieure** | 27/09/2026 | obsolète |
| `C:\Users\FERDJANI\Desktop\convention` (racine) | **Application de bureau d'origine** (`main.py`, `gestion_articles.db`, `seed_db.py`, `build.bat`, `.gitignore`, `TODO.md`) | — | source métier d'origine |

### Ce que la copie `Desktop\convention\web-app` n'a **pas** (arrivé après le 27/09/2026)

- `app/reports/docx.py` → **formulaires Word** (toute la fonctionnalité)
- `app/static/js/form_dialog.js` et `app/templates/_form_dialog.html` → dialogue de saisie des champs
- Les correctifs d'import (`enctype` du formulaire, `sheet_map` inversée)
- Le vocabulaire « document » → « commande » dans l'interface
- `app/config.py` → `MODEL_DIR` et la détection du dossier `Model/`

Fichiers **modifiés dans les deux copies** (donc divergents) :
`app/__init__.py`, `app/config.py`, `app/database.py`, `app/importer.py`,
`app/routes/api.py`, `app/routes/conventions.py`, `app/routes/documents.py`,
`app/routes/settings.py`, `app/services/documents.py`, `app/static/css/themes.css`,
`app/static/js/document.js`, plusieurs templates, `serve.py`, `run.bat`,
`README.md`, `CONTEXTE.md`.

> **Conclusion** : `D:\Gestion_convetion` est bien la copie à jour. La copie
> Desktop ne doit servir que d'archive (ou être supprimée pour éviter toute
> confusion). Un dépôt Git (§ 11-E) supprimerait ce genre d'ambiguïté.

### Copie versionnée ?

Aucun des trois emplacements n'est un dépôt Git actif (le Desktop contient un
`.gitignore` pour l'application de bureau, mais pas de dossier `.git` rattaché
au web).
