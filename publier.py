"""
publier.py -- une seule commande pour mettre le site a jour.

Remplace la sequence : lancer le serveur, consulter chaque joueur,
python figer.py, cd site, git add, git commit, git push.

    python publier.py                 # rafraichit les joueurs deja publies
    python publier.py --top 50        # ajoute le top 50 mondial
    python publier.py --legendes      # ajoute les grands joueurs retires
    python publier.py CarlosAlcaraz JannikSinner
    python publier.py --top 100 --sans-push   # construit sans publier

Les telechargements sont espaces d'une seconde : on tire des centaines
de pages du site de quelqu'un d'autre, autant rester poli.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import annuaire
import cache
import figer

PAUSE_INITIALE = 3.0    # secondes entre deux telechargements
PAUSE_MAX = 25.0
ESSAIS = 4              # tentatives par joueur avant d'abandonner

# Le dernier --top utilise est memorise ici, pour que la commande nue
# fasse la meme chose que la derniere fois. Sans ca, un joueur entrant
# dans le top 100 ne serait jamais ajoute : la commande nue ne reprend
# que les joueurs deja publies.
REGLAGES = Path("publication.json")

# live-tennis.eu et Tennis Abstract n'ecrivent pas certains noms pareil.
# Ce fichier retient les correspondances trouvees, pour ne pas retenter
# indefiniment un identifiant qu'on sait faux.
#   "AleksandrShevchenko": "AlexanderShevchenko"   -> remplace
#   "UnJoueurSansPage": null                       -> ignore
CORRECTIONS = Path("corrections.json")

# Les grands joueurs retires ne figurent dans aucun classement, donc
# --top ne les atteindra jamais. On les nomme explicitement.
# Si un identifiant echoue, trouver_slug.py donnera le bon.
LEGENDES = [
    "RogerFederer", "RafaelNadal", "AndyMurray", "NovakDjokovic",
    "PeteSampras", "AndreAgassi", "BjornBorg", "JohnMcEnroe",
    "IvanLendl", "JimmyConnors", "StefanEdberg", "BorisBecker",
    "MatsWilander", "JimCourier", "GustavoKuerten", "MaratSafin",
    "JuanCarlosFerrero", "AndyRoddick", "LleytonHewitt", "CarlosMoya",
    "GoranIvanisevic", "MichaelChang", "YevgenyKafelnikov",
    "JuanMartinDelPotro", "StanWawrinka", "DavidFerrer",
    "TomasBerdych", "JoWilfriedTsonga", "DominicThiem",
    "KeiNishikori", "MilosRaonic", "RichardGasquet",
]


def corriger(slugs):
    """Applique les correspondances connues et retire les slugs a ignorer."""
    if not CORRECTIONS.exists():
        return slugs

    table = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    sortie, remplaces = [], 0
    for s in slugs:
        if s not in table:
            sortie.append(s)
        elif table[s]:
            sortie.append(table[s])
            remplaces += 1
        else:
            remplaces += 1

    if remplaces:
        print(f"{remplaces} identifiants corriges depuis {CORRECTIONS.name}")
    return sortie


def telecharger(slugs):
    """
    Met en cache les pages manquantes ou perimees.

    Tennis Abstract applique un seau a jetons : un rythme fixe finit
    toujours par se faire refuser. On s'adapte donc au site plutot que
    de lui imposer une cadence -- on ralentit apres chaque 429, et on
    accelere doucement quand tout se passe bien.
    """
    a_faire = [s for s in slugs if cache.est_perimee(s)]
    if not a_faire:
        print(f"{len(slugs)} joueurs deja en cache et a jour.")
        return slugs

    pause = PAUSE_INITIALE
    print(f"{len(a_faire)} pages a telecharger, cadence adaptative "
          f"(compte {len(a_faire) * pause / 60:.0f} min au minimum)\n")

    ok = [s for s in slugs if s not in a_faire]
    abandons = []

    for i, slug in enumerate(a_faire, 1):
        for essai in range(1, ESSAIS + 1):
            try:
                _, message = cache.rafraichir(slug)
                print(f"  [{i:>3}/{len(a_faire)}] {slug:<28} {message}")
                ok.append(slug)
                pause = max(PAUSE_INITIALE, pause * 0.9)   # on relache
                break

            except cache.TropDeRequetes as e:
                pause = min(PAUSE_MAX, pause * 1.8)        # on ralentit
                attente = max(e.secondes, pause)
                if essai == ESSAIS:
                    print(f"  [{i:>3}/{len(a_faire)}] {slug:<28} reporte "
                          f"(limite de debit)")
                    abandons.append(slug)
                    break
                print(f"  [{i:>3}/{len(a_faire)}] {slug:<28} 429, "
                      f"pause {attente:.0f} s (essai {essai}/{ESSAIS})")
                time.sleep(attente)

            except Exception as e:
                print(f"  [{i:>3}/{len(a_faire)}] {slug:<28} ECHEC -- {e}")
                abandons.append(slug)
                break

        time.sleep(pause)

    print(f"\n{len(ok)} joueurs disponibles")
    if abandons:
        print(f"{len(abandons)} reportes : relance la meme commande "
              f"plus tard, ils seront repris.")
    return ok


def git(*args):
    """Lance une commande git dans site/ et renvoie sa sortie."""
    r = subprocess.run(["git", *args], cwd=figer.SORTIE,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def pousser():
    code, _ = git("rev-parse", "--git-dir")
    if code != 0:
        print("\nsite/ n'est pas un depot git : rien a pousser d'ici.")
        print("La mise en ligne est faite par GitHub Actions -- soit chaque")
        print("lundi, soit a la demande depuis l'onglet Actions du depot.")
        print("Pour verifier en local : cd site && python -m http.server 8080")
        return

    code, sortie = git("status", "--porcelain")
    if not sortie:
        print("\nAucun changement a publier.")
        return

    n = len(sortie.splitlines())
    print(f"\n{n} fichiers modifies, publication...")

    git("add", "-A")
    code, _ = git("commit", "-m", f"maj {time.strftime('%Y-%m-%d %H:%M')}")
    code, sortie = git("push")

    if code == 0:
        print("Publie. Le site sera a jour dans une a deux minutes.")
    else:
        print(f"Echec du push :\n{sortie}")


def main(args):
    global PAUSE_INITIALE
    sans_push = "--sans-push" in args
    args = [a for a in args if a != "--sans-push"]

    if "--pause" in args:
        i = args.index("--pause")
        PAUSE_INITIALE = float(args[i + 1])
        args = args[:i] + args[i + 2:]

    legendes = "--legendes" in args
    args = [a for a in args if a != "--legendes"]

    slugs = []

    top = None
    if "--top" in args:
        i = args.index("--top")
        top = int(args[i + 1])
        args = args[:i] + args[i + 2:]
        anciens = (json.loads(REGLAGES.read_text(encoding="utf-8"))
                   if REGLAGES.exists() else {})
        anciens["top"] = top
        REGLAGES.write_text(json.dumps(anciens), encoding="utf-8")
    elif REGLAGES.exists():
        top = json.loads(REGLAGES.read_text(encoding="utf-8")).get("top")
        if top:
            print(f"top {top} memorise lors d'une execution precedente "
                  f"(--top 0 pour ne plus le suivre)")

    if top:
        n = top
        classes = annuaire.charger()
        if not classes:
            print("Annuaire indisponible : on se limite aux joueurs deja publies.")
            classes = []
        slugs += [j["slug"] for j in classes[:n]]
        print(f"top {n} mondial : {len(classes[:n])} joueurs vises")

    reglages = (json.loads(REGLAGES.read_text(encoding="utf-8"))
                if REGLAGES.exists() else {})

    if legendes:
        reglages["legendes"] = True
        REGLAGES.write_text(json.dumps(reglages), encoding="utf-8")

    if reglages.get("legendes"):
        slugs += LEGENDES
        print(f"{len(LEGENDES)} legendes incluses")

    slugs += args                              # slugs passes en clair
    slugs += cache.joueurs_en_cache()          # et les deja publies

    slugs = corriger(slugs)

    vus, uniques = set(), []
    for s in slugs:
        if s not in vus:
            vus.add(s)
            uniques.append(s)

    if not uniques:
        print("Rien a faire. Essaie : python publier.py --top 50")
        return

    disponibles = telecharger(uniques)
    print()
    figer.construire(disponibles)

    if not sans_push:
        pousser()


if __name__ == "__main__":
    main(sys.argv[1:])