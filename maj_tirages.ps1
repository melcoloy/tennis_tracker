# maj_tirages.ps1 -- met a jour les tableaux seulement, sans retelecharger les joueurs
Set-Location $PSScriptRoot
git pull --ff-only
New-Item -ItemType Directory -Force logs | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$log = "logs\tirages_$(Get-Date -Format 'yyyy-MM-dd_HH-mm').txt"

& .\.venv\Scripts\python.exe -u tirages_auto.py *>&1 | Tee-Object -FilePath $log
& .\.venv\Scripts\python.exe -u prochain.py      *>&1 | Tee-Object -FilePath $log -Append

# on ne pousse que s'il y a vraiment du nouveau
git add site/donnees/prochain.json tirages
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "tirages $(Get-Date -Format 'yyyy-MM-dd HH:mm')" *>&1 | Tee-Object -FilePath $log -Append
    git push --quiet *>&1 | Tee-Object -FilePath $log -Append
}
