"""
tirages_auto.py -- recupere les tableaux des tournois ATP en cours
depuis les pages de pronostics de Tennis Abstract.

    python tirages_auto.py

Ecrit tirages/<ville>.txt au format lu par prochain.py. Un fichier
sans la ligne '# Source: auto' a ete fait a la main : on n'y touche pas.
"""

import html as _html
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests

import cache

ACCUEIL = "https://www.tennisabstract.com/"
GABARIT = "https://www.tennisabstract.com/current/{annee}ATP{ville}.html"
DOSSIER = Path("tirages")
MARQUEUR = "# Source: auto"

# (surface, niveau) des tournois connus ; les autres restent vides
INFOS = {
    "Paris": ("Hard", "Masters 1000"),
}


def telecharger(url):
    r = requests.get(url, headers=cache.HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def tournois_en_cours():
    """[('2026', 'Paris'), ...] d'apres les liens de la page d'accueil."""
    return sorted(set(re.findall(r"current/(\d{4})ATP(\w+)\.html",
                                 telecharger(ACCUEIL))))


def plus_grand_tableau(page):
    """
    (taille, tableau) du premier tour : proj64, ou proj32 pour un petit
    tournoi. (0, None) si la page n'en contient pas encore.
    """
    tailles = [int(n) for n in re.findall(r"var\s+proj(\d+)\s*=", page)]
    if not tailles:
        return 0, None
    n = max(tailles)
    # chaine JS entre apostrophes ; \\. saute les \' echappes (O\'Connell)
    m = re.search(r"var\s+proj%d\s*=\s*'((?:[^'\\]|\\.)*)'" % n, page)
    return (n, m.group(1).replace("\\'", "'")) if m else (0, None)


def lignes_tirage(tableau):
    """Une ligne par place, dans l'ordre : 'Carlos Alcaraz (2)', 'Bye'..."""
    sortie = []
    for cellule in re.findall(r"<tr><td>(.*?)</td>", tableau):
        texte = _html.unescape(re.sub(r"<[^>]+>", "", cellule)).strip()
        # Ligne d'en-tete, et lignes vides que Tennis Abstract intercale
        # entre les sections du tableau : une ligne vide dans le .txt
        # deviendrait une place « a determiner » et decalerait tout.
        if not texte or texte.startswith("Player"):
            continue
        marque = re.match(r"\(([^)]+)\)", texte)        # (2), (Q), (WC)...
        nom = re.sub(r"^\([^)]+\)\s*", "", texte)       # retire la marque
        nom = re.sub(r"\s*\([A-Z]{3}\)$", "", nom)      # retire le pays
        sortie.append(f"{nom} ({marque.group(1)})" if marque else nom)
    return sortie


def date_a_garder(fichier):
    """
    Garde la date deja ecrite : l'identifiant du tournoi en depend, et
    les pronostics enregistres dans le navigateur sont ranges sous cet
    identifiant. Sinon, le lundi de la semaine.
    """
    if fichier.exists():
        m = re.search(r"^# Date:\s*(\d{8})",
                      fichier.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    lundi = date.today() - timedelta(days=date.today().weekday())
    return lundi.strftime("%Y%m%d")


def ecrire(ville, lignes):
    DOSSIER.mkdir(exist_ok=True)
    fichier = DOSSIER / f"{ville.lower()}.txt"

    if fichier.exists() and MARQUEUR not in fichier.read_text(encoding="utf-8"):
        print(f"  {ville:<16} ignore : {fichier.name} a ete fait a la main")
        return

    surface, niveau = INFOS.get(ville, ("", ""))
    entete = [MARQUEUR,
              f"# Nom: {ville}",
              f"# Date: {date_a_garder(fichier)}",
              f"# Surface: {surface}",
              f"# Niveau: {niveau}"]
    fichier.write_text("\n".join(entete + lignes) + "\n", encoding="utf-8")
    print(f"  {ville:<16} {len(lignes)} places -> {fichier}")


def main():
    tournois = tournois_en_cours()
    if not tournois:
        print("Aucun tournoi ATP en cours sur Tennis Abstract.")
        return

    for annee, ville in tournois:
        try:
            page = telecharger(GABARIT.format(annee=annee, ville=ville))
            taille, tableau = plus_grand_tableau(page)
            if not tableau:
                print(f"  {ville:<16} pas encore de tableau publie")
                continue
            lignes = lignes_tirage(tableau)
            # proj64 = 64 places exactement, byes compris. Un autre compte
            # veut dire que le format de la page a change : mieux vaut ne
            # rien ecrire qu'un tableau decale.
            if len(lignes) != taille:
                print(f"  {ville:<16} ECHEC -- {len(lignes)} lignes lues "
                      f"pour un tableau de {taille}, fichier non modifie")
                continue
            ecrire(ville, lignes)
        except Exception as e:
            print(f"  {ville:<16} ECHEC -- {e}")
        time.sleep(2)                     # rester poli avec le site


if __name__ == "__main__":
    main()