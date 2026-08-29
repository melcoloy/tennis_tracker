/* Front du tracker. Aucune bibliotheque : les deux graphiques sont
   dessines a la main en SVG. Moins de dependances, et on controle
   exactement ce qui est trace. */

const API = "http://127.0.0.1:8000";

// Le joueur est dans l'URL : ?joueur=CarlosAlcaraz. Partageable,
// et le bouton Precedent du navigateur fonctionne naturellement.
let SLUG = new URLSearchParams(location.search).get("joueur") || "ArthurFils";
const SVG_NS = "http://www.w3.org/2000/svg";

const SURFACES = {
  Hard:  { nom: "Dur",          couleur: "var(--dur)" },
  Clay:  { nom: "Terre battue", couleur: "var(--terre)" },
  Grass: { nom: "Gazon",        couleur: "var(--gazon)" },
};

// Paliers, du plus haut au plus bas. Un match sait a quelle bande il va
// par son code de niveau brut.
const PALIERS = [
  { nom: "Grand Chelem",  codes: ["G"] },
  { nom: "Masters 1000",  codes: ["M"] },
  { nom: "ATP / autres",  codes: ["A", "F", "D", "O"] },
  { nom: "Challenger",    codes: ["C"] },
  { nom: "ITF",           codes: ["15", "25"] },
];

let MATCHS = [];

/* ------------------------------------------------------------- outils */

function $(id) {
  const n = document.getElementById(id);
  if (!n) throw new Error(`identifiant absent de index.html : #${id}`);
  return n;
}

function el(nom, attrs = {}, parent = null) {
  const n = document.createElementNS(SVG_NS, nom);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
}

/** "20260813" -> objet Date */
function versDate(s) {
  return new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8));
}

function couleurSurface(surf) {
  return (SURFACES[surf] || {}).couleur || "var(--sourdine)";
}

function palierDe(code) {
  return PALIERS.findIndex((p) => p.codes.includes(code));
}

async function json(chemin, slug, options) {
  const sep = chemin.includes("?") ? "&" : "?";
  const r = await fetch(`${API}${chemin}${sep}joueur=${encodeURIComponent(slug)}`, options);
  if (!r.ok) throw new Error(`${chemin} a repondu ${r.status}`);
  return r.json();
}

/* Deux modes de fonctionnement :
     - DYNAMIQUE : le serveur FastAPI tourne, on interroge /api/...
     - STATIQUE  : site publie (GitHub Pages), on lit des JSON figes.

   La bascule ne repose pas sur le nom d'hote ni sur une configuration,
   mais sur la presence de donnees/index.json, fabrique par figer.py.
   Le meme dossier frontend/ marche donc dans les deux cas. */

let STATIQUE = false;
let INDEX_STATIQUE = null;

async function detecterMode() {
  try {
    const r = await fetch("donnees/index.json", { cache: "no-store" });
    if (r.ok) {
      INDEX_STATIQUE = await r.json();
      STATIQUE = true;
    }
  } catch {
    STATIQUE = false;
  }
  return STATIQUE;
}

/** Renvoie { profil, classement, stats, matchs }, quel que soit le mode. */
async function chargerTout(slug) {
  if (STATIQUE) {
    // Le nom du fichier ne change jamais alors que son contenu change
    // a chaque publication : sans ce parametre, le navigateur peut
    // servir indefiniment une version perimee. La date de generation
    // vient d'index.json, lui-meme demande en no-store.
    const version = INDEX_STATIQUE && INDEX_STATIQUE.genere_le
      ? `?v=${encodeURIComponent(INDEX_STATIQUE.genere_le)}`
      : "";
    const r = await fetch(`donnees/${slug}.json${version}`);
    if (!r.ok) throw new Error(`${slug} n'a pas ete inclus dans cette publication`);
    return r.json();
  }

  const [profil, classement, stats, matchs] = await Promise.all([
    json("/api/profil", slug),
    json("/api/classement", slug),
    json("/api/stats", slug),
    json("/api/matchs?limite=2000", slug),
  ]);
  return { profil, classement, stats, matchs };
}

/* ------------------------------------------------------------- entete */

