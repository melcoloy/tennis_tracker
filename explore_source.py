"""
Étape 1 — Valider la source de données.

But : trouver l'identifiant d'Arthur Fils chez SofaScore, puis récupérer
une liste brute de ses matchs. On ne structure rien ici : on regarde
juste ce que l'API nous donne vraiment.

Usage :
    pip install requests
    python explore_source.py
"""

import json
import time
import requests

BASE = "https://api.sofascore.com/api/v1"

# Sans User-Agent, l'API renvoie souvent 403. On se présente comme un navigateur.
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0 Safari/537.36"),
    "Accept": "application/json",
})


def get(url):
    """Un GET qui explique ce qui s'est passé au lieu de planter bêtement."""
    r = SESSION.get(url, timeout=20)
    print(f"  GET {url} -> {r.status_code}")
    if r.status_code == 403:
        raise SystemExit("403 : l'API refuse. Regarde les headers dans F12 > Network.")
    if r.status_code == 429:
        raise SystemExit("429 : trop de requêtes, attends quelques minutes.")
    r.raise_for_status()
    return r.json()


def chercher_joueur(nom):
    """Cherche un nom et ne garde que les entités de tennis."""
    print(f"\n[1] Recherche de « {nom} »")
    data = get(f"{BASE}/search/all?q={nom.replace(' ', '%20')}")

    candidats = []
    for res in data.get("results", []):
        entite = res.get("entity", {})
        sport = (entite.get("sport") or {}).get("name", "")
        if sport == "Tennis" and res.get("type") in ("team", "player"):
            candidats.append({
                "id": entite.get("id"),
                "nom": entite.get("name"),
                "type": res.get("type"),
                "pays": (entite.get("country") or {}).get("name"),
            })

    for c in candidats:
        print(f"      id={c['id']:<10} {c['nom']:<25} type={c['type']}  {c['pays']}")
    if not candidats:
        raise SystemExit("Aucun joueur de tennis trouvé — le format de réponse a changé.")
    return candidats[0]


def recuperer_matchs(joueur_id, max_pages=3):
    """Récupère les matchs passés, page par page (les plus récents d'abord)."""
    print(f"\n[2] Matchs du joueur {joueur_id}")
    matchs = []
    for page in range(max_pages):
        data = get(f"{BASE}/team/{joueur_id}/events/last/{page}")
        events = data.get("events", [])
        print(f"      page {page} : {len(events)} matchs")
        matchs.extend(events)
        if not data.get("hasNextPage"):
            print("      -> fin de l'historique")
            break
        time.sleep(1)   # on ne martèle pas l'API
    return matchs


def apercu(matchs, n=5):
    """Affiche les n premiers matchs pour voir la tête des données."""
    print(f"\n[3] Aperçu ({len(matchs)} matchs au total)")
    for m in matchs[:n]:
        tournoi = (m.get("tournament") or {}).get("name", "?")
        dom = (m.get("homeTeam") or {}).get("name", "?")
        ext = (m.get("awayTeam") or {}).get("name", "?")
        date = time.strftime("%Y-%m-%d", time.localtime(m.get("startTimestamp", 0)))
        print(f"      {date}  {tournoi[:30]:<30}  {dom} vs {ext}")


if __name__ == "__main__":
    joueur = chercher_joueur("Arthur Fils")
    matchs = recuperer_matchs(joueur["id"])
    apercu(matchs)

    # On sauvegarde le brut : c'est ce qu'on lira à l'étape 2 pour concevoir models.py
    with open("brut_matchs.json", "w", encoding="utf-8") as f:
        json.dump(matchs, f, ensure_ascii=False, indent=2)
    print("\n-> Écrit dans brut_matchs.json")