"""
Etape 2 -- Extraire les donnees de la page sauvegardee.

Version 2 : le JS de Tennis Abstract n'est PAS du JSON. Il contient des
commentaires et des virgules finales. On nettoie avant de parser, et
en cas d'echec on affiche le texte fautif au lieu d'une pile d'erreurs.

    python extrait.py
"""

import json
import re
from collections import Counter

FICHIER = "page_fils.html"


def decouper_variable(html, nom):
    """Isole le texte de 'var <nom> = [...]' en comptant les crochets."""
    m = re.search(r"var\s+" + nom + r"\s*=\s*\[", html)
    if not m:
        raise ValueError(f"Variable '{nom}' introuvable")

    debut = m.end() - 1
    profondeur = 0
    dans_chaine = False
    guillemet = ""

    i = debut
    while i < len(html):
        c = html[i]
        if dans_chaine:
            if c == "\\":
                i += 2          # on saute le caractere echappe
                continue
            if c == guillemet:
                dans_chaine = False
        else:
            if c in "\"'":
                dans_chaine, guillemet = True, c
            elif c == "[":
                profondeur += 1
            elif c == "]":
                profondeur -= 1
                if profondeur == 0:
                    return html[debut:i + 1]
        i += 1

    raise ValueError(f"Crochet fermant introuvable pour '{nom}'")


def nettoyer_js(texte):
    """
    Transforme du JS en JSON valide.

    On parcourt caractere par caractere en sachant si on est dans une
    chaine : sans ca, on supprimerait un '//' present dans un nom de
    tournoi. On retire les commentaires et on uniformise les guillemets.
    """
    sortie = []
    i = 0
    dans_chaine = False
    guillemet = ""

    while i < len(texte):
        c = texte[i]

        if dans_chaine:
            if c == "\\":
                sortie.append(texte[i:i + 2])
                i += 2
                continue
            if c == guillemet:
                dans_chaine = False
                sortie.append('"')          # on ressort toujours en double
                i += 1
                continue
            if c == '"':
                sortie.append('\\"')        # un " dans une chaine simple
                i += 1
                continue
            sortie.append(c)
            i += 1
            continue

        # hors chaine
        if c in "\"'":
            dans_chaine, guillemet = True, c
            sortie.append('"')
            i += 1
        elif texte.startswith("//", i):
            saut = texte.find("\n", i)
            if saut == -1:
                break
            i = saut
        elif texte.startswith("/*", i):
            fin = texte.find("*/", i)
            i = len(texte) if fin == -1 else fin + 2
        else:
            sortie.append(c)
            i += 1

    propre = "".join(sortie)
    # virgules finales : [1, 2, ] -> [1, 2]
    propre = re.sub(r",\s*([\]}])", r"\1", propre)
    return propre


def extraire_tableau(html, nom):
    brut = decouper_variable(html, nom)
    propre = nettoyer_js(brut)
    try:
        return json.loads(propre)
    except json.JSONDecodeError as e:
        print(f"\n[!] '{nom}' illisible meme apres nettoyage : {e}")
        print("    --- texte brut (400 premiers caracteres) ---")
        print("   ", brut[:400].replace("\n", "\n    "))
        print(f"    --- apres nettoyage, autour du caractere {e.pos} ---")
        print("   ", propre[max(0, e.pos - 120):e.pos + 120])
        raise


def construire_matchs(colonnes, lignes):
    return [
        {col: (ligne[i] if i < len(ligne) else "") for i, col in enumerate(colonnes)}
        for ligne in lignes
    ]


def resume(matchs):
    print("=" * 60)
    print(f"{len(matchs)} matchs extraits")
    print("=" * 60)

    dates = sorted(m["date"] for m in matchs if m.get("date"))
    if dates:
        print(f"\nPeriode : {dates[0]} -> {dates[-1]}")

    print("\nMatchs par annee :")
    for annee, n in sorted(Counter(m["date"][:4] for m in matchs if m.get("date")).items()):
        print(f"   {annee} : {n:>3}  {'#' * min(n, 50)}")

    print("\nMatchs par niveau de tournoi :")
    for niveau, n in Counter(m.get("level", "?") for m in matchs).most_common():
        print(f"   '{niveau}' : {n}")

    print("\nBilan :")
    for res, n in Counter(m.get("wl", "?") for m in matchs).most_common():
        print(f"   '{res}' : {n}")

    print("\nLes 3 matchs les plus recents :")
    for m in sorted(matchs, key=lambda x: x.get("date", ""), reverse=True)[:3]:
        print(f"   {m.get('date')}  {m.get('tourn')} ({m.get('round')})  "
              f"{m.get('wl')} vs {m.get('opp')}  {m.get('score')}")


if __name__ == "__main__":
    with open(FICHIER, encoding="utf-8") as f:
        html = f.read()

    colonnes = extraire_tableau(html, "matchhead")
    print(f"Colonnes ({len(colonnes)}) :")
    for i, c in enumerate(colonnes):
        print(f"   [{i:>2}] {c}")
    print()

    lignes = extraire_tableau(html, "matchmx")
    matchs = construire_matchs(colonnes, lignes)
    resume(matchs)

    try:
            # Le classement vient de matchmx, pas de vranks (qui contient
    # les rangs des ADVERSAIRES, pour un filtre de l'interface).
        par_date = {}
        for m in matchs:
            date, rang = m.get("date", ""), m.get("rank", "")
            if date and rang.isdigit():
                par_date[date] = int(rang)

        classement = [{"date": d, "rang": par_date[d]} for d in sorted(par_date)]
        print(f"\nClassement : {len(classement)} points, "
          f"de {classement[0]['date']} a {classement[-1]['date']}")
        print(f"   meilleur rang a l'entree d'un tournoi : "
          f"{min(c['rang'] for c in classement)}")
        print(f"   rang avant son dernier tournoi        : {classement[-1]['rang']}")
        print("   /!\\ le classement actuel est plus recent que cette serie")
    except Exception as e:
        print(f"\n[!] Classement non extrait : {e}")
        classement = []

    with open("donnees.json", "w", encoding="utf-8") as f:
        json.dump({"matchs": matchs, "classement": classement},
                  f, ensure_ascii=False, indent=2)
    print("\n-> Ecrit dans donnees.json")