function dessinerEntete(profil) {
  const main = profil.hand === "R" ? "droitier" : "gaucher";
  const revers = profil.backhand === "2" ? "revers à deux mains" : "revers à une main";

  $("eyebrow").textContent =
    `${profil.nb_matchs} matchs · ${profil.victoires} v. ${profil.defaites} d.`;
  const ne = profil.dob && profil.dob.length === 8
    ? ` (né le ${profil.dob.slice(6)}/${profil.dob.slice(4, 6)}/${profil.dob.slice(0, 4)})`
    : "";

  $("bio").textContent =
    `${profil.age} ans${ne} · ${profil.ht} cm · ${main}, ${revers} · ${profil.country}` +
    (profil.actif ? "" : " · retiré du circuit");
  $("nom-joueur").textContent = profil.fullname;
  document.title = `${profil.fullname} — la montée`;
  // Un joueur retire n'a ni classement ATP, ni Race, ni Elo. Afficher
  // trois "#—" alignes est du bruit : on masque simplement les blocs
  // sans valeur, et le libelle du premier porte l'information.
  const propre = (v) => String(v ?? "").replace(/["']/g, "").trim();

  const rang = propre(profil.currentrank);
  const peak = propre(profil.peakrank);
  const elo = propre(profil.elo_rank);
  const race = profil.race_position ? String(profil.race_position) : "";

  const actif = Boolean(rang);

  const blocs = [
    ["rang-actuel", rang],
    ["rang-peak", peak && peak !== "UNR" ? peak : ""],
    ["rang-race", race],
    ["rang-elo", elo],
  ];

  blocs.forEach(([id, valeur]) => {
    const bloc = $(id).parentElement;
    bloc.hidden = !valeur;
    if (valeur) $(id).textContent = valeur;
  });

  $("rang-peak-date").textContent =
    profil.peakfirst_fr ? `atteint le ${profil.peakfirst_fr}` : "";

  // le meilleur classement devient la valeur mise en avant
  $("rang-actuel").parentElement.classList.toggle("rang--principal", actif);
  $("rang-peak").parentElement.classList.toggle("rang--principal", !actif);

  // En mode statique ces champs sont sortis des fichiers joueurs (ils
  // changeaient a chaque publication et faisaient grossir le depot) ;
  // le pied de page est de toute facon reecrit ensuite.
  $("fraicheur").textContent = profil.cache_age_heures === undefined
    ? race
    : `données mises à jour il y a ${profil.cache_age_heures} h · ${race}`;
}

/** Position horizontale du pointeur, exprimee dans le viewBox du SVG. */
function xDansSvg(svg, ev, largeurViewBox) {
  const boite = svg.getBoundingClientRect();
  return ((ev.clientX - boite.left) / boite.width) * largeurViewBox;
}

/* -------------------------------------------------- SIGNATURE : la frise */

// Ordre des tours, pour retrouver le match le plus avance d'un tournoi.
const TOURS = {
  Q1: 0, Q2: 1, Q3: 2, R128: 3, R64: 4, R32: 5, RR: 5.5,
  R16: 6, QF: 7, SF: 8, BR: 8.5, F: 9,
};

const NOM_TOUR = {
  F: "finale", SF: "demi-finale", QF: "quart de finale",
  R16: "8e de finale", R32: "16e de finale", R64: "32e de finale",
  R128: "64e de finale", RR: "phase de poules", BR: "match pour la 3e place",
  Q1: "qualifications", Q2: "qualifications", Q3: "qualifications",
};

/** Une phrase decrivant le parcours dans un tournoi. */
function resumerTournoi(liste) {
  const v = liste.filter((m) => m.resultat === "W").length;
  const d = liste.length - v;

  // le match le plus avance, pas le premier de la liste
  const dernier = liste.reduce((a, b) =>
    (TOURS[b.tour] ?? -1) > (TOURS[a.tour] ?? -1) ? b : a);

  let issue;
  if (dernier.tour === "F" && dernier.resultat === "W") {
    issue = `TITRE — victoire en finale contre ${dernier.adversaire} (${dernier.score})`;
  } else if (dernier.tour === "F") {
    issue = `finaliste — battu par ${dernier.adversaire} (${dernier.score})`;
  } else if (dernier.resultat === "L") {
    issue = `éliminé en ${NOM_TOUR[dernier.tour] || dernier.tour} ` +
            `par ${dernier.adversaire} (${dernier.score})`;
  } else {
    issue = `${NOM_TOUR[dernier.tour] || dernier.tour} remportée ` +
            `contre ${dernier.adversaire} (${dernier.score})`;
  }

  const m = liste[0];
  return `${m.date_fr} · ${m.tournoi} · ${m.niveau} · ${m.surface} · ` +
         `${v}V-${d}D · ${issue}`;
}

function dessinerFrise(matchs, profil) {
  const svg = $("frise");
  svg.textContent = "";

  const L = 108, R = 14, H_BANDE = 44, HAUT = 26;
  const largeur = 1000;
  const hauteur = HAUT + PALIERS.length * H_BANDE + 30;
  svg.setAttribute("viewBox", `0 0 ${largeur} ${hauteur}`);

  const dates = matchs.map((m) => versDate(m.date));
  const t0 = new Date(Math.min(...dates)).getTime();

  // Un joueur retire n'a plus de matchs a venir : prolonger l'axe
  // jusqu'a aujourd'hui ajouterait des annees de vide. Borg s'est
  // arrete en 1983, sa frise s'arrete en 1983.
  const dernier = new Date(Math.max(...dates)).getTime();
  // On se fie a profil.actif, calcule cote serveur : la page de certains
  // joueurs retires contient la chaine littérale '""', qui est truthy
  // en JavaScript et ferait passer Federer pour un joueur en activite.
  const t1 = profil && profil.actif ? Date.now() : dernier;
  const x = (d) => L + ((d.getTime() - t0) / (t1 - t0)) * (largeur - L - R);

  // reperes d'annee
  const a0 = new Date(t0).getFullYear();
  const a1 = new Date(t1).getFullYear();
  for (let a = a0; a <= a1; a++) {
    const px = x(new Date(a, 0, 1));
    if (px < L) continue;
    el("line", { x1: px, y1: HAUT - 8, x2: px, y2: hauteur - 26,
                 stroke: "var(--trait)", "stroke-width": 1 }, svg);
    el("text", { x: px, y: hauteur - 10, fill: "var(--sourdine)",
                 "font-family": "var(--mono)", "font-size": 11,
                 "text-anchor": "middle" }, svg).textContent = a;
  }

  // bandes + libelles
  PALIERS.forEach((p, i) => {
    const y = HAUT + i * H_BANDE;
    el("line", { x1: L, y1: y + H_BANDE - 1, x2: largeur - R, y2: y + H_BANDE - 1,
                 stroke: "var(--trait)", "stroke-width": 1 }, svg);
    el("text", { x: L - 14, y: y + H_BANDE / 2 + 4, fill: "var(--sourdine)",
                 "font-family": "var(--mono)", "font-size": 10.5,
                 "text-anchor": "end", "letter-spacing": ".04em" }, svg)
      .textContent = p.nom;
  });

  const infobulle = $("infobulle-frise");

  // Tous les matchs d'un tournoi portent la date d'ouverture du tournoi :
  // ils se superposent donc exactement au meme endroit. Survoler la pile
  // revenait a lire le match du dessus -- le premier tour. On regroupe
  // par tournoi et on decrit le parcours entier.
  const groupes = new Map();
  matchs.forEach((m) => {
    const i = palierDe(m.niveau_code);
    if (i < 0) return;
    const cle = `${m.date}|${m.tournoi}`;
    if (!groupes.has(cle)) groupes.set(cle, { palier: i, liste: [] });
    groupes.get(cle).liste.push(m);
  });

  groupes.forEach(({ palier, liste }) => {
    const px = x(versDate(liste[0].date));
    const py = HAUT + palier * H_BANDE + 9;

    liste.forEach((m) => {
      el("rect", {
        x: px - 1.4, y: py, width: 2.8, height: H_BANDE - 20,
        fill: couleurSurface(m.surface),
        opacity: m.resultat === "W" ? 0.92 : 0.24,
        rx: 1.4,
      }, svg);
    });

    const titre = liste.find((m) => m.tour === "F" && m.resultat === "W");
    if (titre) {
      el("path", {
        d: `M ${px} ${py - 9} l 4.5 4.5 l -4.5 4.5 l -4.5 -4.5 z`,
        fill: "var(--texte)",
      }, svg);
    }

    // zone de survol posee par-dessus toute la bande, a cet endroit
    const zone = el("rect", {
      x: px - 3.5, y: py - 12, width: 7, height: H_BANDE - 4,
      fill: "transparent",
    }, svg);
    zone.style.cursor = "crosshair";
    zone.addEventListener("mouseenter", () => {
      infobulle.textContent = resumerTournoi(liste);
    });
  });
  $("legende-surfaces").innerHTML = Object.entries(SURFACES)
    .map(([, s]) => `<span><i style="background:${s.couleur}"></i>${s.nom}</span>`)
    .join("") +
    `<span><i style="background:var(--texte);transform:rotate(45deg)"></i>titre</span>`;
}

/* --------------------------------------------------------- la courbe */

function dessinerCourbe(donnees, profil) {
  const svg = $("courbe");
  svg.textContent = "";

  const pts = donnees.courbe;
  if (!pts.length) return;

  const L = 52, R = 14, HAUT = 18, BAS = 30;
  const largeur = 1000, hauteur = 260;

  const actif = donnees.rang_actuel != null;

  const t0 = versDate(pts[0].date).getTime();
  const t1 = actif ? Date.now() : versDate(pts[pts.length - 1].date).getTime();
  const x = (d) => L + ((d - t0) / (t1 - t0)) * (largeur - L - R);

  // echelle log : l'ecart entre 900 et 400 ne vaut pas celui entre 20 et 11
  const rangMax = Math.max(...pts.map((p) => p.rang));
  const lo = Math.log10(1), hi = Math.log10(Math.max(rangMax, 10) * 1.15);
  const y = (r) => HAUT + ((Math.log10(Math.max(r, 1)) - lo) / (hi - lo)) * (hauteur - HAUT - BAS);

  [1, 10, 100, 1000].forEach((r) => {
    if (r > rangMax * 1.5) return;
    const py = y(r);
    el("line", { x1: L, y1: py, x2: largeur - R, y2: py,
                 stroke: "var(--trait)", "stroke-width": 1 }, svg);
    el("text", { x: L - 12, y: py + 4, fill: "var(--sourdine)",
                 "font-family": "var(--mono)", "font-size": 11,
                 "text-anchor": "end" }, svg).textContent = "#" + r;
  });

  const trace = pts
    .map((p, i) => `${i ? "L" : "M"} ${x(versDate(p.date).getTime()).toFixed(1)} ${y(p.rang).toFixed(1)}`)
    .join(" ");
  el("path", { d: trace, fill: "none", stroke: "var(--dur)", "stroke-width": 2,
               "stroke-linejoin": "round" }, svg);

  const dernier = pts[pts.length - 1];
  const xd = x(versDate(dernier.date).getTime());
  el("circle", { cx: xd, cy: y(dernier.rang), r: 3.5, fill: "var(--dur)" }, svg);

  // Les reperes que le curseur pourra viser. Construits pour tout le
  // monde -- c'est le point que la version precedente ratait, en ne
  // les creant que dans une seule branche.
  const jalons = pts.map((p) => ({
    px: x(versDate(p.date).getTime()),
    py: y(p.rang),
    date_fr: p.date_fr,
    date: p.date,
    rang: p.rang,
  }));

  if (actif) {
    const xa = largeur - R;
    const ya = y(donnees.rang_actuel);
    el("line", { x1: xd, y1: y(dernier.rang), x2: xa, y2: ya,
                 stroke: "var(--dur)", "stroke-width": 2,
                 "stroke-dasharray": "3 4", opacity: .7 }, svg);
    el("circle", { cx: xa, cy: ya, r: 4.5, fill: "var(--texte)" }, svg);
    el("text", { x: xa - 10, y: ya - 12, fill: "var(--texte)",
                 "font-family": "var(--mono)", "font-size": 12,
                 "text-anchor": "end" }, svg).textContent = "#" + donnees.rang_actuel;

    const auj = new Date();
    const j = `${auj.getFullYear()}${String(auj.getMonth() + 1).padStart(2, "0")}` +
              `${String(auj.getDate()).padStart(2, "0")}`;
    jalons.push({ px: xa, py: ya, date_fr: "aujourd'hui", date: j,
                  rang: donnees.rang_actuel });

    $("note-courbe").textContent =
      `Le trait plein s'arrête à son dernier tournoi joué (#${dernier.rang}). ` +
      `Le pointillé rejoint le classement publié depuis : #${donnees.rang_actuel}, ` +
      `son meilleur rang en carrière.`;
  } else {
    $("note-courbe").textContent =
      `Carrière achevée. Dernier classement connu : #${dernier.rang}` +
      (donnees.meilleur_rang ? ` · meilleur rang : #${donnees.meilleur_rang}` : "");
  }

  // --- curseur ---------------------------------------------------------
  // Une couche transparente capte le pointeur : les traits font 2 px,
  // impossible a viser directement.
  const repere = el("g", { opacity: 0 }, svg);
  const vLigne = el("line", { y1: HAUT, y2: hauteur - BAS,
                              stroke: "var(--sourdine)", "stroke-width": 1 }, repere);
  const vRond = el("circle", { r: 5, fill: "var(--texte)",
                               stroke: "var(--fond)", "stroke-width": 2 }, repere);

  const lecture = $("infobulle-courbe");
  const parDefaut = "Promenez le curseur sur la courbe.";
  const dob = profil && profil.dob;

  const couche = el("rect", { x: L, y: HAUT, width: largeur - L - R,
                              height: hauteur - HAUT - BAS,
                              fill: "transparent" }, svg);
  couche.style.cursor = "crosshair";

  couche.addEventListener("pointermove", (ev) => {
    const px = xDansSvg(svg, ev, largeur);
    const proche = jalons.reduce((a, b) =>
      Math.abs(b.px - px) < Math.abs(a.px - px) ? b : a);

    vLigne.setAttribute("x1", proche.px);
    vLigne.setAttribute("x2", proche.px);
    vRond.setAttribute("cx", proche.px);
    vRond.setAttribute("cy", proche.py);
    repere.setAttribute("opacity", 1);

    const age = dob ? ageA(dob, proche.date) : null;
    lecture.textContent =
      `${proche.date_fr} · #${proche.rang}` +
      (age ? ` · ${age.toFixed(1)} ans` : "");
  });

  couche.addEventListener("pointerleave", () => {
    repere.setAttribute("opacity", 0);
    lecture.textContent = parDefaut;
  });
}


/* ---------------------------------------------------------- les titres */

function dessinerTitres(titres) {
  $("titres").innerHTML = titres.map((t) => `
    <li>
      <span class="t-date">${t.date_fr.slice(6)}</span>
      <span><span class="t-nom">${t.tournoi}</span><span class="t-detail">${t.niveau} · ${t.adversaire}</span></span>
      <span class="t-score">${t.score}</span>
    </li>`).join("");
}

/* ---------------------------------------------------------- les barres */

function dessinerBarres(cible, entrees, couleurs) {
  const max = Math.max(...entrees.map(([, b]) => b.joues));
  $(cible).innerHTML = entrees.map(([nom, b]) => `
    <div class="barre">
      <span class="barre-nom">${nom}</span>
      <span class="barre-piste">
        <span class="barre-part" style="width:${(b.joues / max) * b.pourcentage}%;
              background:${couleurs(nom)}"></span>
      </span>
      <span class="barre-val">${b.pourcentage}% · ${b.joues}</span>
    </div>`).join("");
}

/* --------------------------------------------------------- le tableau */

function appliquerFiltres() {
  const an = $("f-annee").value;
  const niv = $("f-niveau").value;
  const res = $("f-resultat").value;
  const adv = $("f-adversaire").value.trim().toLowerCase();

  const filtres = MATCHS.filter((m) =>
    (!an || m.date.startsWith(an)) &&
    (!niv || m.niveau === niv) &&
    (!res || m.resultat === res) &&
    (!adv || m.adversaire.toLowerCase().includes(adv))
  );

  const v = filtres.filter((m) => m.resultat === "W").length;
  $("compte-matchs").textContent = filtres.length
    ? `${filtres.length} matchs · ${v} v. ${filtres.length - v} d.`
    : "aucun match ne correspond";

  $("corps-matchs").innerHTML = filtres.map((m) => `
    <tr>
      <td class="m-date">${m.date_fr}</td>
      <td class="large">${m.tournoi}</td>
      <td style="color:var(--sourdine)">${m.niveau}</td>
      <td style="color:var(--sourdine)">${m.tour}</td>
      <td><span class="pastille pastille--${m.resultat.toLowerCase()}">${m.resultat === "W" ? "V" : "D"}</span></td>
      <td class="large">${m.adversaire}${m.rang_adversaire ? ` <span style="color:var(--sourdine)">#${m.rang_adversaire}</span>` : ""}</td>
      <td class="m-score">${m.score}</td>
    </tr>`).join("");
}

function remplirFiltres() {
  const annees = [...new Set(MATCHS.map((m) => m.date.slice(0, 4)))].sort().reverse();
  $("f-annee").insertAdjacentHTML("beforeend",
    annees.map((a) => `<option>${a}</option>`).join(""));

  const niveaux = [...new Set(MATCHS.map((m) => m.niveau))];
  $("f-niveau").insertAdjacentHTML("beforeend",
    niveaux.map((n) => `<option>${n}</option>`).join(""));

  ["f-annee", "f-niveau", "f-resultat"].forEach((id) =>
    $(id).addEventListener("change", appliquerFiltres));
  $("f-adversaire").addEventListener("input", appliquerFiltres);
}
/* ------------------------------------------------------------ demarrage */

async function demarrer() {
  try {
    const d = await chargerTout(SLUG);

    MATCHS = d.matchs.matchs;

    dessinerEntete(d.profil);
    dessinerFrise(MATCHS, d.profil);
    dessinerCourbe(d.classement, d.profil);
    dessinerTitres(d.stats.titres);

    dessinerBarres("par-surface", Object.entries(d.stats.par_surface),
      (nom) => couleurSurface(nom));
    dessinerBarres("par-niveau",
      Object.entries(d.stats.par_niveau).sort((a, b) => b[1].joues - a[1].joues),
      () => "var(--dur)");

    remplirFiltres();
    appliquerFiltres();

    $("chargement").hidden = true;
    $("page").hidden = false;
  } catch (e) {
    const reseau = e instanceof TypeError || e.message.includes("a repondu");
    document.getElementById("chargement").textContent = reseau
      ? `API injoignable sur ${API} — le serveur est-il lancé ? (${e.message})`
      : `Erreur d'affichage : ${e.message}`;
    console.error(e);
  }
}

/* ------------------------------------------------- changement de joueur */

let ANNUAIRE = [];
let CACHES = new Set();

async function chargerListeJoueurs() {
  try {
    if (STATIQUE) {
      // Seuls les joueurs figes sont accessibles : sans serveur, on ne
      // peut rien telecharger. Autant ne proposer qu'eux.
      ANNUAIRE = INDEX_STATIQUE.joueurs;
      $("joueurs-connus").innerHTML = ANNUAIRE
        .map((j) => `<option value="${j.nom}">#${j.rang} · ${j.pays}</option>`)
        .join("");
      $("f-joueur").placeholder = `Voir un autre joueur… (${ANNUAIRE.length} publiés)`;
      return;
    }

    const [cachees, annu] = await Promise.all([
      fetch(`${API}/api/joueurs`).then((r) => r.json()),
      fetch(`${API}/api/annuaire`).then((r) => r.json()),
    ]);

    ANNUAIRE = annu.joueurs || [];

    const dejaLa = new Set(cachees.en_cache);
    CACHES = dejaLa;
    const enTete = ANNUAIRE.filter((j) => dejaLa.has(j.slug));
    const reste = ANNUAIRE.filter((j) => !dejaLa.has(j.slug));

    $("joueurs-connus").innerHTML = [...enTete, ...reste]
      .map((j) => `<option value="${j.nom}">#${j.rang} · ${j.pays}` +
                  `${dejaLa.has(j.slug) ? " · déjà chargé" : ""}</option>`)
      .join("");

    $("f-joueur").placeholder = ANNUAIRE.length
      ? `Voir un autre joueur… (${ANNUAIRE.length} proposés)`
      : "Voir un autre joueur…";
  } catch {
    /* l'autocompletion est un confort : son echec ne bloque rien */
  }
}

async function afficherJoueur(slug, nom) {
  // On ne touche pas aux sections ici : c'est router() qui decide seul
  // ce qui est visible. La version precedente masquait la fiche et le
  // chargement mais pas l'accueil, qui restait par-dessus.
  $("joueur-msg").textContent = "";
  $("f-joueur").value = "";
  $("acc-champ").value = "";
  $("chargement").textContent = `Chargement de ${nom}…`;
  history.pushState({}, "", `?joueur=${slug}`);
  await router();
  chargerListeJoueurs();
}

async function changerJoueur(saisie, cibleMsg = "joueur-msg") {
  const msg = $(cibleMsg);
  msg.className = "joueur-msg";

  if (STATIQUE) {
    const j = ANNUAIRE.find(
      (x) => x.nom.toLowerCase() === saisie.toLowerCase() ||
             x.slug.toLowerCase() === saisie.toLowerCase());
    if (!j) {
      msg.className = "joueur-msg erreur";
      msg.textContent = `« ${saisie} » ne fait pas partie des joueurs publiés`;
      return;
    }
    return afficherJoueur(j.slug, j.nom);
  }

  msg.textContent = "recherche…";
  try {
    const r = await fetch(`${API}/api/recherche?nom=${encodeURIComponent(saisie)}`);
    const j = await r.json();
    if (!j.trouve) {
      msg.className = "joueur-msg erreur";
      msg.textContent = `« ${saisie} » introuvable (identifiant essayé : ${j.slug})`;
      return;
    }
    await afficherJoueur(j.slug, j.nom);
  } catch (e) {
    msg.className = "joueur-msg erreur";
    msg.textContent = "recherche impossible : " + e.message;
  }
}

$("f-joueur").addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter") return;
  const v = ev.currentTarget.value.trim();
  if (v) changerJoueur(v);
});

