# Contexte projet — édition web « Gestion Articles »

> Document de reprise pour un assistant IA (ou un développeur) qui reprendrait le
> projet. Pour l'utilisateur final, voir [`README.md`](README.md).
>
> État au 28/09/2026 — phases 1 → 7 terminées, puis phases correctives :
> Ph1 (déblocage ajout document : gaFetch POST, bouton +, ExerciceManquant),
> Ph2 (suivi : dashboard segmenté, fiche convention, rapports année civile +
> année convention, assistant 3 étapes), Ph3 (2 thèmes clair/sombre, CSS/a11y),
> puis correctifs d'import : `enctype="multipart/form-data"` manquant sur le
> formulaire (aucun fichier n'arrivait au serveur) + `sheet_map` inversée dans
> `import_commit` (cible ≠ feuille → « Feuille introuvable »).
> Puis vocabulaire « document » → « commande » dans toute l'interface
> (URLs, base et code technique inchangés) + correctif du bouton de
> vérification vidé par `saveLabel` capturé avant l'assignation de `saveBtn`.
> Vérifications vertes (smoke 83/83, E2E Chrome headless sans erreur).
>
> Puis **formulaires Word** (dossier `Model/`, 3 `.docx` vides en lecture seule) :
> boutons « **D.M/F/M** / **D.Achat** / **D.A.Mag** » sur la fiche commande **et**
> dans l'aperçu de l'historique, remplissage à la volée sans aucune dépendance
> (`app/reports/docx.py`, `zipfile` + `ElementTree` comme `importer.py`),
> dialogue de saisie des champs libres (`_form_dialog.html` +
> `form_dialog.js`) et valeurs par défaut en Paramètres (`app_meta`).
> Puis **pagination** : 10 lignes d'articles par page, chaque page étant un
> formulaire complet (en-tête, N°, champs libres, « Page x/y », tableau,
> signatures), la note (1)/(2) du modèle 2 restant sur la page 1.
> Vérifications vertes : **smoke 136/136**, `pyflakes`/`compileall`/`node --check` propres.
>
> Puis **distribution hors-ligne** : `wheels/` (paquets pour Python 3.10 → 3.14,
> `win_amd64`), `run.bat` installe d'abord en `--no-index` puis replie sur
> `pip` en ligne, `source_listes.xlsx` embarqué, `LISEZ-MOI.txt` pour le
> collègue, `fabriquer_archive.ps1` → `GestionArticles-v2.0.zip` (39 Mo, sans
> `web_app.db` / `.session.key` / `uploads` / `documents_pdf`).
> `serve.py` gagne le port suivant libre (`PORT_SEARCH_LIMIT`) et `--open`
> (navigateur sur l'URL réelle). Validé par installation à froid dans un dossier
> vierge (venv `--no-index`, `init-db` + `import-seed`, smoke 136/136, `run.bat`).
>
> Puis **refonte visuelle de l'écran « Nouvelle commande »** (étape 2 de
> l'assistant) : le tableau panier à 6 colonnes, illisible dans la colonne
> étroite (défilement horizontal), est remplacé par une **liste de lignes en
> cartes** (code + désignation, puis unité / PU HT / quantité / total) ; le bloc
> Plafond devient une **carte compacte** (jauge + 2 valeurs principales « Reste
> disponible » et « Cette commande » + 2 secondaires « Plafond » et
> « Consommé ») ; les **totaux (HT/TVA/TTC) et les actions** (« Vider »,
> « Vérifier la commande ») migrent dans une **barre collante** en bas d'écran,
> toujours visible ; la barre d'étapes est allégée (pastilles) et les styles
> inline de l'étape 2 sont remplacés par des classes (`.stack`, `.flex-tight`,
> `.field-qty`, `.cart-list`, `.action-bar`, `.budget-figures`). Aucun `id`/
> attribut lu par `document.js`, aucun libellé ni assertion du test de fumée
> n'a changé (**136/136** toujours vert ; `pyflakes`/`compileall`/`node --check`
> propres).
>
> Puis **défilement du panier** : `.cart-list` passe d'une liste infinie à une
> **zone bornée** (`max-height: min(48vh, 440px)` + `overflow-y: auto`), comme le
> catalogue (`.results`, 335 px) — avant, avec beaucoup d'articles la colonne
> s'allongeait indéfiniment et la ligne fraîchement ajoutée apparaissait **derrière
> la barre collante**, donc invisible. `flashLine(index)` (appelée **uniquement**
> depuis `addArticle()`, jamais depuis `renderCart()`, pour ne pas provoquer de
> déplacement parasite lors d'un retrait/vidage/erreur) amène la ligne avec
> `scrollIntoView({block:"nearest"})` et l'illumine 1,2 s (`.cart-line.is-new` +
> `@keyframes cart-flash`). `.cart-line { scroll-margin-bottom: 96px }` compense la
> barre collante.
>
> **Correctifs ultérieurs** : `.steps li { flex: 0 0 auto }` à ≤900 px (en
> `flex-direction: column`, `flex: 1 1 150px` s'appliquait à la **hauteur** →
> barre d'étapes de ~460 px) ; `@media print` déplie désormais `.cart-list` et
> `.results` (`max-height: none`) et remet `.action-bar` en `static` (sinon le
> panier était rogné au PDF) ; les 2 derniers styles inline des étapes 1 et 3 sont
> remplacés par `.stack`. Toutes ces classes sont **confinées à
> `document_form.html`** ; `.budget-rows` (partagé avec `dashboard.html` et
> `convention_detail.html`) est inchangé.
>
> **Le dépôt est versionné** (`git init`, branche `main`, 7 commits, `.gitignore`
> excluant `web_app.db`, `.session.key`, `uploads/`, `documents_pdf/`, `wheels/`).
> Voir `AGENT.md` : **un commit par grand changement**.

---

## 1. Objectif
Réimplémenter en web l'application de bureau *Gestion Articles — Conventions & Commandes*
(dépôt `C:\Users\FERDJANI\Desktop\convention`) dans le sous-dossier `web-app/`.

Contraintes validées avec l'utilisateur :

- **Flask + Jinja + CSS/JS locaux** (aucun CDN, aucun build npm) ;
- **100 % hors-ligne**, **monoposte** : serveur sur `127.0.0.1:8765` ;
- **aucun mot de passe** ni compte (l'accès est physique) ;
- base **dédiée** `web_app.db`, créée vide puis peuplée par import de
  `source_listes.xlsx` (pas de migration des données du poste de bureau) ;
- documents produits dans `documents_pdf/web/` (PDF + Excel).

Phases 1 → 7 (structure/DB, layout/dashboard, saisie document, historique/édition,
conventions/imports, rapports/paramètres, sécurité/tests/README) : **terminées**.

## 2. Stack & environnement
- Python **3.11** (`C:\Program Files\Python311\python.exe`) — Flask 3.1.3,
  Werkzeug, Jinja2, openpyxl 3.1.5, **reportlab 4.4.2**, itsdangerous,
  **pyflakes**, **node**. (`run.bat` cherche aussi `C:\Python314\python.exe`,
  puis `python` du PATH, puis `py -3`.)
- Les wheels livrées dans `wheels/` installent **reportlab 5.0.1** (pypi) : le
  smoke test est vert avec les deux versions (4.4.2 système, 5.0.1 isolée).
- **Non installés / à ne pas utiliser** : `waitress`, `pytest`
  (les tests passent par `flask.test_client()`).

## 3. Arborescence (fichiers clés)
```
web-app/
├─ run.bat              # LANCEUR (CRLF obligatoires, ASCII sans BOM) — wheels d'abord
├─ serve.py             # port libre sur 20 essais + --open ; refus de tout hôte ≠ local
├─ requirements.txt  README.md  LISEZ-MOI.txt  .gitignore
├─ fabriquer_archive.ps1 # → ..\GestionArticles-v2.0.zip (hors dépôt)
├─ source_listes.xlsx   # classeur graine embarqué dans l'archive
├─ wheels/              # paquets hors-ligne Python 3.10→3.14 win_amd64 (39 Mo, hors git)
├─ web_app.db           # base SQLite (393 articles importés)
├─ .session.key         # clé de session locale
├─ app/
│  ├─ __init__.py       # create_app(), filtres Jinja, globals, handlers erreurs, CLI
│  ├─ config.py         # chemins, TVA_RATE=0.19, seuils, 5 THEMES, HOST/PORT
│  ├─ security.py       # CSRF, en-têtes, safe_export_path, filename_safe
│  ├─ database.py       # ~1475 l. : schéma, règles métier, contrôles
│  ├─ importer.py       # lecture/écriture .xlsx (zipfile + XML, pas openpyxl en lecture)
│  ├─ utils.py          # parse_price/quantity, compute_totals, format_*
│  ├─ routes/           # api, conventions, dashboard, documents, files, history,
│  │                    #        reports, settings
│  ├─ services/documents.py  # create/update_document, free_number, exports
│  ├─ reports/          # pdf.py, excel.py, annual.py (copiés de l'édition bureau)
│  │                    #        + docx.py (remplissage des formulaires Model/)
│  ├─ templates/        # base, dashboard, document_form, document_detail, history,
│  │                    #          conventions, import_preview, reports, settings,
│  │                    #          error, _icons, _form_dialog
│  └─ static/           # css/{themes,app}.css, js/{theme,app,document,history,
│                       #        conventions,import_preview,reports,settings,
│                       #        form_dialog}.js, img/favicon.svg
├─ Model/               # 3 modèles Word des formulaires (LECTURE SEULE)
├─ tests/smoke_test.py  # 136 vérifications, exécutées dans un dossier temporaire
└─ tools/gen_themes.py  # régénère static/css/themes.css
```

## 4. Règles métier (à préserver)
- **Prix figés** : le prix est toujours relu en base ; écart > 0.0001 → `ConflitPrix`
  → dialogue « les prix ont changé » + `accept_new_prices`.
- **Numérotation** `PRÉFIXE-EXERCICE-0001` via `free_number()` (libre en base **et**
  sur disque, avec incrément).
- **Plafond** : blocage si `consommé + document >= plafond` (égalité incluse) ;
  message écrit **une seule fois** (`Database._assert_within_plafond`).
- **Un seul exercice actif** par convention ; la clôture archive
  `consumed_at_close` / `remaining_at_close`.
- **Convention fermée ou expirée** → refus côté base (`_validate_category_open`,
  `effective_status`).
- **Totaux** : HT = somme des totaux de ligne **arrondis** (garantit la cohérence
  affichage / PDF / Excel) ; TVA 19 %.
- **Séquence d'écriture** : `preview_document` (validation, zéro écriture) →
  génération en `.tmp` → remplacement → base en une transaction ; en cas d'échec,
  suppression des nouveaux fichiers (création) ou restauration des `.bak`
  (modification) — jamais de divergence fichier / base.

## 5. Points d'implémentation importants (pièges connus)
1. **Attributs sur dictionnaires dans Jinja** : `dict.x` fonctionne, **sauf si `x`
   est une méthode** (`items`, `values`, `get`…). Écrire `preview["items"]`.
2. **CSP stricte** (`script-src 'self'`) : **interdits** — `onclick=`, `onchange=`,
   `href="javascript:…"`, `<script>` inline, tout CDN. Passer par un fichier JS
   local. Les styles inline (`style="…"`) sont tolérés (`style-src 'unsafe-inline'`).
3. **`sqlite3.Row`** : pas d'attributs ; Jinja retombe sur `row["col"]` — mais
   `row.items` casserait (cf. point 1).
4. **Chemins figés à l'import** : `services/documents.py` fait
   `from app.config import EXPORT_DIR` ; les tests doivent patcher `cfg.EXPORT_DIR`
   **et** `documents_service.EXPORT_DIR/TMP_DIR`.
5. **`run.bat`** : fins de ligne **CRLF** + ASCII sans BOM. Une parenthèse `)`
   dans un `echo` placé dans un bloc `if ( … )` ferme le bloc (bug déjà rencontré
   et corrigé).
6. **Console Windows cp1252** : `serve.py` et `tests/smoke_test.py` forcent
   `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` ; ne pas afficher
   `→` ailleurs.
7. **Shell de travail = PowerShell** : pas d'heredoc `<<` ; préférer les outils
   `write`/`edit` aux cmdlets de contenu.
8. **`.docx` (formulaires `Model/`)** : `ElementTree` omet les déclarations
   `xmlns:*` inutilisées alors que `mc:Ignorable` les référence → Word refuserait
   le fichier ; `app/reports/docx.py::_serialize` les réinjecte (ne pas retirer
   ce contrôle). Les noms de modèles contiennent espaces et `’` : ils sont
   résolus par glob (`2-*.docx`), jamais écrits en dur. Les `.docx` produits
   portent `w14:paraId` supprimés sur les lignes clonées (sinon doublons).
9. **Pagination des formulaires** : les 3 modèles sont normalisés à
   `LINES_PER_PAGE = 10` lignes (`_normalize` : le 2 perd 3 lignes vierges, le 3
   en gagne 3 — d'où `_renumber`). Le tableau du modèle est **flottant**
   (`w:tblpPr`, ancré au texte) : copié tel quel après un saut de page, il
   remonterait en fin de page précédente → `_clone_table` retire `w:tblpPr` et
   pose `<w:jc w:val="center"/>` (même position horizontale, **ordre du schéma :
   avant `w:tblCellMar`, jamais après**). Les pages 2+ sont clonées **avant**
   tout remplissage, la mention « Page x/y » est une copie formatée du
   paragraphe `N°` insérée dans la même cellule, et les éléments qui suivent le
   tableau (note (1)/(2) du modèle 2, paragraphe vide) ne sont repris que sur la
   page 1.

## 6. Sécurité
- **CSRF** sur **toutes** mutations (meta `csrf-token` + en-tête `X-CSRF-Token`
  ou champ `csrf_token` du body).
- En-têtes : CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`,
  `Permissions-Policy`, `COOP`.
- Cookie de session HttpOnly / SameSite=Lax ; clé dans `.session.key` local.
- Téléchargements uniquement via `/files/<id>/<kind>` avec `safe_export_path`
  (chemins **relatifs** en base, refus de `..`, des absolus et des traversées).
- `serve.py` refuse tout hôte non local ; `debug=False` par défaut.

## 7. Commandes de vérification
```bat
python -m pyflakes app serve.py tests      :: propre
python -m compileall -q app serve.py tests
node --check app\static\js\*.js             :: 9 fichiers OK
python tests\smoke_test.py                 :: 136/136
python serve.py                            :: http://127.0.0.1:8765 (sinon port suivant)

:: versionnement (voir AGENT.md : un commit par grand changement)
git status --short                         :: arbre propre avant/après
git --no-pager log --oneline -7            :: historique
git add -A && git commit -m "feat(portee): description impérative"

:: distribution hors-ligne
python -m pip download -r requirements.txt -d wheels --only-binary=:all: ^
      --platform win_amd64 --implementation cp --python-version 3.11   (x 3.10/3.12/3.13/3.14)
powershell -ExecutionPolicy Bypass -File fabriquer_archive.ps1         :: ..\GestionArticles-v2.0.zip
```
Le test de fumée couvre : pages, en-têtes de sécurité, refus CSRF, API
articles/budget/prévisualisation, création (PDF + Excel réellement produits),
téléchargements, anti-traversée de chemin, blocage de plafond (409), modification,
clôture d'exercice, rapports, sauvegarde, modèle vierge, import Excel indexé,
suppressions, formulaires conventions, **formulaires Word** (3 `.docx` produits,
champs saisis et défauts `app_meta`, libellés de boutons, normalisation à
10 lignes, pagination multipage : 2 tableaux, 1 saut de page, « Page 1/2 » et
« Page 2/2 », note (1)/(2) sur la page 1, aucun `paraId` dupliqué ajouté).

## 8. État & points non validés
- **Validé** : `pyflakes` / `compileall` / `node --check` propres, smoke test
  136/136, serveur réel répondant 200 sur `/`, `/conventions`, `/settings`,
  fiche commande et téléchargement des 3 formulaires Word (200 + mimetype docx),
  `run.bat` exécuté sans erreur (code 0).
- **Validé (installation à froid)** : archive `GestionArticles-v2.0.zip`
  (39 Mo) extraite dans un dossier vierge → `pip install --no-index --find-links
  wheels` sans réseau, `flask init-db` + `import-seed` (393 articles),
  smoke 136/136 dans la copie, `serve.py` passant automatiquement du port 8765
  occupé au 8766, puis `run.bat` complet (détection Python → base → serveur).
  **Non testé** : une machine sans Python préalablement installé (le message
  d'erreur a été relu, pas exécuté).
- **Non validé visuellement** : aucun navigateur ni Playwright n'est disponible
  → le rendu, les dialogues `<dialog>` (dont celui des formulaires), la grille de
  thèmes, le pré-remplissage de `conventions.js` (édition d'exercice) et la
  navigation clavier du catalogue **n'ont pas été testés à l'écran**. À vérifier
  en priorité en cas de reprise. Porte aussi, depuis la refonte : le
  **défilement interne du panier** (ajouter 15–20 articles → ascenseur + ligne
  amenée et surlignée), la **barre d'étapes à ≤900 px** (doit rester ~45 px par
  pastille, non ~150 px), la **barre collante** de l'étape 2, et un **`Ctrl+P`**
  de l'étape 2 (panier intégral, barre d'actions dans le flux).
- **Non validé dans Word** : le remplissage des `.docx` est vérifié
  structurellement (zip valide, XML bien formé, espaces de nom et `mc:Ignorable`
  préservés, 10 lignes normalisées, pagination 2 pages + saut de page, lignes
  clonées, zones signature intactes) mais **l'ouverture réelle des fichiers dans
  Word/LibreOffice n'a pas pu être automatisée** sur ce poste → ouvrir un
  formulaire de chaque type, dont au moins un à **2 pages** (commande de plus de
  10 articles) : vérifier en particulier l'alignement vertical de la page 2
  (tableau centré en flux) et la position de la ligne « Page x/y ».
- Rappel de cohérence : en mode **édition**, ré-enregistrer un document dont le
  total atteint exactement le plafond est refusé (comportement identique à
  l'édition bureau).
- `init_schema()` crée toujours deux conventions par défaut (`Informatique`,
  `Bureautique`) ; le bouton « Importer source_listes.xlsx » de l'écran
  Conventions n'apparaît que si `article_count() == 0`.
