"""
patch_pronostics.py -- passe la section pronostics a plusieurs tournois.

A lancer une seule fois depuis la racine du projet :

    python patch_pronostics.py

Chaque modification verifie son repere avant d'agir : si un morceau ne
correspond pas, le script s'arrete sans rien ecrire plutot que de
corrompre le fichier en silence. Une copie .bak est faite d'abord.
"""

import shutil
import sys
from pathlib import Path

JS = Path("frontend/script.js")
HTML = Path("frontend/index.html")
CSS = Path("frontend/style.css")


def remplacer(texte, avant, apres, quoi):
    if avant not in texte:
        raise SystemExit(
            f"[ARRET] repere introuvable : {quoi}\n"
            f"Le fichier a peut-etre deja ete modifie, ou differe de celui "
            f"que j'ai lu. Rien n'a ete ecrit."
        )
    if texte.count(avant) > 1:
        raise SystemExit(f"[ARRET] repere ambigu ({texte.count(avant)} fois) : {quoi}")
    print(f"  ok  {quoi}")
    return texte.replace(avant, apres)


# --------------------------------------------------------------- script.js

JS_DECL_AV = """let PROCHAIN = null;
let PICKS = [];"""

JS_DECL_AP = """// Plusieurs tournois peuvent etre ouverts la meme semaine : prochain.json
// contient une liste, et l'URL (?prochain=<id>) designe celui affiche.
let PROCHAINS = [];
let PROCHAIN = null;
let PICKS = [];"""


JS_AFFICHE_AV = '''async function afficherProchain() {
  $("accueil").hidden = true;
  $("page").hidden = true;
  $("comparaison").hidden = true;
  $("tournois").hidden = true;
  $("chargement").hidden = false;
  $("chargement").textContent = "Chargement du tirage…";

  try {
    const url = STATIQUE
      ? `donnees/prochain.json${INDEX_STATIQUE && INDEX_STATIQUE.genere_le
          ? `?v=${encodeURIComponent(INDEX_STATIQUE.genere_le)}` : ""}`
      : "donnees/prochain.json";
    const r = await fetch(url);
    if (!r.ok) throw new Error(String(r.status));
    PROCHAIN = await r.json();
  } catch {
    $("chargement").textContent =
      "Aucun tirage publié pour l'instant. Il se prépare avec tirage.txt " +
      "puis python prochain.py.";
    return;
  }

  const n = PROCHAIN.joueurs.length;'''

JS_AFFICHE_AP = '''/** Tous les tirages publies, charges une seule fois. */
async function chargerProchains() {
  if (PROCHAINS.length) return PROCHAINS;

  const url = STATIQUE
    ? `donnees/prochain.json${INDEX_STATIQUE && INDEX_STATIQUE.genere_le
        ? `?v=${encodeURIComponent(INDEX_STATIQUE.genere_le)}` : ""}`
    : "donnees/prochain.json";

  const r = await fetch(url);
  if (!r.ok) throw new Error(String(r.status));
  const d = await r.json();

  // d.tournois est le format actuel ; un objet seul a la racine est
  // l'ancien, encore accepte pour ne pas casser un fichier deja publie.
  PROCHAINS = d.tournois || (d.joueurs ? [d] : []);
  return PROCHAINS;
}

async function afficherProchain(id) {
  $("accueil").hidden = true;
  $("page").hidden = true;
  $("comparaison").hidden = true;
  $("tournois").hidden = true;
  $("chargement").hidden = false;
  $("chargement").textContent = "Chargement du tirage…";

  let liste;
  try {
    liste = await chargerProchains();
    if (!liste.length) throw new Error("aucun tirage");
  } catch {
    $("chargement").textContent =
      "Aucun tirage publié pour l'instant. Il se prépare avec un fichier " +
      "dans tirages/ puis python prochain.py.";
    return;
  }

  // Sans identifiant valable, on ouvre le premier de la liste.
  PROCHAIN = liste.find((t) => t.id === id) || liste[0];

  // Selecteur, seulement s'il y a plusieurs tournois a departager.
  $("prc-choix").innerHTML = liste.length > 1
    ? liste.map((t) =>
        `<a class="prc-tab${t.id === PROCHAIN.id ? " actif" : ""}" ` +
        `href="?prochain=${t.id}">${t.nom}</a>`).join("")
    : "";

  const n = PROCHAIN.joueurs.length;'''


JS_BANDEAU_AV = '''  // Bandeau du prochain tournoi. Il ne s'affiche que si un tirage a
  // ete publie : sans prochain.json, le bloc reste masque.
  fetch("donnees/prochain.json")
    .then((r) => (r.ok ? r.json() : Promise.reject()))
    .then((p) => {
      $("ap-titre").textContent = p.nom;
      $("ap-detail").textContent =
        [p.date_fr, p.niveau, p.surface, `${p.joueurs.length} joueurs`]
          .filter(Boolean).join(" · ");
      $("acc-pronostic").hidden = false;
    })
    .catch(() => { $("acc-pronostic").hidden = true; });'''