$("f-joueur").addEventListener("change", (ev) => {
  const v = ev.currentTarget.value.trim();
  if (v && ANNUAIRE.some((j) => j.nom === v)) changerJoueur(v);
});

window.addEventListener("popstate", () => {
  SLUG = new URLSearchParams(location.search).get("joueur") || "ArthurFils";
  demarrer();
});

/* ------------------------------------------------------ mise a jour */

$("rafraichir").addEventListener("click", async (ev) => {
  const b = ev.currentTarget;
  b.disabled = true;
  b.textContent = "mise à jour…";
  try {
    const r = await json("/api/rafraichir", SLUG, { method: "POST" });
    $("fraicheur").textContent = r.message;
    await demarrer();
  } catch (e) {
    $("fraicheur").textContent = "la mise à jour a échoué : " + e.message;
  }
  b.disabled = false;
  b.textContent = "Mettre à jour";
});


/* ---------------------------------------------------------- tournois */

// Les tableaux sont reconstitues en croisant les carrieres de la base :
// aucune source supplementaire. Un match entre deux joueurs absents de
// la base n'y figure donc pas.
let TOURNOIS = null;

const NOM_TOUR_FR = {
  F: "Finale", BR: "3e place", SF: "Demi-finales", QF: "Quarts de finale",
  R16: "8es de finale", R32: "16es de finale", R64: "32es de finale",
  R128: "64es de finale", RR: "Phase de poules",
  Q1: "Qualifications", Q2: "Qualifications", Q3: "Qualifications",
};
const ORDRE_TOURS = ["F", "BR", "SF", "QF", "R16", "R32", "R64", "R128", "RR",
                     "Q3", "Q2", "Q1"];

