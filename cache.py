"""
cache.py -- copies locales des pages Tennis Abstract, un fichier par joueur.

Regle : on ne retelecharge que si la copie a plus de 24 h.
"""

import html as _html
import re
import time
import unicodedata
from pathlib import Path

import requests

GABARIT_URL = "https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p={slug}"


class TropDeRequetes(Exception):
    """Le site a repondu 429. Porte le delai d'attente conseille."""

    def __init__(self, secondes):
        self.secondes = secondes
        super().__init__(f"429 -- reessayer dans {secondes} s")

DOSSIER = Path("cache")
DUREE_VIE = 24 * 3600

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
}



def _decoder(reponse):
    """
    Choisit le bon encodage avant de lire le texte.

    Quand un serveur ne declare pas de charset, requests suppose
    Latin-1 (heritage de la specification HTTP). live-tennis.eu sert
    de l'UTF-8 sans le declarer : sans ce correctif, 'Felix' devient
    'FA©lix' et l'identifiant qui en decoule n'existe pas.
    """
    if "charset" not in reponse.headers.get("Content-Type", "").lower():
        reponse.encoding = reponse.apparent_encoding or "utf-8"
    return reponse.text

# Lettres latines que NFD ne decompose pas : ce ne sont pas des lettres
# accentuees mais des caracteres a part entiere. Sans cette table,
# 'Elmer Moller' garde son 'o' barre et l'identifiant est rejete.
LETTRES_SPECIALES = str.maketrans({
    "\u00f8": "o", "\u00d8": "O",      # o barre (danois, norvegien)
    "\u0111": "d", "\u0110": "D",      # d barre (croate, serbe)
    "\u0142": "l", "\u0141": "L",      # l barre (polonais)
    "\u00e6": "ae", "\u00c6": "Ae",
    "\u0153": "oe", "\u0152": "Oe",
    "\u00df": "ss",
    "\u00fe": "th", "\u00de": "Th",
    "\u00f0": "d", "\u00d0": "D",
    "\u0131": "i", "\u0130": "I",      # i sans point (turc)
})


def slugifier(nom):
    """
    'Felix Auger-Aliassime' -> 'FelixAugerAliassime'

    Tennis Abstract identifie ses joueurs par leur nom sans accent,
    sans espace ni tiret, chaque mot capitalise.
    """
    # Les noms peuvent arriver avec des entites HTML et des symboles :
    # live-tennis.eu prefixe d'une coche les qualifies pour le Masters.
    propre = _html.unescape(nom).replace("\xa0", " ").translate(LETTRES_SPECIALES)

    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", propre)
        if unicodedata.category(c) != "Mn"
    )
    mots = re.split(r"[\s\-']+", sans_accent.strip())

    # tout ce qui n'est pas une lettre est ecarte : un symbole laisse
    # dans le slug le rend introuvable, sans aucune erreur visible
    mots = ["".join(c for c in m if c.isalpha()) for m in mots]
    return "".join(m[:1].upper() + m[1:] for m in mots if m)


def valider(slug):
    """
    Le slug finit dans un nom de fichier ET dans une URL.

    Sans ce filtre, '../../etc/passwd' passerait par la case chemin.
    On n'accepte que des lettres.
    """
    if not slug or not re.fullmatch(r"[A-Za-z]{2,60}", slug):
        raise ValueError(f"identifiant de joueur invalide : {slug!r}")
    return slug


def chemin(slug):
    return DOSSIER / f"page_{valider(slug)}.html"


def age_secondes(slug):
    f = chemin(slug)
    return None if not f.exists() else time.time() - f.stat().st_mtime


def est_perimee(slug):
    age = age_secondes(slug)
    return age is None or age > DUREE_VIE


def rafraichir(slug, force=False):
    """
    Renvoie (a_telecharge, message).

    Ecriture atomique, et en cas d'echec on garde la copie existante :
    des donnees d'hier valent mieux qu'une page d'erreur.
    """
    valider(slug)
    DOSSIER.mkdir(exist_ok=True)

    fichier = chemin(slug)
    age = age_secondes(slug)

    if not force and not est_perimee(slug):
        return False, f"copie locale a jour ({age / 3600:.1f} h)"

    temporaire = fichier.with_suffix(".tmp")
    try:
        r = requests.get(GABARIT_URL.format(slug=slug), headers=HEADERS, timeout=30)

        # Tennis Abstract applique un seau a jetons : une petite rafale
        # passe, puis il faut laisser les jetons se reconstituer.
        if r.status_code == 429:
            attente = r.headers.get("Retry-After")
            raise TropDeRequetes(int(attente) if attente and attente.isdigit() else 30)

        r.raise_for_status()
        texte = _decoder(r)

        # Tennis Abstract renvoie 200 avec une page quasi vide pour un
        # identifiant inconnu : on verifie la presence des donnees.
        if len(texte) < 50_000 or not re.search(r"var\s+matchmx\s*=\s*\[", texte):
            raise ValueError(
                f"page inexploitable pour '{slug}' "
                f"({len(texte)} caracteres, matchmx absent) -- "
                f"cet identifiant existe-t-il sur Tennis Abstract ?"
            )

        temporaire.write_text(texte, encoding="utf-8")
        temporaire.replace(fichier)
        return True, f"page rafraichie ({len(texte)} caracteres)"

    except TropDeRequetes:
        temporaire.unlink(missing_ok=True)
        raise

    except Exception as e:
        temporaire.unlink(missing_ok=True)
        if fichier.exists():
            return False, f"echec ({type(e).__name__}) -- on garde la copie du disque"
        raise RuntimeError(f"aucune copie locale pour '{slug}' : {e}")


def joueurs_en_cache():
    """Liste des slugs deja telecharges."""
    if not DOSSIER.is_dir():
        return []
    return sorted(f.stem.removeprefix("page_") for f in DOSSIER.glob("page_*.html"))


if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "ArthurFils"
    print(f"{slug} : {rafraichir(slug)[1]}")
    print("en cache :", joueurs_en_cache())