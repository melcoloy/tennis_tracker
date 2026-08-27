"""
Ou se trouve le VRAI classement dans page_fils.html ?

matchmx donne le rang a l'entree de chaque tournoi : il ignore le
classement publie apres le dernier tournoi joue. On cherche donc la
valeur affichee par le site lui-meme.

    python trouve_rang.py
"""

import re

FICHIER = "page_fils.html"

with open(FICHIER, encoding="utf-8") as f:
    html = f.read()

print("=" * 65)
print("1. VARIABLES DONT LE NOM CONTIENT 'rank'")
print("=" * 65)
vus = set()
for m in re.finditer(r"var\s+(\w*[Rr]ank\w*)\s*=\s*([^;\n]{0,120})", html):
    nom, val = m.group(1), m.group(2).strip()
    if nom in vus:
        continue
    vus.add(nom)
    print(f"  {nom:<18} = {val[:100]}")

print("\n" + "=" * 65)
print("2. TEXTE AUTOUR DES MOTS-CLES DE CLASSEMENT")
print("=" * 65)
for mot in ["Current rank", "Peak rank", "Peak:", "currentrank", "peakrank",
            "Highest", "ATP Rank", "careerhigh"]:
    for m in re.finditer(re.escape(mot), html):
        extrait = html[max(0, m.start() - 90):m.start() + 150]
        extrait = re.sub(r"\s+", " ", extrait)
        print(f"\n  '{mot}' :")
        print(f"    ...{extrait}...")
        break

print("\n" + "=" * 65)
print("3. EN-TETE DE LA FICHE (souvent le rang y est affiche)")
print("=" * 65)
m = re.search(r"<body.*?>(.{0,1800})", html, re.S)
if m:
    texte = re.sub(r"<[^>]+>", " ", m.group(1))
    texte = re.sub(r"\s+", " ", texte).strip()
    print("  " + texte[:900])