async function chargerTournois() {
  if (TOURNOIS) return TOURNOIS;
  const url = STATIQUE
    ? `donnees/tournois.json${INDEX_STATIQUE && INDEX_STATIQUE.genere_le
        ? `?v=${encodeURIComponent(INDEX_STATIQUE.genere_le)}` : ""}`
    : `${API}/api/tournois`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`tournois indisponibles (${r.status})`);
  TOURNOIS = (await r.json()).tournois || [];
  return TOURNOIS;
}

const COURONNE =
  '<svg class="ct-couronne" viewBox="0 0 24 18" aria-hidden="true">' +
  '<path d="M2 16h20l1.5-12-6 4L12 1 6.5 8l-6-4z" fill="currentColor"/></svg>';

function carteTournoi(t) {
  const gagnant = t.vainqueur
    ? `<span class="ct-gagnant">${COURONNE}${t.vainqueur}</span>`
    : "";

  return `
    <a class="carte-tournoi" href="?tournoi=${t.id}">
      <span class="ct-date">${t.date_fr} · ${t.niveau} · ${t.surface}</span>
      <span class="ct-nom">${t.nom}</span>
      ${gagnant}
    </a>`;
}

function lienJoueur(nom, slug, classe) {
  return slug
    ? `<a href="?joueur=${slug}" class="${classe}">${nom}</a>`
    : `<span class="${classe} hors-base">${nom}</span>`;
}


