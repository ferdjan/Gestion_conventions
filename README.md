# Gestion Articles — édition web

Équivalent web de l'application de bureau *Gestion Articles — Conventions & Commandes* :
même métier, même vocabulaire, interface moderne, **monoposte et 100 % hors-ligne**
(aucun CDN, aucun service externe, aucun compte).

- Serveur local uniquement : `http://127.0.0.1:8765`
- Base SQLite dédiée : `web_app.db`
- Commandes produites : `documents_pdf/web/` (PDF + Excel)
- Aucun mot de passe : l'accès est physique (la machine)

---

## 1. Démarrage rapide

Prérequis : **Python 3.10 à 3.14** (cocher *Add Python to PATH* à l'installation).
Les paquets nécessaires sont **embarqués dans `wheels/`** : `run.bat` les installe
**sans internet** (repli automatique sur `pip` en ligne si besoin).

```bat
run.bat
```

Le script détecte Python, installe les dépendances si besoin, crée la base au
premier lancement, importe `source_listes.xlsx` puis ouvre le navigateur sur
l'URL réellement servie.

Démarrage manuel équivalent :

```bat
python -m flask --app app init-db
python -m flask --app app import-seed
python serve.py
```

Options utiles :

```bat
python serve.py --port 8080      # autre port de départ
python serve.py --open           # ouvrir le navigateur sur l'URL réelle
python serve.py --dev            # rechargement automatique (développement)
```

`serve.py` refuse tout hôte autre que `127.0.0.1` / `localhost` / `::1`. Si le
port demandé est déjà pris, il essaie automatiquement les **20 ports suivants**
et l'ouverture du navigateur suit le port retenu.

### Partage avec un collègue

```bat
powershell -ExecutionPolicy Bypass -File fabriquer_archive.ps1
```

produit `..\GestionArticles-v2.0.zip` (~39 Mo) contenant le programme, les
modèles `Model/`, `source_listes.xlsx` et les paquets `wheels/`, **sans** les
données personnelles (`web_app.db`, `.session.key`, `documents_pdf/`,
`uploads/`, `__pycache__/`). Le collègue décompresse sur son disque dur et
double-clique `run.bat` : rien d'autre à installer (voir `LISEZ-MOI.txt`).
Chaque poste garde **sa propre base** : aucune donnée n'est partagée.

---

## 2. Ce que fait l'application

| Écran | Adresse | Rôle |
| --- | --- | --- |
| Tableau de bord | `/` | jauges de plafond par convention, alertes 80/90 %, raccourcis |
| Nouvelle commande | `/documents/new` | recherche d'articles, panier, totaux, récapitulatif, enregistrement |
| Historique | `/history` | filtres, aperçu de la commande, PDF / Excel / export, modification, suppression |
| Conventions | `/conventions` | statut, échéance, exercices, plafonds, import Excel, modèle vierge |
| Rapport | `/reports` | consommation par convention pour un exercice + export Excel |
| Paramètres | `/settings` | thème, compteurs, sauvegarde de la base, à propos |

### Règles métier (reprises de l'édition bureau)

- **Prix figés** : le prix est toujours relu en base ; un écart déclenche le
  dialogue « Les prix ont changé » (reprendre les prix actuels ou annuler).
- **Numérotation** : `PRÉFIXE-EXERCICE-0001`, libre en base **et** sur le disque.
- **Plafond** : `consommé + commande >= plafond` **bloque** l'enregistrement
  (égalité incluse). Les alertes s'affichent à 80 % et 90 %.
- **Exercice actif unique** par convention ; un exercice clôturé archive son
  consommé et interdit toute nouvelle saisie.
- **Convention fermée ou expirée** : saisie refusée côté serveur.
- **Totaux** : total HT = somme des totaux de ligne arrondis, identique à
  l'affichage, au PDF et à l'Excel. TVA 19 %.
- **Séquence d'écriture** : validation sans écriture → génération des fichiers →
  base en une transaction ; en cas d'échec, les fichiers sont supprimés ou
  restaurés (jamais de divergence fichier / base).

### Formulaires Word (dossier `Model/`)

Trois formulaires administratifs vides sont fournis en `.docx` :

| N° | Formulaire | Bouton |
| --- | --- | --- |
| 2 | Demande de matières, fournitures et matériels | **D.M/F/M** |
| 3 | Demande d'achat | **D.Achat** |
| 4 | Demande d'approvisionnement du magasin | **D.A.Mag** |

Depuis la **fiche commande** ou l'**aperçu de l'historique**, les boutons
téléchargent le formulaire rempli à partir de la commande (n°, date,
désignations, quantités, référence et unité pour le 4). Un dialogue — dont le
libellé complet apparaît en titre — permet de compléter les champs libres :
**service demandeur** (2 et 3), **référence de la demande de matières** (3),
**convention commerciale du centre N°** (4), dont les valeurs par défaut se
règlent dans **Paramètres → Formulaires Word**.

- **Pagination** : chaque page contient 10 lignes d'articles et un formulaire
  complet (titre, n°, date, champs libres, tableau, observations, signatures) ;
  la mention *Page x/y* est imprimée sous le n°. Au-delà de 10 articles, une
  nouvelle page commence automatiquement (la note (1)/(2) du formulaire 2
  n'apparaît que sur la première page).
- Les zones d'observation, d'avis et de signature restent **vierges** : elles
  sont remplies à la main dans Word.
- Les fichiers `.docx` de `Model/` ne sont **jamais modifiés** : le formulaire
  est produit à la volée, rien n'est conservé sur le disque.

---

## 3. Structure du projet

```
web-app/
├── run.bat                 # lancement double-clique (Windows, CRLF)
├── serve.py                # serveur local 127.0.0.1:8765 (+ ports suivants)
├── requirements.txt
├── source_listes.xlsx      # classeur graine (import initial)
├── wheels/                 # paquets pour installation hors-ligne
├── LISEZ-MOI.txt           # notice remise au collègue
├── fabriquer_archive.ps1   # fabrique GestionArticles-v2.0.zip
├── web_app.db              # base SQLite (créée au premier lancement)
├── app/
│   ├── __init__.py         # fabrique Flask, filtres Jinja, erreurs, CLI
│   ├── config.py           # chemins, TVA, seuils, thèmes, port
│   ├── security.py         # CSRF, en-têtes, résolution de fichiers
│   ├── database.py         # schéma, règles métier, contrôles
│   ├── importer.py         # lecture/écriture des classeurs Excel
│   ├── routes/             # blueprints (pages + API JSON)
│   ├── services/documents.py  # création/modification, PDF, Excel, numéros
│   ├── reports/            # générateurs PDF, Excel, rapport annuel, formulaires Word
│   ├── templates/          # Jinja (thème unique `base.html`)
│   └── static/             # CSS et JS locaux (aucun CDN)
├── Model/                  # modèles Word des formulaires (lecture seule)
├── tests/smoke_test.py     # test de fumée complet (aucune dépendance)
├── tools/gen_themes.py     # régénère static/css/themes.css
└── CONTEXTE.md             # contexte projet / architecture (reprise par un tiers ou une IA)
```

---

## 4. Import des listes de prix

Feuilles attendues (en-têtes exacts) :

| N° | Désignation | Unité de mesure | Prix unitaire HT |
| --- | --- | --- | --- |

Deux façons d'importer :

1. **Conventions → Importer une liste** : choix du classeur, prévisualisation des
   feuilles, convention de destination par feuille.
   Une feuille vers une convention existante **remplace** sa liste ; une feuille
   vers une convention inconnue **crée** une nouvelle liste.
2. **Paramètres → Importer `source_listes.xlsx`** : import direct du classeur
   fourni avec le projet.

Le **modèle Excel vierge** (`Conventions → Modèle Excel`) respecte ces en-têtes.

---

## 5. Sécurité

- Liaison **127.0.0.1 uniquement**, `debug` désactivé en production.
- **CSRF** obligatoire sur toute mutation (formulaires et API JSON) : le jeton est
  porté par le balise `<meta name="csrf-token">` et envoyé en en-tête
  `X-CSRF-Token` ou dans le corps.
- **En-têtes** : CSP stricte (`script-src 'self'`), `X-Frame-Options: DENY`,
  `nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `COOP`.
- **Fichiers** : téléchargements via `/files/<id>/<kind>` ; les chemins stockés en
  base sont relatifs et vérifiés contre le dossier d'export (anti-`../`).
- **Clé de session** : fichier local `.session.key`, jamais versionné.
- Aucune donnée n'est envoyée hors de la machine.

---

## 6. Tests et contrôles

```bat
 python tests\smoke_test.py     :: 136 vérifications (pages, CSRF, plafond, import, formulaires…)
python -m pyflakes app serve.py tests
node --check app\static\js\*.js
```

Le test de fumée utilise `flask.test_client()` dans un dossier temporaire :
aucune donnée réelle n'est touchée.

---

## 7. Sauvegarde et restauration

- **Paramètres → Sauvegarde de la base** : copie SQLite cohérente (`VACUUM INTO`)
  téléchargée immédiatement.
- **CLI** : `python -m flask --app app backup` crée
  `web_app-backup-AAAAMMJJ-HHMMSS.db` à côté de l'application.
- Restauration : arrêter l'application, remplacer `web_app.db` par la copie,
  relancer.

Les PDF/Excel générés sont de simples fichiers : ils peuvent être copiés tels quels.

---

## 8. Dépannage

| Symptôme | Cause probable | Solution |
| --- | --- | --- |
| Page blanche / `TemplateNotFound` | dossier `app/templates` incomplet | vérifier l'intégrité des fichiers |
| « Aucun exercice actif » | convention sans exercice | Conventions → *Ouvrir un exercice* |
| Enregistrement bloqué | plafond atteint | augmenter le plafond ou clôturer l'exercice |
| Import refusé | en-têtes de colonnes différents | utiliser le modèle Excel fourni |
| `[ERREUR] Python introuvable` | Python absent ou sans *Add to PATH* | installer Python 3.10-3.14 puis relancer `run.bat` |
| Installation hors-ligne échouée | `wheels/` incompatible avec ce Python | se connecter une fois à internet puis relancer `run.bat` |
| Navigateur sur page vide | ancien serveur encore ouvert | fermer l'ancienne fenêtre noire, relancer `run.bat` |
