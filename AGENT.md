# AGENT.md — Manuel de travail du projet *Gestion Articles*

> **À tous les agents IA et contributeurs humains.** Lisez ce fichier **avant**
> toute modification. Il décrit l'architecture, le métier, les pièges et le
> processus de validation de **ce dépôt précisément** — pas des généralités.
>
> Documents compagnons : [`CONTEXTE.md`](CONTEXTE.md) (narratif & *pourquoi*),
> [`INDEX.md`](INDEX.md) (carte technique), [`README.md`](README.md) (utilisateur).

---

## 0. Le rôle de ce fichier

Un `AGENT.md` est la **mémoire de travail** d'un projet. Son objectif : rendre
un nouveau contributeur — humain ou IA — **autonome en quelques minutes**, et
l'**empêcher de réintroduire des bugs déjà corrigés**.

| Objectif | Oui, mais concrètement |
| --- | --- |
| **Comprendre vite** | §1 fiche d'identité · §2 architecture · §3 carte du code |
| **Ne pas casser le métier** | §4 règles métier invariants |
| **Ne pas retomber dans un piège connu** | §6 pièges & garde-fous |
| **Savoir si le travail est fini** | §5 workflow + §7 vérifications |
| **Livrer sans dette technique** | §5.2 un commit par grand changement |

> ⚠️ **Ce fichier n'est pas décoratif.** Chaque règle correspond à un problème
> **réellement rencontré**. Si une règle vous semble **fausse ou obsolète**,
> **corrigez `AGENT.md` dans le même commit** que la correction.

---

## 1. Fiche d'identité

| Élément | Valeur |
| --- | --- |
| Nom | **Gestion Articles** — *Conventions & commandes — édition web* |
| Version | `2.0-web` (`app/config.py` → `VERSION`) |
| Nature | Application **Flask** **monoposte**, **100 % hors-ligne** |
| Racine | `D:\Gestion_convetion` |
| Python | **3.10 → 3.14** (développement sous 3.14.3) |
| Dépendances | `Flask`, `Jinja2`, `Werkzeug`, `itsdangerous`, `openpyxl`, `reportlab` |
| Base | **SQLite** `web_app.db`, schéma `version 1` |
| Serveur | `http://127.0.0.1:8765` (port suivant libre, `PORT_SEARCH_LIMIT = 20`) |
| Sorties | `documents_pdf/web/` (PDF + Excel) |
| Tests | `tests/smoke_test.py` → **136 vérifications** (732 lignes) |
| Git | branche **`main`**, auteur `ferdjani <rhprojetm32@gmail.com>` |

**Contrainte fondamentale : aucun CDN, aucun npm, aucun build, aucun service
externe.** L'application doit tourner sur un poste **sans internet**. Toute
dépendance ajoutée doit pouvoir être embarquée dans `wheels/`.

---

## 2. Architecture

### 2.1 Les couches

```
Navigateur
   │   HTML (Jinja2)  +  CSS local  +  JS natif en <script>
   ▼
app/routes/*.py            Blueprints : HTTP, validation, CSRF, rendu
   ▼
app/services/documents.py  Orchestration : PDF/Excel, fichiers, transaction
   ▼
app/database.py            Classe Database : SQL + règles métier + exceptions
   ▼
web_app.db (SQLite)
```

**Règle de dépendance :** une couche n'appelle jamais vers le haut.
`routes` → `services` → `database`. `database` **n'importe jamais** `routes`.

### 2.2 Cycle d'une requête

```
requête entrante
  → install_security() : _check_csrf()      # 400 si jeton absent/faux (POST)
  → Blueprint (@blueprint.get / @blueprint.post)
  → get_db() → current_app.extensions["db"]
  → Database.*   peut lever PlafondAtteint / ConflitPrix / ArticlesManquants /
                 ExerciceManquant / ValueError
  → _business_error() convertit l'exception en 409 JSON ou 400 HTML
  → _security_headers() : CSP + X-Frame-Options + nosniff + Referrer-Policy
```

