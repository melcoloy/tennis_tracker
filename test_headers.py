"""
Diagnostic — quelle combinaison hôte + headers passe le filtre ?

On teste 4 configurations, de la plus simple à la plus complète.
La première qui renvoie 200 est celle qu'on gardera dans le projet.

    python test_headers.py
"""

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

REQUETE = "/search/all?q=Arthur%20Fils"

# Headers minimaux : juste se faire passer pour un navigateur
MINIMAL = {
    "User-Agent": UA,
    "Accept": "*/*",
}

# + Referer/Origin : on prétend venir du site lui-même.
# C'est souvent LA pièce manquante : l'API vérifie qui l'appelle.
AVEC_REFERER = {
    **MINIMAL,
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

# Panoplie complète : ce qu'un vrai Chrome envoie, y compris les headers sec-*
COMPLET = {
    **AVEC_REFERER,
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="120", "Not(A:Brand";v="24", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Cache-Control": "no-cache",
}

TESTS = [
    ("api.sofascore.com  + headers minimaux", "https://api.sofascore.com/api/v1", MINIMAL),
    ("api.sofascore.com  + referer",          "https://api.sofascore.com/api/v1", AVEC_REFERER),
    ("www.sofascore.com  + referer",          "https://www.sofascore.com/api/v1", AVEC_REFERER),
    ("www.sofascore.com  + panoplie complete", "https://www.sofascore.com/api/v1", COMPLET),
]


def essayer(nom, base, headers):
    url = base + REQUETE
    try:
        r = requests.get(url, headers=headers, timeout=20)
    except Exception as e:
        print(f"  [ERREUR] {nom:<40} {type(e).__name__}")
        return False

    marque = "OK  " if r.status_code == 200 else "FAIL"
    print(f"  [{marque}] {nom:<40} -> {r.status_code}")

    if r.status_code == 200:
        try:
            n = len(r.json().get("results", []))
            print(f"         {n} resultats recus. Base a utiliser : {base}")
        except Exception:
            print("         200 mais reponse illisible (page HTML ? protection Cloudflare ?)")
            return False
        return True

    # Un extrait du corps aide a distinguer un blocage Cloudflare d'un refus API
    extrait = r.text[:120].replace("\n", " ")
    print(f"         corps : {extrait}")
    return False


if __name__ == "__main__":
    print("Test des combinaisons :\n")
    for nom, base, headers in TESTS:
        if essayer(nom, base, headers):
            print("\n-> Combinaison trouvee, on s'arrete la.")
            break
    else:
        print("\n-> Aucune combinaison ne passe. Il faut recuperer les vrais headers"
              "\n   depuis le navigateur, ou changer de source.")