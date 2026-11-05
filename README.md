# Tennis Tracker

Carrières ATP retracées depuis les premiers tournois juniors : frise de
résultats, courbe de classement, titres, bilans par surface et par
palier, comparaisons à âge égal, tableaux de tournois reconstitués et
pronostics sur les tournois en cours.

**Site : https://melcoloy.github.io/tennis_tracker/**

Environ 260 joueurs : le top 200 mondial et une trentaine de légendes
retraitées (Federer, Nadal, Sampras, Borg…).

## Ce que propose le site

| Page | Contenu |
|---|---|
| Accueil | grille des joueurs, recherche, derniers tournois, bandeau des pronostics ouverts |
| Joueur | frise de carrière, classement (échelle log), titres, bilans par surface et par palier, tous les matchs filtrables |
| Comparaison | plusieurs carrières superposées, alignées sur l'âge, et tableau face à face |
| Tournois | tableaux des 60 derniers tournois, reconstitués en croisant les carrières |
| Pronostics | tableau du tournoi en cours à remplir, enregistré dans le navigateur, exportable en image |

## Fonctionnement

```
Tennis Abstract ──► cache/ ──► source.py ──► api.py ──► figer.py ──► site/ ──► GitHub Pages
live-tennis.eu  ──► race.py, annuaire.py ─┘                ▲
Tennis Abstract (pages « current ») ──► tirages_auto.py ──► prochain.py
```

- **Données** : les pages joueur de Tennis Abstract contiennent toute la
  carrière dans des variables JavaScript. `source.py` les extrait,
  `cache.py` les garde 24 h en local.
- **Deux modes, un seul front** : avec le serveur FastAPI (`api.py`),
  le site interroge `/api/...` ; publié, il lit des JSON figés par
  `figer.py`. Le front choisit tout seul selon la présence de
  `site/donnees/index.json`.
- **Publication** : Tennis Abstract refuse les serveurs des centres de
  données, GitHub Actions compris. Le site est donc construit en local,
  puis poussé ; l'Action `publier.yml` ne fait que le mettre en ligne,
  après avoir vérifié qu'il est complet.

## Installation

Python 3.10 ou plus récent.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Utilisation

**Publier** (télécharge ce qui a plus de 24 h, construit `site/`, pousse) :

```powershell
python publier.py                    # même sélection que la dernière fois
python publier.py --top 100          # suivre le top 100 mondial
python publier.py --legendes         # inclure les légendes retraitées
python publier.py CarlosAlcaraz      # ajouter un joueur précis
python publier.py --forcer           # tout retélécharger, sans attendre 24 h
python publier.py --sans-push        # construire sans publier
python publier.py --top 50 --accepter   # publier un site volontairement plus petit
```

Avant de pousser, `publier.py` compare le site construit à la dernière
publication. S'il compte plus de 10 % de joueurs en moins, ou si plus de
10 % des fiches n'ont pas pu être lues (format de Tennis Abstract
modifié, téléchargements bloqués…), rien n'est publié et la commande
s'arrête avec une erreur. `--accepter` passe outre quand la baisse est
voulue.

**Vérifier en local avant de publier** :

```powershell
python publier.py --sans-push
cd site; python -m http.server 8080       # puis http://localhost:8080
```

**Développer avec le serveur** (données à la demande) :

```powershell
uvicorn api:app --reload                  # puis http://127.0.0.1:8000
```

**Tableaux de pronostics** : `tirages_auto.py` récupère les tableaux des
tournois ATP en cours et écrit `tirages/<ville>.txt`, puis `prochain.py`
prépare `site/donnees/prochain.json`. Un tableau peut aussi s'écrire à la
main : un joueur par ligne, dans l'ordre du tableau, avec `(1)`, `(Q)`,
`(WC)`, `(LL)` pour les têtes de série et statuts d'entrée. Un fichier
sans la ligne `# Source: auto` n'est jamais écrasé. Les tournois de plus
de 10 jours sont ignorés.

**Noms qui ne correspondent pas** : quand live-tennis.eu et Tennis
Abstract n'écrivent pas un nom de la même façon, `corrections.json` fait
le lien. `python trouver_slug.py "Nom du joueur"` trouve le bon
identifiant.

## Mise à jour automatique (Windows)

Deux tâches du Planificateur de tâches :

| Tâche | Quand | Script | Rôle |
|---|---|---|---|
| `TennisTracker` | lundi et jeudi, 9 h | `maj.ps1` | joueurs, tableaux, site complet |
| `TennisTirages` | tous les jours, 20 h | `maj_tirages.ps1` | tableaux seulement, poussés s'ils ont changé |

Les journaux vont dans `logs/`. Les tâches tournent sur le PC : s'il est
éteint à l'heure prévue, elles se lancent à l'allumage suivant.
Si le garde-fou annule une publication, `TennisTracker` se termine avec
le code 2 : `Get-ScheduledTaskInfo TennisTracker` l'affiche dans
`LastTaskResult`, et le journal en donne la raison.

## Fichiers

| Fichier | Rôle |
|---|---|
| `cache.py` | téléchargement et cache des pages joueur, identifiants |
| `source.py` | extraction du profil, des matchs et du classement |
| `race.py` | position dans la Race (live-tennis.eu) |
| `annuaire.py` | joueurs classés, pour `--top` et l'autocomplétion |
| `tournois.py` | reconstitution des tableaux à partir des carrières |
| `api.py` | serveur FastAPI |
| `figer.py` | version statique du site dans `site/` |
| `publier.py` | téléchargement, construction et publication en une commande |
| `tirages_auto.py` | tableaux des tournois en cours |
| `prochain.py` | tableaux de pronostics pour le site |
| `trouver_slug.py` | recherche d'un identifiant Tennis Abstract |
| `frontend/` | le site (HTML, CSS, JavaScript sans dépendance) |
| `site/` | le site construit, celui qui est publié |

## Sources

Résultats, classements et tableaux : [Tennis Abstract](https://www.tennisabstract.com/).
Race et classement en direct : [live-tennis.eu](https://live-tennis.eu/).
Les téléchargements sont espacés et ralentissent d'eux-mêmes quand le
site le demande.
