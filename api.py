"""
api.py -- l'API du tracker.

    uvicorn api:app --reload

Tous les endpoints acceptent ?joueur=<identifiant Tennis Abstract>,
par exemple ArthurFils, CarlosAlcaraz, JannikSinner. Par defaut :
ArthurFils.

Documentation interactive : http://127.0.0.1:8000/docs
"""

from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import annuaire
import cache
import race
import source
import tournois

JOUEUR_DEFAUT = "ArthurFils"

app = FastAPI(title="Tracker de carriere ATP", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Donnees analysees, une entree par joueur. Reparser 350 Ko de HTML a
# chaque requete serait absurde ; on invalide sur la date de
# modification du fichier.
_memoire = {}


def donnees(slug):
    try:
        cache.valider(slug)
        cache.rafraichir(slug)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(404, str(e))

    fichier = cache.chemin(slug)
    if not fichier.exists():
        raise HTTPException(404, f"aucune donnee pour '{slug}'")

    mtime = fichier.stat().st_mtime
    entree = _memoire.get(slug)
    if entree is None or entree["mtime"] != mtime:
        entree = {"mtime": mtime, "data": source.charger(str(fichier))}
        _memoire[slug] = entree
    return entree["data"]


def J(joueur: str = Query(JOUEUR_DEFAUT, description="identifiant Tennis Abstract")):
    """Dependance commune : le joueur demande."""
    return joueur


def _fr(d):
    return f"{d[6:]}/{d[4:6]}/{d[:4]}" if len(d) == 8 else d


def _entier(v):
    """
    Rang eventuellement absent ou non numerique.

    Un joueur retire n'a plus de classement : Tennis Abstract laisse
    le champ vide, ou y met 'UNR'. On renvoie None plutot que de
    planter -- toute la carriere reste consultable.
    """
    try:
        return int(str(v).strip().strip('"\''))
    except (TypeError, ValueError):
        return None


def _bilan(matchs):
    v = sum(1 for m in matchs if m.get("wl") == "W")
    n = len(matchs)
    return {"joues": n, "gagnes": v, "perdus": n - v,
            "pourcentage": round(100 * v / n, 1) if n else 0}


# --------------------------------------------------------------- endpoints

@app.get("/api/joueurs")
def joueurs():
    """Les joueurs deja telecharges, plus celui par defaut."""
    return {"en_cache": cache.joueurs_en_cache(), "defaut": JOUEUR_DEFAUT}


@app.get("/api/annuaire")
def liste_joueurs():
    """
    Joueurs classes, pour l'autocompletion du champ de recherche.

    Renvoyee en une fois : quelques centaines de noms tiennent dans
    une reponse legere, et le navigateur filtre ensuite tout seul.
    Pas besoin d'une requete par frappe.
    """
    j = annuaire.charger()
    return {"total": len(j), "joueurs": j}


@app.get("/api/profil")
def profil(joueur: str = Query(JOUEUR_DEFAUT)):
    d = donnees(joueur)
    p = dict(d["profil"])
    p["slug"] = joueur
    p["nb_matchs"] = len(d["matchs"])
    p["victoires"] = sum(1 for m in d["matchs"] if m.get("wl") == "W")
    p["defaites"] = sum(1 for m in d["matchs"] if m.get("wl") == "L")
    p["peakfirst_fr"] = _fr(p.get("peakfirst") or "")
    p["actif"] = _entier(p.get("currentrank")) is not None
    p["cache_age_heures"] = round((cache.age_secondes(joueur) or 0) / 3600, 1)

    # La Race vient d'une autre source : si elle tombe, le reste de la
    # page doit continuer a s'afficher.
    try:
        r = race.charger(joueur, p["fullname"])
        p["race_position"] = r["position"]
        p["race_points"] = r.get("points")
        p["race_releve_le"] = _fr(r.get("releve_le", ""))
        p["race_automatique"] = r.get("automatique", False)
    except Exception as e:
        p["race_position"] = None
        p["race_note"] = str(e)

    return p


@app.get("/api/matchs")
def matchs(
    joueur: str = Query(JOUEUR_DEFAUT),
    annee: str | None = Query(None),
    niveau: str | None = Query(None, description="code brut : M, C, G, 15..."),
    resultat: str | None = Query(None, description="W ou L"),
    adversaire: str | None = Query(None),
    limite: int = Query(100, ge=1, le=2000),
):
    resultats = donnees(joueur)["matchs"]

    if annee:
        resultats = [m for m in resultats if m.get("date", "").startswith(annee)]
    if niveau:
        resultats = [m for m in resultats if m.get("level") == niveau]
    if resultat:
        resultats = [m for m in resultats if m.get("wl") == resultat.upper()]
    if adversaire:
        q = adversaire.lower()
        resultats = [m for m in resultats if q in m.get("opp", "").lower()]

    resultats = sorted(resultats, key=lambda m: m.get("date", ""), reverse=True)

    return {
        "total": len(resultats),
        "matchs": [
            {
                "date": m["date"],
                "date_fr": _fr(m["date"]),
                "tournoi": m["tourn"],
                "niveau": m["niveau_fr"],
                "niveau_code": m.get("level", ""),
                "surface": m["surf"],
                "tour": m["round"],
                "resultat": m["wl"],
                "adversaire": m["opp"],
                "rang_adversaire": m.get("orank", ""),
                "score": m["score"],
                "rang_joueur": m.get("rank", ""),
            }
            for m in resultats[:limite]
        ],
    }


@app.get("/api/classement")
def classement(joueur: str = Query(JOUEUR_DEFAUT)):
    d = donnees(joueur)
    return {
        "rang_actuel": _entier(d["profil"]["currentrank"]),
        "meilleur_rang": _entier(d["profil"]["peakrank"]),
        "rang_elo": d["profil"].get("elo_rank"),
        # La courbe s'arrete au dernier tournoi joue : elle ne contient
        # pas le classement publie depuis. D'ou rang_actuel a part.
        "courbe": [
            {"date": c["date"], "date_fr": _fr(c["date"]), "rang": c["rang"]}
            for c in d["classement"]
        ],
    }


@app.get("/api/stats")
def stats(joueur: str = Query(JOUEUR_DEFAUT)):
    matchs = donnees(joueur)["matchs"]

    par_annee, par_niveau, par_surface = defaultdict(list), defaultdict(list), defaultdict(list)
    for m in matchs:
        if m.get("date"):
            par_annee[m["date"][:4]].append(m)
        par_niveau[m["niveau_fr"]].append(m)
        par_surface[m.get("surf") or "?"].append(m)

    titres = [
        {"date_fr": _fr(m["date"]), "tournoi": m["tourn"],
         "niveau": m["niveau_fr"], "adversaire": m["opp"], "score": m["score"]}
        for m in sorted(matchs, key=lambda x: x.get("date", ""), reverse=True)
        if m.get("round") == "F" and m.get("wl") == "W"
    ]

    return {
        "global": _bilan(matchs),
        "par_annee": {a: _bilan(v) for a, v in sorted(par_annee.items())},
        "par_niveau": {n: _bilan(v) for n, v in par_niveau.items()},
        "par_surface": {s: _bilan(v) for s, v in par_surface.items()},
        "titres": titres,
        "nb_titres": len(titres),
    }


@app.get("/api/recherche")
def recherche(nom: str = Query(..., min_length=2, description="ex. Carlos Alcaraz")):
    """Convertit un nom saisi en identifiant Tennis Abstract et le teste."""
    slug = cache.slugifier(nom)
    try:
        cache.valider(slug)
        cache.rafraichir(slug)
    except (ValueError, RuntimeError) as e:
        return {"trouve": False, "slug": slug, "message": str(e)}

    d = donnees(slug)
    return {"trouve": True, "slug": slug,
            "nom": d["profil"]["fullname"],
            "nb_matchs": len(d["matchs"])}


@app.get("/api/tournois")
def liste_tournois(limite: int = Query(60, ge=1, le=300)):
    """
    Tableaux reconstitues a partir des joueurs deja telecharges.

    Plus la base compte de joueurs, plus les tableaux sont complets.
    """
    pour = []
    for slug in cache.joueurs_en_cache():
        try:
            d = donnees(slug)
        except Exception:
            continue
        pour.append((slug, d["profil"]["fullname"],
                     matchs(joueur=slug, annee=None, niveau=None, resultat=None,
                            adversaire=None, limite=2000)["matchs"]))

    return {"tournois": tournois.construire(pour, cache.slugifier, limite)}


@app.post("/api/rafraichir")
def forcer(joueur: str = Query(JOUEUR_DEFAUT)):
    telecharge, message = cache.rafraichir(joueur, force=True)
    return {"telecharge": telecharge, "message": message}


if Path("frontend").is_dir():
    app.mount("/", StaticFiles(directory="frontend", html=True), name="front")