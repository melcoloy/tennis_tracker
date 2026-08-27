"""
source.py -- lecture des donnees Tennis Abstract.

Consolide tout ce qu'on a valide :
  - le profil (variables scalaires : rang actuel, pic, taille...)
  - les matchs (matchmx + matchhead)
  - la courbe de classement (deduite de matchmx)

Utilisable comme module (from source import charger) ou en direct :

    python source.py
"""

import json
import re
from collections import Counter
from datetime import date

FICHIER = "page_fils.html"

# Traduction des codes de niveau de tournoi vus dans les donnees
NIVEAUX = {
    "15": "ITF M15", "25": "ITF M25", "C": "Challenger",
    "A": "ATP 250/500", "M": "Masters 1000", "G": "Grand Chelem",
    "F": "Finals", "D": "Coupe Davis", "O": "Jeux Olympiques",
}


# ---------------------------------------------------------------- extraction

def decouper_variable(html, nom):
    """Isole 'var <nom> = [...]' en comptant les crochets imbriques."""
    m = re.search(r"var\s+" + nom + r"\s*=\s*\[", html)
    if not m:
        raise ValueError(f"Variable '{nom}' introuvable")

    debut, profondeur, dans_chaine, guillemet = m.end() - 1, 0, False, ""
    i = debut
    while i < len(html):
        c = html[i]
        if dans_chaine:
            if c == "\\":
                i += 2
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
    """JS -> JSON : retire commentaires et virgules finales, unifie les guillemets."""
    sortie, i, dans_chaine, guillemet = [], 0, False, ""
    while i < len(texte):
        c = texte[i]
        if dans_chaine:
            if c == "\\":
                sortie.append(texte[i:i + 2]); i += 2; continue
            if c == guillemet:
                dans_chaine = False; sortie.append('"'); i += 1; continue
            if c == '"':
                sortie.append('\\"'); i += 1; continue
            sortie.append(c); i += 1; continue

        if c in "\"'":
            dans_chaine, guillemet = True, c
            sortie.append('"'); i += 1
        elif texte.startswith("//", i):
            saut = texte.find("\n", i)
            if saut == -1:
                break
            i = saut
        elif texte.startswith("/*", i):
            fin = texte.find("*/", i)
            i = len(texte) if fin == -1 else fin + 2
        else:
            sortie.append(c); i += 1

    return re.sub(r",\s*([\]}])", r"\1", "".join(sortie))


def extraire_tableau(html, nom):
    brut = decouper_variable(html, nom)
    propre = nettoyer_js(brut)
    try:
        return json.loads(propre)
    except json.JSONDecodeError as e:
        print(f"\n[!] '{nom}' illisible : {e}")
        print("    brut :", brut[:300].replace("\n", " "))
        print("    zone :", propre[max(0, e.pos - 100):e.pos + 100])
        raise


def extraire_scalaire(html, nom, defaut=None):
    """
    Recupere 'var <nom> = 11;' ou "var <nom> = 'R';".

    Renvoie toujours une chaine. On prend la PREMIERE occurrence :
    la page reassigne certaines variables plus bas dans le code.
    """
    m = re.search(r"var\s+" + nom + r"\s*=\s*('([^']*)'|\"([^\"]*)\"|([^;\n,]+))", html)
    if not m:
        return defaut
    valeur = m.group(2) or m.group(3) or (m.group(4) or "").strip()
    return valeur if valeur != "" else defaut


# ------------------------------------------------------------------ assemblage

def _age(dob):
    """Age a partir d'une date AAAAMMJJ."""
    if not dob or len(dob) != 8:
        return None
    naiss = date(int(dob[:4]), int(dob[4:6]), int(dob[6:]))
    auj = date.today()
    return auj.year - naiss.year - ((auj.month, auj.day) < (naiss.month, naiss.day))


def charger(fichier=FICHIER):
    with open(fichier, encoding="utf-8") as f:
        html = f.read()

    # -- profil
    profil = {
        cle: extraire_scalaire(html, cle)
        for cle in ("fullname", "country", "dob", "ht", "hand", "backhand",
                    "currentrank", "peakrank", "peakfirst", "elo_rank")
    }
    profil["age"] = _age(profil.get("dob"))

    # -- matchs
    colonnes = extraire_tableau(html, "matchhead")
    lignes = extraire_tableau(html, "matchmx")
    matchs = [
        {col: (ligne[i] if i < len(ligne) else "") for i, col in enumerate(colonnes)}
        for ligne in lignes
    ]
    for m in matchs:
        m["niveau_fr"] = NIVEAUX.get(m.get("level", ""), m.get("level", "?"))

    # -- courbe de classement
    # ATTENTION : 'rank' est le classement A L'OUVERTURE du tournoi
    # (confirme par les infobulles du site). Cette serie ne contient donc
    # PAS le classement publie apres le dernier tournoi joue.
    # Le rang actuel, c'est profil['currentrank'].
    par_date = {}
    for m in matchs:
        d, r = m.get("date", ""), m.get("rank", "")
        if d and r.isdigit():
            par_date[d] = int(r)
    classement = [{"date": d, "rang": par_date[d]} for d in sorted(par_date)]

    return {"profil": profil, "matchs": matchs, "classement": classement}


# ---------------------------------------------------------------------- resume

def resume(donnees):
    p, matchs, cl = donnees["profil"], donnees["matchs"], donnees["classement"]

    main = "droitier" if p.get("hand") == "R" else "gaucher"
    revers = "revers a deux mains" if p.get("backhand") == "2" else "revers a une main"

    print("=" * 62)
    print(f"  {p['fullname']} ({p['country']})  --  {p['age']} ans, "
          f"{p['ht']} cm, {main}, {revers}")
    print(f"  Classement ATP actuel : {p['currentrank']}")
    print(f"  Meilleur classement   : {p['peakrank']}  (depuis le {p['peakfirst']})")
    print(f"  Classement Elo        : {p['elo_rank']}")
    print("=" * 62)

    v = sum(1 for m in matchs if m.get("wl") == "W")
    d = sum(1 for m in matchs if m.get("wl") == "L")
    total = v + d
    pct = f"  ({100 * v / total:.1f} %)" if total else ""
    print(f"\n{len(matchs)} matchs  |  {v}V - {d}D{pct}")

    print("\nPar annee :")
    for annee, n in sorted(Counter(m["date"][:4] for m in matchs if m.get("date")).items()):
        gagnes = sum(1 for m in matchs if m.get("date", "").startswith(annee)
                     and m.get("wl") == "W")
        print(f"   {annee} : {n:>3} matchs  ({gagnes}V-{n - gagnes}D)")

    print("\nPar niveau :")
    for niv, n in Counter(m["niveau_fr"] for m in matchs).most_common():
        print(f"   {niv:<14} {n}")

    if cl:
        print(f"\nCourbe de classement : {len(cl)} points, "
              f"{cl[0]['date']} -> {cl[-1]['date']}")
        print(f"   dernier point de la courbe : {cl[-1]['rang']}"
              f"   (rang actuel reel : {p['currentrank']})")


if __name__ == "__main__":
    donnees = charger()
    resume(donnees)

    with open("donnees.json", "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("\n-> Ecrit dans donnees.json")