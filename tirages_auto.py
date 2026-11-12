"""
tirages_auto.py -- recupere les tableaux des tournois ATP en cours
depuis les pages de pronostics de Tennis Abstract.

    python tirages_auto.py

Ecrit tirages/<ville>.txt au format lu par prochain.py. Un fichier
sans la ligne '# Source: auto' a ete fait a la main : on n'y touche pas.
"""

import html as _html
import json
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

import cache

ACCUEIL = "https://www.tennisabstract.com/"
GABARIT = "https://www.tennisabstract.com/current/{annee}ATP{ville}.html"
DOSSIER = Path("tirages")
MARQUEUR = "# Source: auto"

# (surface, niveau) imposes a la main. Les autres tournois sont
# reconnus dans les carrieres deja publiees (voir infos_connues()).
INFOS = {
    "Paris": ("Hard", "Masters 1000"),
}

# Fiches joueurs deja publiees : elles contiennent les editions passees
# de presque tous les tournois du circuit.
DONNEES = Path("site/donnees")

# Au-dela, la date d'un ancien fichier n'est plus reprise : c'est
# l'edition de l'annee suivante.
JOURS_REPRISE = 21

# Codes de niveau Tennis Abstract du circuit principal : Grand Chelem,
# Masters 1000, ATP 250/500, Masters de fin d'annee.
NIVEAUX_ATP = {"G", "M", "A", "F"}


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


def lundi_du_tournoi():
    """
    Le lundi de la semaine du tournoi. Un tableau publie le week-end est
    celui de la semaine suivante : le samedi et le dimanche, on prend
    donc le lundi qui vient, pas celui qui est passe.
    """
    aujourd_hui = date.today()
    if aujourd_hui.weekday() >= 5:
        return aujourd_hui + timedelta(days=7 - aujourd_hui.weekday())
    return aujourd_hui - timedelta(days=aujourd_hui.weekday())


def date_a_garder(fichier):
    """
    Garde la date deja ecrite : l'identifiant du tournoi en depend, et
    les pronostics enregistres dans le navigateur sont ranges sous cet
    identifiant. Sauf si elle est ancienne : c'est alors l'edition de
    l'annee suivante, qui recoit sa propre date.
    """
    lundi = lundi_du_tournoi()
    if fichier.exists():
        m = re.search(r"^# Date:\s*(\d{8})",
                      fichier.read_text(encoding="utf-8"), re.M)
        if m:
            ancienne = datetime.strptime(m.group(1), "%Y%m%d").date()
            if abs((lundi - ancienne).days) <= JOURS_REPRISE:
                return m.group(1)
    return lundi.strftime("%Y%m%d")


def cle_nom(nom):
    """'Los Cabos' et 'LosCabos' -> 'loscabos'."""
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return "".join(c for c in s.lower() if c.isalnum())


def infos_connues():
    """
    {cle de ville: (surface, niveau)} d'apres les carrieres publiees,
    en gardant l'edition la plus recente de chaque tournoi. On ne lit
    qu'une trentaine de fiches : les meilleurs joueurs jouent presque
    tout le circuit, c'est largement suffisant.
    """
    infos, dates = {}, {}
    fiches = sorted(p for p in DONNEES.glob("*.json")
                    if p.stem not in ("index", "prochain", "tournois_resume"))
    for fiche in fiches[:40]:
        try:
            matchs = json.loads(fiche.read_text(encoding="utf-8"))["matchs"]["matchs"]
        except (ValueError, KeyError):
            continue
        for m in matchs:
            # circuit principal seulement : Turin ou Brisbane ont aussi
            # un Challenger, qui ne doit pas preter son niveau a l'ATP
            if m.get("niveau_code") not in NIVEAUX_ATP:
                continue
            cle = cle_nom(m.get("tournoi", ""))
            if cle and m.get("date", "") > dates.get(cle, ""):
                dates[cle] = m["date"]
                infos[cle] = (m.get("surface", ""), m.get("niveau", ""))
    return infos


def surface_niveau(ville, connues):
    """Le dictionnaire INFOS d'abord, puis les carrieres publiees."""
    if ville in INFOS:
        return INFOS[ville]
    cle = cle_nom(ville)
    if not cle:
        return ("", "")
    if cle in connues:                                  # « Stockholm »
        return connues[cle]
    for nom, valeurs in connues.items():                # « Paris Masters »
        if cle in nom:
            return valeurs
    return ("", "")


def ecrire(ville, lignes, connues):
    DOSSIER.mkdir(exist_ok=True)
    fichier = DOSSIER / f"{ville.lower()}.txt"

    if fichier.exists() and MARQUEUR not in fichier.read_text(encoding="utf-8"):
        print(f"  {ville:<16} ignore : {fichier.name} a ete fait a la main")
        return

    surface, niveau = surface_niveau(ville, connues)
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

    connues = infos_connues()
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
            ecrire(ville, lignes, connues)
        except Exception as e:
            print(f"  {ville:<16} ECHEC -- {e}")
        time.sleep(2)                     # rester poli avec le site


if __name__ == "__main__":
    main()