/**
 * Reconstitue l'arbre du tournoi en remontant depuis la finale.
 *
 * Le finaliste a gagne une demi-finale : on la cherche, son adversaire
 * ouvre la branche suivante, et ainsi de suite. La ou un match manque
 * (deux joueurs absents de la base), la place est conservee avec un
 * adversaire inconnu -- l'arbre reste complet, les trous sont visibles.
 *
 * Renvoie null pour les formats sans tableau (phase de poules).
 */
function construireArbre(matchs) {
  if (matchs.some((m) => m.tour === "RR")) return null;

  const finale = matchs.find((m) => m.tour === "F");
  if (!finale) return null;

  const gagnes = new Map();
  matchs.forEach((m) => gagnes.set(`${m.tour}|${m.vainqueur.toLowerCase()}`, m));

  const echelle = ["F", "SF", "QF", "R16", "R32", "R64", "R128"];
  const presents = echelle.filter((t) => matchs.some((m) => m.tour === t));

  const niveaux = [[finale]];

  for (let i = 1; i < presents.length; i++) {
    const tour = presents[i];
    const precedent = niveaux[niveaux.length - 1];
    const courant = [];

    precedent.forEach((m) => {
      [m.vainqueur, m.perdant].forEach((joueur) => {
        if (!joueur) { courant.push(null); return; }
        const trouve = gagnes.get(`${tour}|${joueur.toLowerCase()}`);
        if (trouve) { courant.push(trouve); return; }

        // Pas de match trouve a ce tour. Deux causes tres differentes :
        //  - le joueur est dans la base, donc on connait TOUTE sa
        //    carriere : s'il n'a pas joue ce tour, il en etait exempte
        //    (tetes de serie des Masters 1000 sur 96 joueurs) ;
        //  - il n'y est pas : le match existe mais nous echappe.
        const slug = (m.vainqueur === joueur ? m.vainqueur_slug : m.perdant_slug);
        courant.push({
          tour,
          vainqueur: joueur,
          vainqueur_slug: slug,
          perdant: null,
          score: null,
          exempte: Boolean(slug),
        });
      });
    });
    niveaux.push(courant);
  }

  return niveaux.reverse();       // du premier tour a la finale
}

function caseTableau(m) {
  if (!m) return `<div class="tb-match tb-vide"></div>`;

  if (m.exempte) {
    return `
      <div class="tb-match tb-exempte">
        <div class="tb-ligne tb-gagne">
          ${lienJoueur(m.vainqueur, m.vainqueur_slug, "tb-nom")}
        </div>
        <div class="tb-ligne"><span class="tb-mention">exempté</span></div>
      </div>`;
  }

  return `
    <div class="tb-match${m.perdant ? "" : " tb-partiel"}">
      <div class="tb-ligne tb-gagne">
        ${lienJoueur(m.vainqueur, m.vainqueur_slug, "tb-nom")}
        <span class="tb-score">${m.score || ""}</span>
      </div>
      <div class="tb-ligne">
        ${m.perdant
          ? lienJoueur(m.perdant, m.perdant_slug, "tb-nom")
          : '<span class="tb-nom tb-inconnu">match non retrouvé</span>'}
      </div>
    </div>`;
}

function rendreTableau(t) {
  const arbre = construireArbre(t.matchs);
  if (!arbre) return null;

  const tours = arbre.map((niveau) => (niveau.find(Boolean) || {}).tour || "");

  const colonnes = arbre.map((niveau, i) => `
      <div class="tb-colonne" data-tour="${i}">
        <h4>${NOM_TOUR_FR[tours[i]] || tours[i]}</h4>
        <div class="tb-cases">${niveau.map(caseTableau).join("")}</div>
      </div>`).join("");

  const onglets = tours.map((tour, i) =>
    `<button type="button" class="tb-onglet" data-vers="${i}">${
      NOM_TOUR_FR[tour] || tour}</button>`).join("");

  // On ne compte que les vrais trous : une exemption n'en est pas un.
  const trous = arbre.flat().filter((m) => m && !m.perdant && !m.exempte).length;

  return `
    <div class="tb-commandes">
      <div class="tb-onglets">${onglets}</div>
      <div class="tb-zoom">
        <button type="button" id="zoom-moins" title="Dézoomer">−</button>
        <span id="zoom-valeur">100 %</span>
        <button type="button" id="zoom-plus" title="Zoomer">+</button>
      </div>
    </div>
    <div class="tb-defilement" id="tb-defilement">
      <div class="tb-cadre" id="tb-cadre"><div class="tb-arbre" id="tb-arbre">${colonnes}</div></div>
    </div>
    ${trous ? `<p class="note">${trous} match${trous > 1 ? "s" : ""} ` +
      `non retrouvé${trous > 1 ? "s" : ""} : opposai${trous > 1 ? "ent" : "t"} ` +
      `deux joueurs absents de la base.</p>` : ""}`;
}

