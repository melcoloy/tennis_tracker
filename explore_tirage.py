import re
import requests
import cache

URL = "https://www.tennisabstract.com/current/2026ATPParis.html"
r = requests.get(URL, headers=cache.HEADERS, timeout=30)
html = r.text
print(r.status_code, len(html), "caracteres\n")

print("Variables JS :", re.findall(r"var\s+(\w+)\s*=", html)[:40], "\n")

i = html.find("Alcaraz")
print(html[i - 800 : i + 400])