# =====================================================================
#  fabriquer_exe.ps1 - GestionArticles.exe (un seul fichier, hors-ligne)
#
#  Usage :
#    powershell -ExecutionPolicy Bypass -File fabriquer_exe.ps1
#
#  Produit :
#    dist\GestionArticles.exe   (~40-70 Mo) a envoyer aux collegues
#
#  Le collegue n'installe RIEN : il copie le .exe dans un dossier de son
#  disque dur (ex. Documents) et double-clique. Les donnees (web_app.db,
#  documents_pdf\, uploads\, .session.key) sont creees A COTE du .exe.
#
#  Dependance : Python 3.10-3.14 + pyinstaller (installe automatiquement).
# =====================================================================
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# ---------------------------------------------------------- Python 3.10-3.14
$pyExe = $null
$pyPrefix = @()
if (Test-Path 'C:\Python314\python.exe') {
    $pyExe = 'C:\Python314\python.exe'
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $pyExe = $cmd.Source }
}
if (-not $pyExe) {
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) { $pyExe = $cmd.Source; $pyPrefix = @('-3') }
}
if (-not $pyExe) {
    Write-Host '[ERREUR] Python 3.10-3.14 introuvable (voir run.bat).'
    exit 1
}
Write-Host "[1/3] Python : $pyExe"

# ------------------------------------------------------------ PyInstaller
$pyiVersion = & $pyExe @pyPrefix -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0 -or -not $pyiVersion) {
    Write-Host '[2/3] Installation de pyinstaller...'
    & $pyExe @pyPrefix -m pip install pyinstaller --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERREUR] pip install pyinstaller a echoue (connexion internet ?).'
        exit 1
    }
} else {
    Write-Host "[2/3] PyInstaller : $pyiVersion"
}

# ------------------------------------------------- ressources embarquees
#   app\                 templates Flask + static (CSS/JS/img), memes chemins
#   Model\               formulaires Word (lecture seule)
#   source_listes.xlsx   import initial des articles
# Chemins ABSOLUS obligatoires : --specpath build fait resoudre les chemins
# relatifs depuis build\, pas depuis la racine du projet.
# separateur Windows : ';'  (un seul OS cible : Windows)
$root = $PSScriptRoot
# NB : chaque element doit etre parenthese entierement — en PowerShell le
# separateur ',' se lie plus fort que '+', sans quoi les elements fusionnent.
$datas = @(
    ((Join-Path $root 'app') + ';app'),
    ((Join-Path $root 'Model') + ';Model'),
    ((Join-Path $root 'source_listes.xlsx') + ';.')
)

Write-Host '[3/3] Construction de GestionArticles.exe (1-2 min)...'
New-Item -ItemType Directory -Force -Path 'build', 'dist' | Out-Null

$arguments = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--onefile',
    '--console',
    '--name', 'GestionArticles',
    '--paths', $PSScriptRoot,
    '--specpath', 'build',
    '--workpath', 'build',
    '--distpath', 'dist',
    '--collect-all', 'flask',
    '--collect-all', 'click',
    '--collect-all', 'jinja2',
    '--collect-all', 'werkzeug',
    '--collect-all', 'itsdangerous',
    '--collect-all', 'markupsafe',
    '--collect-all', 'blinker',
    '--collect-all', 'openpyxl',
    '--collect-all', 'et_xmlfile',
    '--collect-all', 'reportlab',
    '--collect-all', 'encodings'
)
foreach ($d in $datas) { $arguments += @('--add-data', $d) }
# Script d'entree en chemin absolu (meme raison que les datas ci-dessus).
$arguments += (Join-Path $root 'serve.py')

# Sortie filtrée : seuls les erreurs/avertissements + fin sont affichés.
# (EAP temporairement 'Continue' : PyInstaller écrit sur stderr, ce qui
#  deviendrait une exception terminante avec 'Stop'.)
$oldEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$out = & $pyExe @pyPrefix @arguments 2>&1 | ForEach-Object { "$_" }
$code = $LASTEXITCODE
$ErrorActionPreference = $oldEAP
$interesting = $out | Where-Object {
    $_ -match 'ERROR|Traceback|no suitable|Failed to|Building EXE|Completing analysis|Building COLLECT|Applications' 
}
$interesting | Select-Object -Last 25 | ForEach-Object { Write-Host $_ }

if ($code -ne 0 -or -not (Test-Path 'dist\GestionArticles.exe')) {
    Write-Host '[ERREUR] La construction a echoue - dernieres lignes :'
    $out | Select-Object -Last 30 | ForEach-Object { Write-Host $_ }
    exit 1
}

$exe = Get-Item 'dist\GestionArticles.exe'
$mo = [math]::Round($exe.Length / 1MB, 1)
Write-Host ''
Write-Host "OK : $($exe.FullName) ($mo Mo)"
Write-Host ''
Write-Host 'A ENVOYER AUX COLLEGUES : ce fichier seul (ou dans un .zip).'
Write-Host 'Le collegue copie le .exe dans un dossier de son disque dur'
Write-Host '(ex. Documents) puis double-clique dessus - rien a installer.'
Write-Host 'Premier lancement : si Windows affiche "Windows a protege votre'
Write-Host 'PC", cliquer Informations complementaires puis Executer quand meme.'
exit 0