`get_db()` (dans `app/__init__.py`) est le **seul** moyen d'accéder à la base :

```python
from app import get_db
db = get_db()
```

### 2.3 Les 8 blueprints

| Blueprint | Fichier | Rôle |
| --- | --- | --- |
| `dashboard` | `routes/dashboard.py` | `/` tableau de bord segmenté |
| `documents` | `routes/documents.py` | assistant 3 étapes, création, édition, export |
| `history` | `routes/history.py` | `/history` historique paginé |
| `conventions` | `routes/conventions.py` | conventions, exercices, import Excel |
| `reports` | `routes/reports.py` | rapports annuel & année civile |
| `settings` | `routes/settings.py` | défauts de formulaires, sauvegarde base |
| `files` | `routes/files.py` | `/files/<id>/<kind>` téléchargement |
| `api` | `routes/api.py` | JSON `/api` : preview, articles, budget, exercices |

### 2.4 Tables et vocabulaire

Tables : `categories` · `exercices` · `articles` · `documents` ·
`document_items` · `app_meta`.

| Terme | Signification |
| --- | --- |
| **Convention** | une *catégorie* (`Informatique`, `Bureautique` par défaut) |
| **Exercice** | période budgétaire **d'une** convention, avec un **plafond** |
| **Commande** | un enregistrement `documents` + ses lignes `document_items` |

Ne jamais traduire ces termes : ils sont dans l'UI, la base **et** les tests.

### 2.5 Passerelle HTML ↔ JS

Chaque template charge **un seul** JS dédié (§3.4). Trois mécanismes relient
les deux mondes — **aucun ne doit être renommé sans mise à jour simultanée** :

1. **`data-*` sur `#document-app`** → objet `CFG` (`data-preview-url`,
   `data-articles-url`, `data-budget-url`, `data-csrf`, `data-category`…) ;
2. **`id`** ciblés par `$(...)` → mise à jour ciblée du DOM ;
3. **`data-*` sélecteurs** (`data-step-nav`, `data-step-panel`, `data-add`,
   `data-remove`, `data-qty`, `data-index`, `data-line-total`) → délégation
   d'événements (`closest(...)`).

---

## 3. Carte du code — « je veux modifier X → je touche Y »

### 3.1 Python

| Je veux… | Fichier |
| --- | --- |
| changer un seuil, la TVA, les thèmes, les ports | `app/config.py` |
| ajouter/modifier une règle métier, une table, du SQL | `app/database.py` (65 Ko — **le cœur**) |
| modifier une route ou une réponse HTTP | `app/routes/<domaine>.py` |
| modifier la génération PDF/Excel/fichiers | `app/services/documents.py` |
| modifier un rapport ou un formulaire Word | `app/reports/{pdf,excel,docx,annual}.py` |
| modifier la sécurité (CSRF, CSP, en-têtes) | `app/security.py` |
| modifier le format monétaire / dates / totaux | `app/utils.py` |
| modifier l'import `source_listes.xlsx` | `app/importer.py` |
| ajouter une commande CLI Flask | `app/__init__.py` → `_register_commands` |

### 3.2 Front

| Je veux… | Fichier |
| --- | --- |
| changer une couleur / un thème | `app/config.py` → `THEMES` **puis** `python tools/gen_themes.py` |
| changer une règle visuelle globale | `app/static/css/app.css` (1025 lignes) |
| changer le squelette de page | `app/templates/base.html` |
| changer l'assistant de commande | `document_form.html` + `static/js/document.js` |
| ajouter une icône | `app/templates/_icons.html` (macro `icon(name, cls)`) |

### 3.3 Structure

