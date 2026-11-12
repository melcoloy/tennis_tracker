# maj.ps1 -- lance la publication et garde une trace de chaque passage
Set-Location $PSScriptRoot
git pull --ff-only
New-Item -ItemType Directory -Force logs | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$log = "logs\maj_$(Get-Date -Format 'yyyy-MM-dd_HH-mm').txt"

# 1. tableaux des tournois en cours, 2. prochain.json, 3. site complet
& .\.venv\Scripts\python.exe -u tirages_auto.py *>&1 | Tee-Object -FilePath $log
& .\.venv\Scripts\python.exe -u prochain.py      *>&1 | Tee-Object -FilePath $log -Append
& .\.venv\Scripts\python.exe -u publier.py       *>&1 | Tee-Object -FilePath $log -Append
# Code de sortie de publier.py (2 = publication annulee par le garde-fou) :
# la tache planifiee l'affiche dans LastTaskResult.
exit $LASTEXITCODE