/** Zoom et navigation par tour, une fois le tableau dans la page. */
function activerTableau() {
  const cadre = document.getElementById("tb-cadre");
  const arbre = document.getElementById("tb-arbre");
  const zone = document.getElementById("tb-defilement");
  if (!cadre || !arbre) return;

  // Dimensions naturelles, mesurees une fois avant toute mise a l'echelle.
  const largeur = arbre.offsetWidth;
  const hauteur = arbre.offsetHeight;

  let z = 1;

  function appliquer() {
    arbre.style.transform = `scale(${z})`;
    // Le cadre porte la taille mise a l'echelle : sans lui, la
    // transformation ne changerait pas les barres de defilement.
    cadre.style.width = `${largeur * z}px`;
    cadre.style.height = `${hauteur * z}px`;
    document.getElementById("zoom-valeur").textContent = `${Math.round(z * 100)} %`;
  }

  document.getElementById("zoom-moins").addEventListener("click", () => {
    z = Math.max(0.4, z - 0.15);
    appliquer();
  });
  document.getElementById("zoom-plus").addEventListener("click", () => {
    z = Math.min(1.6, z + 0.15);
    appliquer();
  });

  document.querySelectorAll(".tb-onglet").forEach((b) => {
    b.addEventListener("click", () => {
      const col = arbre.querySelector(`[data-tour="${b.dataset.vers}"]`);
      if (!col) return;

      document.querySelectorAll(".tb-onglet").forEach((x) =>
        x.classList.toggle("actif", x === b));

      // On centre la colonne a la main : scrollIntoView ferait aussi
      // defiler la page entiere, ce qui est desagreable ici.
      const cible = (col.offsetLeft + col.offsetWidth / 2) * z - zone.clientWidth / 2;
      zone.scrollTo({ left: Math.max(0, cible), behavior: "smooth" });
    });
  });

  // On ouvre sur la finale, la partie la plus lisible du tableau.
  const dernier = document.querySelectorAll(".tb-onglet");
  if (dernier.length) dernier[dernier.length - 1].click();
}

async function afficherTournois() {
  $("accueil").hidden = true;
  $("page").hidden = true;
  $("comparaison").hidden = true;
  $("chargement").hidden = false;
  $("chargement").textContent = "Chargement des tournois…";

  const liste = await chargerTournois();

  $("trn-titre").textContent = "Tournois";
  $("trn-intro").textContent =
    `Les ${liste.length} derniers tournois du circuit principal, du 250 au ` +
    `Grand Chelem. Les tableaux sont reconstitués à partir des carrières ` +
    `présentes dans la base : cliquez sur un joueur qui y figure.`;
  $("trn-grille").innerHTML = liste.map(carteTournoi).join("");
  $("trn-tableau").innerHTML = "";
  $("trn-pied").textContent = `${liste.length} tournois`;

  $("chargement").hidden = true;
  $("tournois").hidden = false;
  document.title = "Tournois — La montée";
}

async function afficherTournoi(id) {
  $("accueil").hidden = true;
  $("page").hidden = true;
  $("comparaison").hidden = true;
  $("chargement").hidden = false;
  $("chargement").textContent = "Chargement du tournoi…";

  const liste = await chargerTournois();
  const t = liste.find((x) => x.id === id);

  if (!t) {
    $("chargement").textContent =
      "Ce tournoi ne fait pas partie des 60 derniers enregistrés.";
    return;
  }

  const groupes = ORDRE_TOURS
    .map((tour) => [NOM_TOUR_FR[tour] || tour,
                    t.matchs.filter((m) => m.tour === tour)])
    .filter(([, ms]) => ms.length);

  const autres = t.matchs.filter((m) => !ORDRE_TOURS.includes(m.tour));
  if (autres.length) groupes.push(["Autres", autres]);

  $("trn-titre").textContent = t.nom;
  $("trn-intro").textContent =
    `${t.date_fr} · ${t.niveau} · ${t.surface}` +
    (t.vainqueur ? ` · vainqueur : ${t.vainqueur} (${t.score_finale})` : "");

  $("trn-grille").innerHTML = "";

  const arbre = rendreTableau(t);
  const vueListe = groupes.map(([libelle, ms]) => `
    <div class="trn-tour">
      <h3>${libelle}</h3>
      ${ms.map((m) => `
        <div class="trn-match">
          ${lienJoueur(m.vainqueur, m.vainqueur_slug, "trn-v")}
          <span class="trn-bat">bat</span>
          ${lienJoueur(m.perdant, m.perdant_slug, "trn-p")}
          <span class="trn-score">${m.score}</span>
        </div>`).join("")}
    </div>`).join("");

  // L'arbre parle de lui-meme ; la liste reste accessible d'un clic,
  // et sert de repli pour les formats sans tableau (phase de poules).
  $("trn-tableau").innerHTML = arbre
    ? `<div class="trn-bascule">
         <button type="button" id="vue-arbre" class="actif">Tableau</button>
         <button type="button" id="vue-liste">Liste</button>
       </div>
       <div id="zone-arbre">${arbre}</div>
       <div id="zone-liste" hidden>${vueListe}</div>`
    : vueListe;

  if (arbre) {
    const basculer = (versArbre) => {
      $("zone-arbre").hidden = !versArbre;
      $("zone-liste").hidden = versArbre;
      $("vue-arbre").classList.toggle("actif", versArbre);
      $("vue-liste").classList.toggle("actif", !versArbre);
    };
    $("vue-arbre").addEventListener("click", () => basculer(true));
    $("vue-liste").addEventListener("click", () => basculer(false));
    activerTableau();
  }

  $("trn-pied").innerHTML =
    `${t.nb_matchs} matchs retrouvés · <a href="?tournois">tous les tournois</a>`;

  $("chargement").hidden = true;
  $("tournois").hidden = false;
  document.title = `${t.nom} — La montée`;
}

/* ------------------------------------------------------------ accueil */

function remplirGrille() {
  const liste = STATIQUE
    ? INDEX_STATIQUE.joueurs
    : ANNUAIRE.filter((j) => CACHES.has(j.slug));

  const tri = [...liste].sort((a, b) => {
    const ra = parseInt(a.rang) || 9999;
    const rb = parseInt(b.rang) || 9999;
    return ra - rb;
  });

  $("grille-joueurs").innerHTML = tri.map((j) => `
    <a class="carte-joueur" href="?joueur=${j.slug}">
      <span class="cj-rang">${j.rang ? "#" + j.rang : "—"}${j.pays ? " · " + j.pays : ""}</span>
      <span class="cj-nom">${j.nom || j.slug}</span>
      <span class="cj-matchs">${j.nb_matchs ? j.nb_matchs + " matchs" : ""}</span>
    </a>`).join("");

  chargerTournois()
    .then((liste) => {
      $("acc-grille-tournois").innerHTML =
        liste.slice(0, 6).map(carteTournoi).join("");
    })
    .catch(() => {
      // les tournois sont un complement : leur absence ne bloque rien
      $("acc-grille-tournois").innerHTML = "";
    });

  $("acc-fraicheur").textContent = STATIQUE
    ? `${tri.length} joueurs · données figées le ${INDEX_STATIQUE.genere_le}`
    : `${tri.length} joueurs en cache · mode développement`;
}

function afficherAccueil() {
  document.title = "La montée — tracker de carrière ATP";
  $("chargement").hidden = true;
  $("page").hidden = true;
  $("accueil").hidden = false;
  $("comparaison").hidden = true;
  $("tournois").hidden = true;
  remplirGrille();
}

$("acc-champ").addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter") return;
  const v = ev.currentTarget.value.trim();
  if (v) changerJoueur(v, "acc-msg");
});