```
app/            Fabrique create_app(), config, database, security, utils, importer
├── routes/     8 blueprints (HTTP)
├── services/   documents.py (fichiers, transaction)
├── reports/    pdf.py · excel.py · docx.py · annual.py
├── static/     css/  js/  img/     ← aucun build, servis tels quels
└── templates/  Jinja2 (13 fichiers)
tests/          smoke_test.py       ← 136 vérifications
tools/          gen_themes.py       ← régénère themes.css
Model/          3 modèles .docx     ← LECTURE SEULE, jamais modifiés
wheels/         wheels pip (38 Mo, ignorés par Git)
```

### 3.4 Quel JS pour quel template ?

| Template | Script |
| --- | --- |
| `base.html` | `theme.js`, `app.js` (partagés) |
| `document_form.html` | **`document.js`** (27,9 Ko — le plus gros) |
| `conventions.html` | `conventions.js` |
| `history.html`, `document_detail.html` | `history.js`, `form_dialog.js` |
| `import_preview.html` | `import_preview.js` |
| `reports.html` / `settings.html` | `reports.js` / `settings.js` |

**Helpers globaux définis dans `app.js`** (disponibles partout) :
`window.gaFetch(url, opts)` · `window.toast(msg, type)` · `window.refreshCsrf()`
· `readCsrf()` · `window.GATheme`.

---

## 4. Règles métier — **invariants, ne jamais modifier**

Vérifiées par le smoke test. Les changer casse le produit.

| # | Règle | Valeur | Où |
| --- | --- | --- | --- |
| 1 | **TVA** | **19 %** | `config.TVA_RATE = 0.19` |
| 2 | Alerte budgétaire | **80 %** du plafond | `config.BUDGET_WARN` |
| 3 | Critique budgétaire | **90 %** | `config.BUDGET_CRITICAL` |
| 4 | **Blocage ferme** | `consommé + commande >= plafond` → **refus** | `BUDGET_BLOCK = 1.0` |
| 5 | Convention **sans exercice actif** | **aucune commande possible** | `ExerciceManquant` |
| 6 | Prix modifié depuis l'import | **dialogue obligatoire** « Les prix ont changé » | `ConflitPrix` |
| 7 | Article supprimé du catalogue | ligne retirée, jamais de crash | `ArticlesManquants` |
| 8 | Numérotation | `INF-2026-2027-0001`, **jamais réutilisée** | `next_document_number` |
| 9 | Convention **figée** en édition | interdit de changer | `update_document` |
| 10 | Édition d'une commande **clôturée** | refusée | `document_editable` |

### 4.1 Exceptions métier → code HTTP

```python
from app.database import (PlafondAtteint, ConflitPrix,
                          ArticlesManquants, ExerciceManquant)
```

Toutes héritent de `ValueError` et sont converties **automatiquement** :

| Exception | Réponse |
| --- | --- |
| `PlafondAtteint` | **409** `type:"budget_block"` |
| `ConflitPrix` | **409** `type:"price_conflict"` + `conflicts[]` |
| `ArticlesManquants` | **409** `type:"missing_articles"` + `missing[]` |
| `ExerciceManquant` | **409** `type:"missing_exercice"` + `category` |
| `ValueError` | 409 générique |

**Il suffit de `raise`** : ne renvoyez jamais un `jsonify(409)` à la main, sinon
`document.js` perdra le `type` qu'il attend.


---

## 5. Workflow de travail

### 5.1 Boucle obligatoire

```bat
:: 1. avant de commencer — partir d'un arbre propre
git status --short

:: 2. après chaque modification
node --check app\static\js\*.js
python -m pyflakes app serve.py tests
python -m compileall -q app serve.py tests
python tests\smoke_test.py

:: 3. après chaque commit — confirmer qu'aucune régression n'est née
python tests\smoke_test.py
```

**On ne committe jamais de code cassé.** Si le smoke test échoue, corrigez
d'abord.

### 5.2 ⚠️ Un commit par grand changement

