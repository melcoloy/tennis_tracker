"""
race.py -- position dans la Race ATP, depuis live-tennis.eu.

La page contient TOUS les joueurs. On la telecharge donc une seule
fois, on en tire une table slug -> rang, et chaque joueur y est ensuite
cherche sans nouvelle requete.

(La version precedente retelechargeait la page entiere par joueur :
sur un build de 100 joueurs, cela faisait 100 fois 1,5 Mo du meme
fichier, et le site finissait par refuser.)

Attention : tennisexplorer.com/ranking/atp-men/?race=1 IGNORE le
parametre et renvoie le classement ATP ordinaire. Une source qui
repond 200 avec des donnees plausibles mais fausses.

    python race.py                 # affiche le haut de la table
    python race.py "Arthur Fils"   # cherche un joueur
"""

import html as _html
import json
import re
import time
from pathlib import Path

import requests

import cache

URL = "https://live-tennis.eu/en/atp-race"
DOSSIER = Path("cache")
TABLE = DOSSIER / "race_table.json"
DUREE_VIE = 12 * 3600          # la Race bouge une fois par semaine

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def _decoder(reponse):
    """
    Choisit le bon encodage avant de lire le texte.

    Quand un serveur ne declare pas de charset, requests suppose
    Latin-1 (heritage de la specification HTTP). live-tennis.eu sert
    de l'UTF-8 sans le declarer : sans ce correctif, 'Felix' devient
    'FA©lix'.
    """
    if "charset" not in reponse.headers.get("Content-Type", "").lower():
        reponse.encoding = reponse.apparent_encoding or "utf-8"
    return reponse.text


def _nettoyer(texte):
    """
    Enleve balises, entites HTML et symboles de tete.

    live-tennis.eu prefixe d'une coche (&#x2713;) les joueurs deja
    qualifies pour le Masters. Sans ce nettoyage, elle reste dans le
    nom et corrompt l'identifiant : le joueur devient introuvable,
    sans qu'aucune erreur ne soit levee.
    """
    t = _html.unescape(re.sub(r"<[^>]+>", "", texte)).replace("\xa0", " ")
    return re.sub(r"^[^0-9A-Za-z\u00C0-\u024F]+", "", t).strip()


def _cellules(ligne_html):
    return [_nettoyer(c)
            for c in re.findall(r"<td[^>]*>(.*?)</td>", ligne_html, re.S)]


def analyser(html):
    """
    Construit la table complete : slug minuscule -> infos.

    On indexe par identifiant, pas par nom : Tennis Abstract et
    live-tennis.eu n'ecrivent pas 'Alex de Minaur' pareil, et
    slugifier() neutralise casse, accents et particules.

    Structure d'une ligne :
      [0] rang  [1] drapeau  [2] nom  [3] age  [4] pays  [5] points
    """
    table = {}

    for ligne in re.split(r"<tr\b", html):
        nom = re.search(r"class=[\"']?pn[\"']?[^>]*>(.*?)</td>", ligne, re.S)
        rang = re.search(r"class=[\"']?rk[\"']?[^>]*>\s*(\d+)", ligne)
        if not nom or not rang:
            continue

        propre = _nettoyer(nom.group(1))
        if not propre:
            continue

        cells = _cellules(ligne)
        i = next((k for k, c in enumerate(cells) if c == propre), None)
        points = None
        if i is not None and len(cells) > i + 3 and cells[i + 3].replace(",", "").isdigit():
            points = int(cells[i + 3].replace(",", ""))

        table[cache.slugifier(propre).lower()] = {
            "position": int(rang.group(1)),
            "points": points,
            "nom_trouve": propre,
        }

    if not table:
        raise ValueError("aucun joueur trouve -- le balisage a change ?")

    return table


def table(force=False):
    """La table complete, telechargee au plus une fois par DUREE_VIE."""
    if not force and TABLE.exists():
        c = json.loads(TABLE.read_text(encoding="utf-8"))
        if time.time() - c.get("horodatage", 0) < DUREE_VIE:
            return c

    try:
        r = requests.get(URL, headers=HEADERS, timeout=25)
        r.raise_for_status()
        data = {
            "horodatage": time.time(),
            "releve_le": time.strftime("%Y%m%d"),
            "source": "live-tennis.eu",
            "joueurs": analyser(_decoder(r)),
        }
        DOSSIER.mkdir(exist_ok=True)
        TABLE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        return data

    except Exception as e:
        if TABLE.exists():
            c = json.loads(TABLE.read_text(encoding="utf-8"))
            c["perime"] = f"mise a jour impossible ({type(e).__name__})"
            return c
        raise RuntimeError(f"table de la Race indisponible : {e}")


def charger(slug, nom_complet=None, force=False):
    """
    Rang d'un joueur dans la Race. Aucune requete si la table est fraiche.

    Leve ValueError si le joueur n'y figure pas -- c'est un cas normal :
    la Race ne compte que la saison en cours, un joueur blesse ou
    retire n'y apparait pas.
    """
    t = table(force)
    joueurs = t["joueurs"]

    entree = joueurs.get(slug.lower())
    if entree is None and nom_complet:
        entree = joueurs.get(cache.slugifier(nom_complet).lower())

    if entree is None:
        fin = slug[-6:].lower()
        proches = [v["nom_trouve"] for k, v in joueurs.items() if fin in k][:3]
        raise ValueError(
            f"'{slug}' absent de la Race ({len(joueurs)} joueurs classes). "
            + (f"Noms proches : {proches}" if proches
               else "Hors classement de la saison en cours.")
        )

    return {
        **entree,
        "releve_le": t.get("releve_le", ""),
        "source": t.get("source", ""),
        "automatique": "perime" not in t,
    }


if __name__ == "__main__":
    import sys

    t = table(force=True)
    print(f"{len(t['joueurs'])} joueurs dans la Race, "
          f"releve le {t['releve_le']}\n")

    if len(sys.argv) > 1:
        nom = " ".join(sys.argv[1:])
        d = charger(cache.slugifier(nom), nom)
        print(f"  {d['nom_trouve']} -- Race #{d['position']} ({d['points']} points)")
    else:
        haut = sorted(t["joueurs"].values(), key=lambda j: j["position"])[:10]
        for j in haut:
            print(f"  #{j['position']:<4} {j['nom_trouve']:<26} {j['points']}")