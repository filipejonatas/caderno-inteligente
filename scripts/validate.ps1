$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$frontend = Join-Path $projectRoot 'frontend'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Ambiente Python não encontrado. Crie a .venv conforme o README antes de validar.'
}

Write-Host 'Validando dependências Python...'
& $python -m pip check
if ($LASTEXITCODE -ne 0) {
    throw 'A validação das dependências Python falhou.'
}

Write-Host 'Executando testes Python...'
& $python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw 'A suíte Python falhou.'
}

Write-Host 'Executando verificações do frontend...'
Push-Location $frontend
try {
    & npm.cmd run check
    if ($LASTEXITCODE -ne 0) {
        throw 'As verificações do frontend falharam.'
    }
}
finally {
    Pop-Location
}

Write-Host 'Validação concluída com sucesso.'