> **À chaque « grand changement », créez un commit dédié — immédiatement.**
> Un grand changement = une unité de sens cohérente : une fonctionnalité, une
> refonte d'interface, un correctif, un ajout de test ou de doc significatif.

**Pourquoi.** Git ne date pas les modifications : il photographie l'état des
fichiers **au moment du commit**. Si vous attendez la fin de la session, tout se
fond en un commit géant — impossible de savoir quel changement a introduit un
bug, ou de revenir en arrière sur un seul sujet.

```bat
git add -A
git commit -m "feat(panier): défilement interne + surbrillance de la ligne ajoutée"
```

### 5.3 Message de commit (Conventional Commits, en français)

```
<type>(<portée>): <description impérative courte>

<corps : le POURQUOI, pas le quoi>

<impact / vérifications effectuées>
```

| Type | Usage | Exemple |
| --- | --- | --- |
| `feat` | nouvelle fonctionnalité | `feat(panier): défilement interne` |
| `fix` | correction de bug | `fix(budget): jauge hors plafond` |
| `refactor` | sans changement de comportement | `refactor(wizard): étape 2 en cartes` |
| `style` | CSS uniquement | `style(steps): pastilles plus légères` |
| `docs` | documentation | `docs: mise à jour de CONTEXTE.md` |
| `test` | tests | `test: contrôle du panier` |
| `chore` | outillage, `.gitignore` | `chore: ignore wheels/` |

Première ligne **≤ 72 caractères**, en **français**, à l'**impératif**.
Le corps explique le **pourquoi** et liste les **vérifications passées**.

### 5.4 Règles associées

1. **Ne jamais mélanger deux sujets** dans un même commit.
2. **`git add -A` est obligatoire** — sinon les *nouveaux* fichiers restent
   invisibles pour Git (erreur n°1).
3. **Ne jamais recopier un SHA** dans de la documentation : il devient obsolète
   dès la première réécriture d'historique. `git log --oneline` est la source
   de vérité.
4. Après `git rebase` / `--amend`, **revérifiez** les empreintes citées.


---

## 6. Pièges & garde-fous

> **Chaque item = un problème réellement rencontré.** Lisez-les avant de toucher
> au code correspondant.

### 6.1 🔒 La CSP et le hash du script inline

`app/security.py` impose une **Content-Security-Policy** stricte :

```
script-src 'self' 'sha256-HfkPbVOIlmPS3ZQMeSlzI9WLkhDNqto9CCKGMYe84BA='
```

Le seul `<script>` inline toléré est celui de `base.html:10` (init du thème,
évite le *flash* blanc). **Si vous modifiez ce script, la CSP le bloque et le
smoke test échoue sur « hash CSP du script inline à jour ».**

Recalculer le hash après toute modification :

```python
# python -  à exécuter à la racine
import re, hashlib, base64, pathlib
html = pathlib.Path("app/templates/base.html").read_text(encoding="utf-8")
inline = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
print("sha256-" + base64.b64encode(
    hashlib.sha256(inline.encode("utf-8")).digest()).decode())
```