$("acc-champ").addEventListener("change", (ev) => {
  const v = ev.currentTarget.value.trim();
  if (v && ANNUAIRE.some((j) => j.nom === v)) changerJoueur(v, "acc-msg");
});


/* ------------------------------------------------------- comparaison */

// Couleurs des joueurs compares. Distinctes des couleurs de surface,
// qui n'ont pas cours sur cette page.
const TEINTES = ["var(--texte)", "var(--dur)", "var(--terre)", "var(--gazon)"];

let COMPARES = [];

/** Age en annees (decimal) a une date AAAAMMJJ. */
function ageA(dob, date) {
  if (!dob || dob.length !== 8) return null;
  const ms = versDate(date) - versDate(dob);
  return ms / (365.2425 * 24 * 3600 * 1000);
}

/** Points {age, rang} d'un joueur, plus son rang actuel s'il est en activite. */
function courbeParAge(d) {
  const dob = d.profil.dob;
  const pts = d.classement.courbe
    .map((c) => ({ age: ageA(dob, c.date), rang: c.rang }))
    .filter((p) => p.age !== null && p.age > 5 && p.rang > 0);

  const actuel = parseInt(d.classement.rang_actuel);
  if (actuel && pts.length) {
    const auj = new Date();
    const j = `${auj.getFullYear()}${String(auj.getMonth() + 1).padStart(2, "0")}` +
              `${String(auj.getDate()).padStart(2, "0")}`;
    pts.push({ age: ageA(dob, j), rang: actuel });
  }
  return pts.sort((a, b) => a.age - b.age);
}

function dessinerComparaison(liste) {
  const svg = $("cmp-courbe");
  svg.textContent = "";

  const series = liste.map((d, i) => ({
    nom: d.profil.fullname,
    couleur: TEINTES[i % TEINTES.length],
    pts: courbeParAge(d),
  })).filter((s) => s.pts.length);

  if (!series.length) return;

  const L = 58, R = 96, HAUT = 20, BAS = 34;
  const largeur = 1000, hauteur = 340;

  const ages = series.flatMap((s) => s.pts.map((p) => p.age));
  const a0 = Math.floor(Math.min(...ages));
  const a1 = Math.ceil(Math.max(...ages));
  const x = (a) => L + ((a - a0) / (a1 - a0)) * (largeur - L - R);

  const rangMax = Math.max(...series.flatMap((s) => s.pts.map((p) => p.rang)));
  const lo = 0, hi = Math.log10(Math.max(rangMax, 10) * 1.15);
  const y = (r) => HAUT + ((Math.log10(Math.max(r, 1)) - lo) / (hi - lo)) * (hauteur - HAUT - BAS);

  [1, 10, 100, 1000].forEach((r) => {
    if (r > rangMax * 1.5) return;
    const py = y(r);
    el("line", { x1: L, y1: py, x2: largeur - R, y2: py,
                 stroke: "var(--trait)", "stroke-width": 1 }, svg);
    el("text", { x: L - 12, y: py + 4, fill: "var(--sourdine)",
                 "font-family": "var(--mono)", "font-size": 11,
                 "text-anchor": "end" }, svg).textContent = "#" + r;
  });

  for (let a = a0; a <= a1; a++) {
    if ((a - a0) % 2 && a1 - a0 > 12) continue;
    const px = x(a);
    el("line", { x1: px, y1: HAUT, x2: px, y2: hauteur - BAS,
                 stroke: "var(--trait)", "stroke-width": 1, opacity: .5 }, svg);
    el("text", { x: px, y: hauteur - 14, fill: "var(--sourdine)",
                 "font-family": "var(--mono)", "font-size": 11,
                 "text-anchor": "middle" }, svg).textContent = a + " ans";
  }

  series.forEach((s) => {
    const d = s.pts
      .map((p, i) => `${i ? "L" : "M"} ${x(p.age).toFixed(1)} ${y(p.rang).toFixed(1)}`)
      .join(" ");
    el("path", { d, fill: "none", stroke: s.couleur, "stroke-width": 2,
                 "stroke-linejoin": "round", opacity: .9 }, svg);

    const dernier = s.pts[s.pts.length - 1];
    el("circle", { cx: x(dernier.age), cy: y(dernier.rang), r: 4, fill: s.couleur }, svg);
    el("text", { x: x(dernier.age) + 10, y: y(dernier.rang) + 4, fill: s.couleur,
                 "font-family": "var(--mono)", "font-size": 11 }, svg)
      .textContent = s.nom.split(" ").slice(-1)[0];
  });

  // --- curseur interactif ---------------------------------------------
  // A un age donne, on affiche le dernier classement connu de chaque
  // joueur. "Dernier connu" et non "exact" : les tournois ne tombent
  // pas aux memes dates d'une carriere a l'autre.
  const repere = el("g", { opacity: 0 }, svg);
  const vLigne = el("line", { y1: HAUT, y2: hauteur - BAS,
                              stroke: "var(--sourdine)", "stroke-width": 1 }, repere);
  const ronds = series.map((s2) =>
    el("circle", { r: 4.5, fill: s2.couleur, stroke: "var(--fond)",
                   "stroke-width": 2 }, repere));

  const lecture = $("cmp-infobulle");
  const parDefaut = "Promenez le curseur sur le graphique.";

  const couche = el("rect", { x: L, y: HAUT, width: largeur - L - R,
                              height: hauteur - HAUT - BAS,
                              fill: "transparent" }, svg);
  couche.style.cursor = "crosshair";

  couche.addEventListener("pointermove", (ev) => {
    const px = Math.min(Math.max(xDansSvg(svg, ev, largeur), L), largeur - R);
    const age = a0 + ((px - L) / (largeur - L - R)) * (a1 - a0);

    vLigne.setAttribute("x1", px);
    vLigne.setAttribute("x2", px);

    const morceaux = series.map((s2, i) => {
      const avant = s2.pts.filter((p) => p.age <= age);
      if (!avant.length) {
        ronds[i].setAttribute("opacity", 0);
        return `${s2.nom} — pas encore classé`;
      }
      const p = avant[avant.length - 1];
      ronds[i].setAttribute("opacity", 1);
      ronds[i].setAttribute("cx", px);
      ronds[i].setAttribute("cy", y(p.rang));
      return `${s2.nom} #${p.rang}`;
    });

    repere.setAttribute("opacity", 1);
    lecture.textContent = `${age.toFixed(1)} ans — ` + morceaux.join("  ·  ");
  });

  couche.addEventListener("pointerleave", () => {
    repere.setAttribute("opacity", 0);
    lecture.textContent = parDefaut;
  });

  // A l'age du plus jeune aujourd'hui, ou en etaient les autres ?
  const jeune = series.reduce((a, b) =>
    b.pts[b.pts.length - 1].age < a.pts[a.pts.length - 1].age ? b : a);
  const age = jeune.pts[jeune.pts.length - 1].age;

  const px = x(age);
  el("line", { x1: px, y1: HAUT, x2: px, y2: hauteur - BAS,
               stroke: "var(--sourdine)", "stroke-width": 1,
               "stroke-dasharray": "3 4", opacity: .6 }, svg);

  const a_cet_age = series.map((s) => {
    const avant = s.pts.filter((p) => p.age <= age + 0.02);
    return avant.length
      ? `${s.nom} #${avant[avant.length - 1].rang}`
      : `${s.nom} pas encore classé`;
  });

  $("cmp-note").textContent =
    `À ${age.toFixed(1)} ans — ` + a_cet_age.join("  ·  ");
}

