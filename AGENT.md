# AGENT.md — Consignes de travail

> Fichier destiné aux **agents IA** (Cline, Claude Code, Copilot…) **et** aux
> contributeurs humains. Il décrit comment travailler sur ce dépôt sans le casser.

---

## 1. Le projet

**Gestion-convention** — application **Flask** (Python 3) de gestion de
conventions, de commandes et de budgets.
Front-end **sans build** : HTML (Jinja2) + CSS + **JavaScript en `<script>` natif**
(lignes `var` / `function`, **pas** d'import, **pas** de modules ES, **pas** de
CDN ni de npm). Tout est servi en local depuis `app/static/`.

- Routes : `app/routes/*.py` (assistant de commande : `app/routes/documents.py`)
- Templates : `app/templates/*.html`
- Styles : `app/static/css/app.css` + `themes.css` (jetons de design)
- JS par page : `app/static/js/document.js`, `conventions.js`, `reports.js`…
- Tests : `tests/smoke_test.py`

---

## 2. ⚠️ RÈGLE PRINCIPALE — **un commit par grand changement**

**Oui, c'est demandé, et c'est obligatoire.**

> **À chaque « grand changement », créez un commit dédié — immédiatement.**
> Un *grand changement* = une unité de sens cohérente, par exemple :
> - une **nouvelle fonctionnalité** (ex. le défilement du panier) ;
> - une **refonte / amélioration d'interface** (ex. l'étape 2 de l'assistant) ;
> - un **correctif** d'un bug observable ;
> - un **ajout de test** ou de documentation significatif.

### Pourquoi
Git n'enregistre **pas la date** des modifications : il photographie l'état des
fichiers **au moment du commit**. Si vous attendez, tout se **fond en un seul
commit géant** : impossible de savoir quelle modification a introduit un bug, ou
de revenir en arrière sur un seul sujet.

### Comment faire
```bash
# 1. vérifier AVANT de commiter
node --check app/static/js/*.js
python -m pyflakes app serve.py tests
python tests/smoke_test.py

# 2. commiter SANS ATTENDRE, avec un message explicite
git add -A
git commit -m "feat(panier): défilement interne + surbrillance de la ligne ajoutée"
```

### Règles associées
1. **Ne mélangez jamais** deux sujets différents dans un même commit.
2. **Ne committez jamais de code cassé** : si les tests échouent, corrigez d'abord.
3. **`git add -A` est obligatoire** : sinon les **nouveaux fichiers** restent
   invisibles pour Git (erreur classique).
4. **Avant de commencer** une tâche : `git status` pour partir d'un arbre propre.
5. **Après chaque commit** : relancer le smoke test pour confirmer qu'aucune
   régression n'a été introduite.

---

## 3. Message de commit (Conventional Commits, en français)

```
<type>(<portée>): <description impérative courte>

<corps : le POURQUOI, pas le quoi>

<impact / vérifications effectuées>
```

| Type | Usage | Exemple |
| --- | --- | --- |
| `feat` | nouvelle fonctionnalité | `feat(panier): défilement interne du panier` |
| `fix` | correction de bug | `fix(budget): la jauge ne dépasse plus le plafond` |
| `refactor` | restructuration sans changement de comportement | `refactor(wizard): étape 2 en cartes` |
| `style` | mise en forme CSS uniquement | `style(steps): pastilles plus légères` |
| `docs` | documentation | `docs: mise à jour de CONTEXTE.md` |
| `test` | tests | `test: ajoute un contrôle du panier` |
| `chore` | outillage, CI, .gitignore | `chore: ignore wheels/ et web_app.db` |

- Première ligne **≤ 72 caractères**, en **français**, à l'**impératif**.
- Le corps explique le **« pourquoi »** : le code montre déjà le « quoi ».
- Le corps peut lister les **vérifications passées** (ex. `smoke 136/136`).

---

## 4. Vérifications obligatoires avant chaque commit

```bash
node --check app/static/js/*.js          # syntaxe des 9 fichiers JS
python -m pyflakes app serve.py tests    # lint Python (attendu : exit 0)
python -m compileall -q app serve.py tests
python tests/smoke_test.py               # attendu : 136 vérifications, 0 échec
```

Le smoke test vérifie la présence d'`id`, d'`aria-label` et d'`href` précis dans
les templates. **Ne les renommez pas** sans mettre le test à jour **dans le même
commit**.

---

## 5. Pièges à connaître

### `document_form.html` ↔ `document.js` sont couplés
`document.js` cible les éléments **par `id`**. Renommer un `id` dans le template
**casse silencieusement** le JS : la page se charge, mais ne réagit plus.
À vérifier avant/après toute modification : `budget-state`, `budget-gauge`,
`b-plafond`, `b-consumed`, `b-document`, `b-remaining`, `budget-notice`,
`budget-rows`, `cart-body`, `t-ht`, `t-tva`, `t-ttc`, `save-btn`, `clear-btn`,
`back-to-1`, `save-hint`, `step1`…`step3`, `convention`.

### `renderCart()` ne doit pas déclencher de défilement
Les actions de repli (retrait d'une ligne, vidage du panier, erreur de preview)
appellent toutes `renderCart()`. Toute mise en lumière ou tout défilement se
place donc **à l'extérieur**, dans la fonction d'ajout uniquement (`flashLine()`).

### `.budget-rows` / `.budget-row` sont partagés
Ils servent aussi à `dashboard.html` et `convention_detail.html` : **ne pas
supprimer** ni restreindre leur portée sans vérifier ces deux pages.

### `.panel { overflow: hidden }`
Tout élément `position: sticky` doit être placé **hors** de `.panel`, sinon il est
neutralisé. C'est pour cela que `.action-bar` vit **à côté** de `.doc-grid`.

### Aucune dépendance externe
Interdit d'ajouter un CDN, un package npm ou un import ES : l'application doit
fonctionner **hors-ligne**, en fichiers locaux uniquement.

---

## 6. Ne jamais commiter

`.gitignore` exclut déjà ces éléments — **ne les retirez pas** :

```
web_app.db          # base de données (données réelles)
.session.key        # SECRET
uploads/            # imports temporaires
documents_pdf/      # documents générés
wheels/             # 38 Mo de wheels pip hors-ligne
__pycache__/  .venv/  smoke_*.txt
```

Vérification : `git status --ignored`.

---

## 7. Historique du dépôt

| Commit | Objet |
| --- | --- |
| `3edec54` | initialisation du dépôt + refonte de l'étape 2 (Variante A) |
| `0f8f09a` | défilement interne du panier + surbrillance de la ligne ajoutée |
| *ce commit* | ajout de `AGENT.md` (consignes de travail) |

Dépôt **local uniquement** (pas de remote). Pour pousser un jour :
```bash
git remote add origin <url>
git push -u origin main
```

