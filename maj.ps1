# maj.ps1 -- lance la publication et garde une trace de chaque passage
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force logs | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$log = "logs\maj_$(Get-Date -Format 'yyyy-MM-dd_HH-mm').txt"
& .\.venv\Scripts\python.exe publier.py *>&1 | Tee-Object -FilePath $log