function tableauComparaison(liste) {
  const chiffre = (v) => (v === null || v === undefined || v === "" ? "—" : v);

  const lignes = [
    ["", liste.map((d, i) =>
      `<span style="color:${TEINTES[i % TEINTES.length]}">${d.profil.fullname}</span>`)],
    ["Âge", liste.map((d) => `${d.profil.age} ans`)],
    ["Classement actuel", liste.map((d) => chiffre(d.classement.rang_actuel))],
    ["Meilleur classement", liste.map((d) => chiffre(d.classement.meilleur_rang))],
    ["Atteint à", liste.map((d) => {
      const a = ageA(d.profil.dob, d.profil.peakfirst || "");
      return a ? `${a.toFixed(1)} ans` : "—";
    })],
    ["Matchs joués", liste.map((d) => d.stats.global.joues)],
    ["Victoires", liste.map((d) =>
      `${d.stats.global.gagnes} (${d.stats.global.pourcentage} %)`)],
    ["Titres", liste.map((d) => d.stats.nb_titres)],
  ];

  ["Hard", "Clay", "Grass"].forEach((surf) => {
    const nom = { Hard: "Dur", Clay: "Terre battue", Grass: "Gazon" }[surf];
    lignes.push([nom, liste.map((d) => {
      const b = d.stats.par_surface[surf];
      return b ? `${b.pourcentage} % (${b.joues})` : "—";
    })]);
  });

  $("cmp-table").innerHTML = lignes.map(([titre, valeurs]) => `
    <tr>
      <th>${titre}</th>
      ${valeurs.map((v) => `<td>${v}</td>`).join("")}
    </tr>`).join("");
}

function vignettes(liste) {
  $("cmp-vignettes").innerHTML = liste.map((d, i) => `
    <div class="cmp-vignette" style="border-color:${TEINTES[i % TEINTES.length]}">
      <a href="?joueur=${d.profil.slug}" class="cmp-nom">${d.profil.fullname}</a>
      <span class="cmp-detail">${d.profil.country} · ${d.profil.age} ans ·
        ${d.stats.nb_titres} titre${d.stats.nb_titres > 1 ? "s" : ""}</span>
    </div>`).join("");
}

async function afficherComparaison(slugs) {
  $("accueil").hidden = true;
  $("page").hidden = true;
  $("chargement").hidden = false;
  $("chargement").textContent = `Chargement de ${slugs.length} carrières…`;

  const liste = [];
  for (const slug of slugs) {
    try {
      liste.push(await chargerTout(slug));
    } catch (e) {
      console.warn(`${slug} ignoré :`, e.message);
    }
  }

  if (liste.length < 2) {
    $("chargement").textContent =
      "Il faut au moins deux joueurs disponibles pour comparer.";
    return;
  }

  COMPARES = liste.map((d) => d.profil.slug);
  document.title = liste.map((d) => d.profil.fullname).join(" vs ");

  vignettes(liste);
  dessinerComparaison(liste);
  tableauComparaison(liste);

  $("cmp-fraicheur").textContent = STATIQUE && INDEX_STATIQUE
    ? `données figées le ${INDEX_STATIQUE.genere_le}`
    : "";

  $("chargement").hidden = true;
  $("comparaison").hidden = false;
}

/** Convertit une saisie (nom ou identifiant) en identifiant. */
function versSlug(saisie) {
  const j = ANNUAIRE.find(
    (x) => x.nom.toLowerCase() === saisie.toLowerCase() ||
           x.slug.toLowerCase() === saisie.toLowerCase());
  return j ? j.slug : null;
}

function lancerComparaison(slugs, cibleMsg) {
  const propres = slugs.filter(Boolean);
  if (propres.length < 2) {
    const m = $(cibleMsg);
    m.className = "joueur-msg erreur";
    m.textContent = "Il faut deux joueurs connus — choisis-les dans la liste.";
    return;
  }
  history.pushState({}, "", `?comparer=${propres.join(",")}`);
  router();
}

$("acc-cmp-go").addEventListener("click", () => {
  lancerComparaison(
    [versSlug($("acc-cmp-a").value.trim()), versSlug($("acc-cmp-b").value.trim())],
    "acc-cmp-msg");
});

$("f-comparer").addEventListener("change", (ev) => {
  const autre = versSlug(ev.currentTarget.value.trim());
  if (autre && autre !== SLUG) lancerComparaison([SLUG, autre], "joueur-msg");
});

$("cmp-champ").addEventListener("change", (ev) => {
  const ajout = versSlug(ev.currentTarget.value.trim());
  if (ajout && !COMPARES.includes(ajout)) {
    lancerComparaison([...COMPARES, ajout], "cmp-msg");
  }
});

/* ---------------------------------------------------------- lancement */

// Une seule fonction decide quoi afficher, a partir de l'URL. Le bouton
// Precedent, un lien clique et le chargement initial passent tous par
// elle : il n'y a donc qu'un seul endroit ou l'etat peut diverger.
async function router() {
  const params = new URLSearchParams(location.search);
  const comparer = params.get("comparer");
  const demande = params.get("joueur");

  $("comparaison").hidden = true;
  $("tournois").hidden = true;

  const tournoi = params.get("tournoi");
  if (tournoi) {
    await afficherTournoi(tournoi);
    return;
  }

  if (params.has("tournois")) {
    await afficherTournois();
    return;
  }

  if (comparer) {
    const slugs = comparer.split(",").map((s) => s.trim()).filter(Boolean);
    if (slugs.length >= 2) {
      await afficherComparaison(slugs.slice(0, 4));
      return;
    }
  }

  if (!demande) {
    afficherAccueil();
    return;
  }

  SLUG = demande;
  $("accueil").hidden = true;
  $("page").hidden = true;
  $("chargement").hidden = false;
  await demarrer();
}

window.addEventListener("popstate", router);

// Les cartes et le lien de retour sont de vrais liens : ils marchent
// meme sans JavaScript. On les intercepte seulement pour eviter un
// rechargement complet.
document.addEventListener("click", (ev) => {
  const lien = ev.target.closest('a.carte-joueur, a.retour, a.carte-tournoi, a.lien-plus, a[href^="?"]');
  if (!lien || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
  ev.preventDefault();
  history.pushState({}, "", lien.getAttribute("href"));
  router();
});

(async () => {
  await detecterMode();

  if (STATIQUE) {
    $("rafraichir").hidden = true;   // sans serveur, rien a rafraichir
  }

  await chargerListeJoueurs();
  await router();

  if (STATIQUE && !$("page").hidden) {
    $("fraicheur").textContent = `version figée le ${INDEX_STATIQUE.genere_le}`;
  }
})();