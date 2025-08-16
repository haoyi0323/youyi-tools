[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Repo,  # e.g. https://github.com/YourName/youyi-tools.git
    [string]$Branch = "main"
)

# Run in script directory (supports non-ASCII and spaces)
Set-Location -LiteralPath $PSScriptRoot

Write-Host "== Working Directory ==" (Get-Location).Path -ForegroundColor Cyan

# 1) Check git
try {
    git --version | Out-Null
} catch {
    Write-Error "Git not found. Please install Git (winget install -e --id Git.Git) and re-run."
    exit 1
}

# 2) Init repo if needed
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repo..." -ForegroundColor Yellow
    git init | Out-Null
}

# 3) Create .gitignore if missing
$gitignorePath = Join-Path (Get-Location) ".gitignore"
if (-not (Test-Path $gitignorePath)) {
    Write-Host ".gitignore not found. Creating..." -ForegroundColor Yellow
    $gitignoreContent = @'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg-info/
.eggs/
.venv/
venv/
ENV/
env/
pip-wheel-metadata/
.pytest_cache/
.coverage
htmlcov/

# IDE/Editor
.vscode/
.idea/
*.code-workspace

# OS
.DS_Store
Thumbs.db
desktop.ini

# Logs
logs/
*.log

# Streamlit
.streamlit/logs/
.streamlit/secrets.toml

# Data (ignored by default for privacy)
*.xlsx
*.xls
*.csv
*.tsv
data/
datasets/
tmp/
temp/

# Node
node_modules/

# Build
build/
dist/
'@
    $gitignoreContent | Set-Content -Path $gitignorePath -Encoding ASCII
}

# 4) Ensure local git user
$localName = git config user.name 2>$null
$localEmail = git config user.email 2>$null
if (-not $localName) {
    git config user.name "$env:USERNAME" | Out-Null
}
if (-not $localEmail) {
    $noreply = "$($env:USERNAME)@users.noreply.github.com"
    git config user.email $noreply | Out-Null
}

# 5) Add and commit
Write-Host "Staging and committing changes..." -ForegroundColor Yellow
git add -A
$pending = git status --porcelain 2>$null
if ($pending) {
    git commit -m "Initial commit" | Out-Null
} else {
    Write-Host "No changes to commit." -ForegroundColor DarkGray
}

# 6) Set branch name
git branch -M $Branch 2>$null

# 7) Set remote origin
$hasOrigin = git remote 2>$null | Select-String -SimpleMatch "origin"
if ($hasOrigin) {
    git remote set-url origin $Repo
} else {
    git remote add origin $Repo
}

# 8) Push
Write-Host "Pushing to: $Repo ($Branch) ..." -ForegroundColor Yellow
try {
    git push -u origin $Branch
    Write-Host "Push successful!" -ForegroundColor Green
    Write-Host "You can now deploy from this repo on Streamlit Community/Render/Railway." -ForegroundColor Green
} catch {
    Write-Error ("Push failed: {0}" -f $_.Exception.Message)
    Write-Host "Common reasons:" -ForegroundColor Yellow
    Write-Host "1) Remote repo does not exist: create an empty repo on GitHub and rerun." -ForegroundColor Yellow
    Write-Host "2) Authentication failed: use your GitHub username and a Personal Access Token (with repo scope) as password." -ForegroundColor Yellow
    exit 1
}

Write-Host "Done." -ForegroundColor Green