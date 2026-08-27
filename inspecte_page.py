"""
Inspection de la page Tennis Abstract.

La page pese 350 Ko : les donnees sont dedans, dans des variables JS.
Ce script ne devine rien -- il liste tout ce qu'il trouve, pour qu'on
voie de nos yeux ou sont les matchs.

    python inspecte_page.py
"""

import re
import requests

URL = "https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p=ArthurFils"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
}


def recuperer():
    print(f"Telechargement de {URL}")
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    print(f"  -> {r.status_code}, {len(r.text)} caracteres\n")

    # On garde une copie locale : on pourra la relire sans retaper le site
    with open("page_fils.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("  copie sauvegardee dans page_fils.html\n")
    return r.text


def inventaire_variables(html):
    """Liste toutes les variables JS declarees, triees par taille."""
    print("=" * 70)
    print("VARIABLES JAVASCRIPT TROUVEES (les plus grosses en premier)")
    print("=" * 70)

    trouvees = []
    # On repere 'var nom =' puis on prend ce qui suit jusqu'au prochain 'var '
    # ou la fin du script. Approximatif mais suffisant pour un inventaire.
    for m in re.finditer(r"var\s+([A-Za-z_$][\w$]*)\s*=\s*", html):
        nom = m.group(1)
        debut = m.end()
        suite = html[debut:debut + 400000]
        fin = re.search(r";\s*\n|\n\s*var\s+", suite)
        contenu = suite[:fin.start()] if fin else suite[:1000]
        trouvees.append((len(contenu), nom, contenu))

    trouvees.sort(reverse=True)

    for taille, nom, contenu in trouvees[:25]:
        apercu = contenu[:180].replace("\n", " ").replace("\r", "")
        print(f"\n  {nom}  ({taille} caracteres)")
        print(f"     {apercu}")

    print(f"\n  ... {len(trouvees)} variables au total")
    return trouvees


def cherche_indices(html):
    """Cherche des mots-cles revelateurs pour se reperer."""
    print("\n" + "=" * 70)
    print("INDICES")
    print("=" * 70)

    for mot in ["Cincinnati", "Tiafoe", "2019", "2020", "Challenger",
                "ITF", "matchmx", "Roland", "Wimbledon"]:
        n = html.count(mot)
        print(f"  '{mot}' apparait {n} fois")


if __name__ == "__main__":
    html = recuperer()
    inventaire_variables(html)
    cherche_indices(html)
    print("\n-> Colle cette sortie : on saura quelle variable contient les matchs.")