JS_BANDEAU_AP = '''  // Un bandeau par tournoi a venir. Rien de publie, rien d'affiche.
  chargerProchains()
    .then((tirages) => {
      $("acc-pronostics").innerHTML = tirages.map((p) => `
        <a class="acc-pronostic" href="?prochain=${p.id}">
          <div class="ap-texte">
            <span class="ap-etiquette">Pronostics</span>
            <span class="ap-titre">${p.nom}</span>
            <span class="ap-detail">${
              [p.date_fr, p.niveau, p.surface, `${p.joueurs.length} joueurs`]
                .filter(Boolean).join(" · ")}</span>
          </div>
          <span class="ap-bouton">Remplir mon tableau →</span>
        </a>`).join("");
      $("acc-pronostics").hidden = !tirages.length;
    })
    .catch(() => { $("acc-pronostics").hidden = true; });'''


JS_ROUTE_AV = '''  if (params.has("prochain")) {
    await afficherProchain();
    return;
  }'''

JS_ROUTE_AP = '''  if (params.has("prochain")) {
    await afficherProchain(params.get("prochain"));
    return;
  }'''


# ------------------------------------------------------------- index.html

HTML_BANDEAU_AV = '''  <a class="acc-pronostic" id="acc-pronostic" href="?prochain" hidden>
    <div class="ap-texte">
      <span class="ap-etiquette">Pronostics</span>
      <span class="ap-titre" id="ap-titre">—</span>
      <span class="ap-detail" id="ap-detail">—</span>
    </div>
    <span class="ap-bouton">Remplir mon tableau →</span>
  </a>'''

HTML_BANDEAU_AP = '''  <div class="acc-pronostics" id="acc-pronostics" hidden></div>'''


HTML_CHOIX_AV = '''    <h1 id="prc-titre">Prochain tournoi</h1>
    <p class="trn-intro" id="prc-intro"></p>
  </header>'''

HTML_CHOIX_AP = '''    <h1 id="prc-titre">Prochain tournoi</h1>
    <p class="trn-intro" id="prc-intro"></p>
    <div class="prc-choix" id="prc-choix"></div>
  </header>'''


CSS_AJOUT = '''

/* ------------------------------------------- plusieurs tournois ouverts */

.acc-pronostics { display: flex; flex-direction: column; gap: 12px; margin: 42px 0 0; }
.acc-pronostics .acc-pronostic { margin: 0; }

.prc-choix { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 20px; }

.prc-tab {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: .1em;
  text-transform: uppercase;
  padding: 9px 15px;
  border: 1px solid var(--trait);
  border-radius: 5px;
  color: var(--sourdine);
  text-decoration: none;
  transition: border-color .14s, color .14s;
}

.prc-tab:hover { color: var(--texte); }
.prc-tab.actif { border-color: var(--dur); color: var(--texte); background: var(--panneau); }
'''


def main():
    for f in (JS, HTML, CSS):
        if not f.exists():
            raise SystemExit(f"[ARRET] {f} introuvable. Lance le script "
                             f"depuis la racine du projet.")
        shutil.copy2(f, f.with_suffix(f.suffix + ".bak"))
    print("copies de secours : *.bak\n")

    print("script.js")
    js = JS.read_text(encoding="utf-8")
    js = remplacer(js, JS_DECL_AV, JS_DECL_AP, "declaration des tirages")
    js = remplacer(js, JS_AFFICHE_AV, JS_AFFICHE_AP, "chargement et selecteur")
    js = remplacer(js, JS_BANDEAU_AV, JS_BANDEAU_AP, "bandeaux de l'accueil")
    js = remplacer(js, JS_ROUTE_AV, JS_ROUTE_AP, "routage ?prochain=<id>")

    print("\nindex.html")
    html = HTML.read_text(encoding="utf-8")
    html = remplacer(html, HTML_BANDEAU_AV, HTML_BANDEAU_AP, "bandeau accueil")
    html = remplacer(html, HTML_CHOIX_AV, HTML_CHOIX_AP, "selecteur de tournoi")

    print("\nstyle.css")
    css = CSS.read_text(encoding="utf-8")
    if ".prc-tab" in css:
        print("  ok  styles deja presents")
    else:
        css += CSS_AJOUT
        print("  ok  styles ajoutes")

    # On n'ecrit qu'une fois TOUTES les modifications validees.
    JS.write_text(js, encoding="utf-8")
    HTML.write_text(html, encoding="utf-8")
    CSS.write_text(css, encoding="utf-8")

    print("\nTermine. Ensuite :")
    print("  python prochain.py")
    print("  python publier.py")


if __name__ == "__main__":
    main()