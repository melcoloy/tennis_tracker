"""
tournois.py -- reconstitue les tableaux de tournoi.

On ne telecharge rien de plus : chaque fichier joueur contient ses
matchs avec le nom de l'adversaire. En croisant les 131 carrieres, on
retrouve la quasi-totalite d'un tableau principal.

Limite assumee : un match entre deux joueurs absents de la base
n'apparait nulle part. Sur un tournoi couvert par le top 100, cela ne
concerne guere que les qualifies.
"""

import re
import unicodedata

# Du 250 au Grand Chelem. On laisse de cote les challengers, les ITF
# et la Coupe Davis, qui n'ont pas la forme d'un tableau classique.
NIVEAUX = {"G", "M", "A", "F", "O"}

# Ordre d'affichage des tours, du plus avance au premier
ORDRE_TOURS = ["F", "BR", "SF", "QF", "R16", "R32", "R64", "R128", "RR",
               "Q3", "Q2", "Q1"]

NOM_TOUR = {
    "F": "Finale", "BR": "3e place", "SF": "Demi-finales",
    "QF": "Quarts de finale", "R16": "8es de finale",
    "R32": "16es de finale", "R64": "32es de finale",
    "R128": "64es de finale", "RR": "Phase de poules",
    "Q3": "Qualifications", "Q2": "Qualifications", "Q1": "Qualifications",
}


def _sans_accent(t):
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn")


def identifiant(tournoi, date):
    """'Cincinnati Masters' + '20260813' -> 'cincinnati-masters-20260813'"""
    base = re.sub(r"[^a-z0-9]+", "-", _sans_accent(tournoi).lower()).strip("-")
    return f"{base}-{date}"


def inverser_score(score):
    """
    '4-6 3-6' -> '6-4 6-3', du point de vue du vainqueur.

    Necessaire quand on ne dispose que de la fiche du perdant. Les
    tie-breaks gardent leur numero : '6-7(4)' devient '7-6(4)'.
    """
    manches = []
    for m in score.split():
        j = re.match(r"^(\d+)-(\d+)(\(\d+\))?$", m)
        if not j:
            return score            # abandon, walkover... on n'y touche pas
        a, b, tb = j.group(1), j.group(2), j.group(3) or ""
        manches.append(f"{b}-{a}{tb}")
    return " ".join(manches)


def construire(joueurs, slugifier, limite=60):
    """
    joueurs : liste de (slug, nom_complet, matchs)
    slugifier : la fonction de cache.py, pour reconnaitre un adversaire

    Renvoie les `limite` tournois les plus recents.
    """
    connus = {slug.lower() for slug, _, _ in joueurs}
    tournois = {}

    for slug, nom, matchs in joueurs:
        for m in matchs:
            if m.get("niveau_code") not in NIVEAUX:
                continue

            adversaire = m.get("adversaire") or ""
            if not adversaire:
                continue

            gagne = m.get("resultat") == "W"
            vainqueur, perdu = (nom, adversaire) if gagne else (adversaire, nom)
            score = m["score"] if gagne else inverser_score(m["score"])

            cle_t = identifiant(m["tournoi"], m["date"])
            t = tournois.setdefault(cle_t, {
                "id": cle_t,
                "nom": m["tournoi"],
                "date": m["date"],
                "date_fr": m["date_fr"],
                "niveau": m["niveau"],
                "niveau_code": m["niveau_code"],
                "surface": m["surface"],
                "matchs": {},
            })

            # Un match entre deux joueurs de la base apparait deux fois.
            # La cle inclut la paire, donc les deux versions se
            # confondent -- et on garde celle du vainqueur, dont le
            # score n'a pas eu besoin d'etre inverse.
            paire = tuple(sorted([vainqueur.lower(), perdu.lower()]))
            cle_m = (m.get("tour", ""), paire)

            if cle_m in t["matchs"] and not gagne:
                continue

            t["matchs"][cle_m] = {
                "tour": m.get("tour", ""),
                "vainqueur": vainqueur,
                "perdant": perdu,
                "score": score,
            }

    sortie = []
    for t in tournois.values():
        liste = list(t["matchs"].values())

        # rang du tour pour trier ; inconnu -> a la fin
        def rang(x):
            return (ORDRE_TOURS.index(x["tour"])
                    if x["tour"] in ORDRE_TOURS else len(ORDRE_TOURS))

        liste.sort(key=lambda x: (rang(x), x["vainqueur"]))

        finale = next((x for x in liste if x["tour"] == "F"), None)

        for x in liste:
            for role in ("vainqueur", "perdant"):
                s = slugifier(x[role])
                x[role + "_slug"] = s if s.lower() in connus else None

        t["matchs"] = liste
        t["nb_matchs"] = len(liste)
        t["vainqueur"] = finale["vainqueur"] if finale else None
        t["vainqueur_slug"] = finale["vainqueur_slug"] if finale else None
        t["finaliste"] = finale["perdant"] if finale else None
        t["score_finale"] = finale["score"] if finale else None
        sortie.append(t)

    sortie.sort(key=lambda t: t["date"], reverse=True)
    return sortie[:limite]


def grouper_par_tour(matchs):
    """Regroupe pour l'affichage : [(libelle, [matchs]), ...]."""
    groupes = []
    for tour in ORDRE_TOURS:
        dedans = [m for m in matchs if m["tour"] == tour]
        if dedans:
            groupes.append((NOM_TOUR.get(tour, tour), dedans))
    autres = [m for m in matchs if m["tour"] not in ORDRE_TOURS]
    if autres:
        groupes.append(("Autres", autres))
    return groupes