Coller le résultat dans `security_mod.THEME_INIT_HASH` **et** repasser le smoke
test (qui vérifie aussi que la valeur est bien présente dans l'en-tête CSP).

**Interdits** : `onclick=`, `onchange=`, `href="javascript:…"`, `<script>` non
autosigné, tout CDN. Les styles `style="…"` sont **tolérés**
(`style-src 'unsafe-inline'`).

### 6.2 🎨 `themes.css` est **généré**

`app/static/css/themes.css` porte le commentaire
*« Fichier généré — ne pas éditer à la main »*. Après avoir modifié `THEMES`
dans `app/config.py` :

```bat
python tools\gen_themes.py
```

Seuls **deux thèmes** existent : `clair` et `sombre`.

### 6.3 🛡️ CSRF

Toute requête **non-GET** exige un jeton. Trois canaux acceptés
(`app/security.py` → `_request_token`) :

| Canal | Usage |
| --- | --- |
| en-tête **`X-CSRF-Token`** | appels `fetch` |
| champ **`csrf_token`** | formulaires HTML classiques |
| champ JSON **`csrf_token`** | corps `application/json` |

Côté JS, **passez toujours par `window.gaFetch`** : il ajoute l'en-tête et
**réessaie automatiquement** une fois après `window.refreshCsrf()` si le serveur
répond `{"error":"csrf"}`. N'appelez jamais `fetch()` brut pour une mutation.

Jeton lisible via `readCsrf()`, `<meta name="csrf-token">`, `CFG.csrf`
(`data-csrf`) ou `currentCsrf()` dans `document.js`.

### 6.4 🐍 `sqlite3.Row` n'a pas d'attributs

```python
row["name"]   # ✅
row.name      # ❌ AttributeError
```

Jinja se comporte pareil : **écrivez `row["col"]`**. `row.items` échouerait
silencieusement car `items` est une *méthode* de `Row`.

### 6.5 🚫 Aucune dépendance externe, JS « style ES5 »

Mesuré sur `app/static/js/*.js` : **164 `var`**, **0 `const`**, **0 `let`**,
**0 `=>`**, **0 `import`**.

```js
// ✅ convention du projet
function renderCart() {
  var html = "";
  results.forEach(function (a, index) { /* ... */ });
}
// ❌ interdit : const / let / fléchés / import / export / classes / npm
```

Aucun CDN, aucun `package.json`, aucun bundler. Vérifiez aussi que
`node --check` passe sur les 9 fichiers.

### 6.6 🔗 `document_form.html` ↔ `document.js` sont couplés

Renommer un `id` casse le JS **silencieusement** : la page se charge, mais ne
réagit plus. À vérifier avant/après :

```
budget-state  budget-gauge  budget-notice  budget-rows
b-plafond  b-consumed  b-document  b-remaining
cart-body   t-ht  t-tva  t-ttc
save-btn  clear-btn  back-to-1  back-to-2  save-hint  form-notice
step1…step3  to-step2  confirm-btn  recap-body  recap-number
article-search  article-results  result-count  line-count  qty
price-dialog  price-body  price-accept  change-category  document-app
```

**Et les sélecteurs `data-*`** : `data-step-nav`, `data-step-panel`,
`data-add`, `data-remove`, `data-qty`, `data-index`, `data-line-total`.


### 6.7 📦 `renderCart()` ne doit **jamais** déclencher de défilement

`renderCart()` est rappelé par **toutes** les actions de repli : retrait d'une
ligne, vidage du panier, erreur de preview, échec d'enregistrement.

Toute mise en lumière ou tout déscroll se place donc **à l'extérieur**, dans la
fonction d'ajout uniquement :

```js
// ✅ addArticle()
renderCart();
flashLine(targetIndex);   // scroll + surbrillance

// ❌ dans renderCart() : provoquerait un saut parasite à chaque retrait
```

Vérification : `flashLine` doit apparaître **0 fois** dans `renderCart`.

### 6.8 📐 `position: sticky` meurt sous `overflow: hidden`

`.panel { overflow: hidden }` (app.css:446) **neutralise** tout descendant
`sticky`. C'est pour cela que `.action-bar` vit **à côté** de `.doc-grid`, pas
dedans.

Avant d'ajouter un élément collant, vérifiez **tous** les ancêtres :

| Élément | Règle | À vérifier |
| --- | --- | --- |
| `.action-bar` | `sticky; bottom: 0; z-index: 15` | aucun ancêtre en `overflow` |
| `.topbar` | `sticky; top: 0; z-index: 20` | `20 > 15` → pas de conflit |

### 6.9 📏 Zones à défilement interne : pensez à l'impression

`.cart-list` (`max-height: 440px`) et `.results` (`max-height: 335px`) sont
**rognés** à l'impression si on ne les déplie pas. `@media print` doit contenir :

```css
.cart-list, .results { max-height: none !important; overflow: visible !important; }
.action-bar { position: static !important; }
```

Toute **nouvelle** zone `overflow: auto` doit être ajoutée à cette règle.

### 6.10 🧩 `flex-direction` change le sens de `flex-basis`

Bug réel : `.steps li { flex: 1 1 150px }` + `@media (max-width: 900px) {
.steps { flex-direction: column } }` → l'axe principal devenant **vertical**,
`150px` s'appliquait à la **hauteur** : la barre d'étapes mesurait **~460 px**.

```css
@media (max-width: 900px) {
  .steps { flex-direction: column; }
  .steps li { flex: 0 0 auto; }   /* ← indispensable */
}
```

**Toujours** remettre `flex: 0 0 auto` sur un conteneur passé en `column`.

### 6.11 🧠 Classes CSS partagées — vérifier avant de modifier

| Classe | Utilisée par |
| --- | --- |
| `.budget-rows` / `.budget-row` | `document_form.html`, **`dashboard.html`**, **`convention_detail.html`** |
| `.steps`, `.result`, `.stack`, `.flex-tight`, `.field-qty`, `.action-bar`, `.budget-figures` | **`document_form.html` uniquement** |
| `.cart-line`, `.cart-line-head/foot`, `.cart-empty`, `.is-new` | **émises par `document.js`** (`renderCart()`), absentes du template |

`document_form.html` concentre les classes de la refonte : inutile de les
chercher ailleurs. En revanche, **`.budget-rows` est un piège** — il sert au
tableau de bord et à la fiche convention.

### 6.12 📁 Ne jamais modifier ni commiter

```
Model/*.docx              LECTURE SEULE — modèles Word sources
web_app.db                données réelles, jamais versionnées
.session.key              SECRET (clé de session, générée automatiquement)
uploads/  documents_pdf/  fichiers temporaires / générés
wheels/                   38 Mo de wheels pip (hors Git)
__pycache__/  .venv/  smoke_*.txt
```

Vérification : `git status --ignored`.

### 6.13 🔐 Chemins de fichiers : anti-traversée

Les chemins stockés en base sont résolus **uniquement** par
`safe_export_path(base, relative)` (`app/security.py`) qui refuse tout chemin
absolu, `drive` ou `..`. **N'ouvrez jamais** un chemin venant de la base sans
passer par elle. Les noms d'en-têtes passent par `filename_safe()`.

### 6.14 🗄️ Migration de base

`Database._migrate()` gère l'ajout de colonnes (`_column_exists`), et
`init_schema()` est **idempotent** : il conserve les données existantes.
Ajoutez une colonne par un `ALTER TABLE` conditionnel dans `_migrate()`, jamais
en recréant la table.


---

## 7. Vérifications

### 7.1 Commandes

```bat
python -m pyflakes app serve.py tests        :: lint Python     → attendu : exit 0
python -m compileall -q app serve.py tests   :: syntaxe Python  → attendu : exit 0
node --check app\static\js\*.js              :: syntaxe JS      → attendu : 9/9
python tests\smoke_test.py                   :: fonctionnel     → attendu : 136/136
python serve.py --open                       :: manuel          → http://127.0.0.1:8765
```

Vérifications « propres » attendues : **0 pyflake**, **0 échec smoke**,
**302/302 accolades CSS** équilibrées.

### 7.2 Ce que couvre le smoke test (136 checks)

Pages & rendu · en-têtes de sécurité (CSP, nosniff, X-Frame-Options) · **refus
CSRF** · API `articles`/`budget`/`preview` · création (**PDF + Excel
réellement produits**) · téléchargements · **anti-traversée de chemin** ·
**blocage de plafond → 409** · modification · clôture d'exercice · rapports ·
sauvegarde · modèle vierge · import Excel indexé · suppressions · formulaires
conventions · **formulaires Word** (3 `.docx` produits, champs saisis, défauts
`app_meta`, normalisation 10 lignes, pagination 2 pages, aucun `paraId`
dupliqué) · assistant 3 étapes · choix de convention en étape 1 · **hash CSP du
script inline à jour**.

### 7.3 Ajouter une vérification

```python
# dans tests/smoke_test.py, fonction main()
check(<condition bool>, "libellé explicite", détail_optionnel)
```

Le compteur `CHECKS` s'incrémente tout seul ; l'échec est collecté dans
`FAILURES`. **Un nouveau comportement = au moins un `check`.**

### 7.4 Contrôle visuel — **non automatisé**

Aucun navigateur ni Playwright n'est disponible sur ce poste. À vérifier
manuellement (`python serve.py --open`) :

- thème **clair** et **sombre** ; largeurs **1280 px** et **1440 px** ;
- assistant : étape 1 (radios `name="convention"`), étape 2 (**15–20 articles**
  → ascenseur du panier + ligne amenée et surlignée), étape 3 ;
- fenêtre **≤ 900 px** : barre d'étapes ≈ **45 px** par pastille (pas 150 px) ;
- **`Ctrl+P`** sur l'étape 2 : panier intégral, barre d'actions dans le flux ;
- dialogues `<dialog>` et navigation clavier du catalogue (↑ ↓ Entrée).

---

## 8. Interdits — en un coup d'œil

| ❌ Interdit | Pourquoi |
| --- | --- |
| Ajouter un CDN / npm / bundler / module ES | poste **sans internet**, CSP stricte |
| Modifier `Model/*.docx` | modèles sources en lecture seule |
| `fetch()` brut pour une mutation | perd le retry CSRF de `gaFetch` |
| Renommer un `id`/`data-*` lu par le JS | casse silencieusement la page |
| `row.col` sur un `sqlite3.Row` | `AttributeError` |
| Renvoyer un 409 JSON à la main | `document.js` perd le `type` attendu |
| Éditer `themes.css` à la main | fichier **généré** |
| Recopier un SHA dans la doc | obsolète après la moindre réécriture |
| Committer du code cassé | dette + historique illisible |
| Committer `web_app.db` / `.session.key` | données & secret |
| Mélanger deux sujets dans un commit | impossible à isoler en cas de bug |

---

## 9. Les documents du projet — qui dit quoi ?

| Fichier | Rôle | Public |
| --- | --- | --- |
| **`AGENT.md`** (ce fichier) | **Comment travailler ici** : architecture, pièges, validation | agent IA + dev |
| `CONTEXTE.md` | Le **narratif** : pourquoi telles décisions, historique, points ouverts | agent IA + dev |
| `INDEX.md` | Carte technique : fichiers, routes, schéma, état des données | dev |
| `README.md` | **Utilisateur final** : démarrage, `run.bat`, options | collègue |
| `LISEZ-MOI.txt` | Version texte du README (double-clic hors navigateur) | collègue |
| `git log --oneline` | **Source de vérité** de l'historique | tout le monde |

> En cas de contradiction **AGENT.md ↔ code**, **le code a raison** : corrigez
> `AGENT.md`. En cas de contradiction **CONTEXTE.md ↔ AGENT.md**, `CONTEXTE.md`
> explique le *pourquoi* historique, `AGENT.md` donne la *consigne* actuelle.

---

## 10. Historique

```bat
git --no-pager log --oneline
git status --short
```

**Ne recopiez jamais ces empreintes dans une documentation** : un `git rebase`,
un `--amend` ou un `reset` les rend tous invalides d'un coup (cela s'est déjà
produit ici).

### Références

- Dépôt **local uniquement**, branche `main`. Pour pousser :
  ```bash
  git remote add origin <url>
  git push -u origin main
  ```
- Python 3.10 → 3.14 · Flask 3 · SQLite · Jinja2 · reportlab · openpyxl

