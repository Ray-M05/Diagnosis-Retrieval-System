# Script de inicio rápido para SRI-DX
# Ejecuta: .\start.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "     SRI-DX - Diagnosis Retrieval System       " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Docker está instalado
Write-Host "🔍 Verificando Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "   ✅ Docker encontrado: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker no está instalado" -ForegroundColor Red
    Write-Host "   Descarga Docker Desktop desde: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Verificar si Docker está corriendo
Write-Host "🔍 Verificando que Docker esté corriendo..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "   ✅ Docker está corriendo" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker no está corriendo" -ForegroundColor Red
    Write-Host "   Inicia Docker Desktop y vuelve a ejecutar este script" -ForegroundColor Yellow
    exit 1
}

# Verificar si existe archivo .env
Write-Host "🔍 Verificando configuración..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "   ✅ Archivo .env encontrado" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Archivo .env no encontrado, usando .env.example" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "   ✅ Archivo .env creado" -ForegroundColor Green
}

# Preguntar si quiere hacer build limpio
Write-Host ""
$rebuild = Read-Host "¿Deseas hacer un build limpio? (s/N)"
if ($rebuild -eq "s" -or $rebuild -eq "S") {
    Write-Host "🧹 Limpiando contenedores y volúmenes anteriores..." -ForegroundColor Yellow
    docker compose down -v
    Write-Host "   ✅ Limpieza completada" -ForegroundColor Green
}

# Iniciar servicios
Write-Host ""
Write-Host "🚀 Iniciando servicios..." -ForegroundColor Yellow
Write-Host ""
Write-Host "   Esto puede tomar algunos minutos la primera vez..." -ForegroundColor Cyan
Write-Host "   Se descargarán las siguientes imágenes:" -ForegroundColor Cyan
Write-Host "   - Elasticsearch 8.11.0 (~500MB)" -ForegroundColor Cyan
Write-Host "   - Python 3.11 y dependencias" -ForegroundColor Cyan
Write-Host ""

docker compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "     ✅ ¡Sistema iniciado correctamente!       " -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Accede a la aplicación en:" -ForegroundColor Cyan
    Write-Host "   http://localhost:8501" -ForegroundColor White
    Write-Host ""
    Write-Host "🔍 Elasticsearch API:" -ForegroundColor Cyan
    Write-Host "   http://localhost:9200" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 Ver logs:" -ForegroundColor Cyan
    Write-Host "   docker compose logs -f" -ForegroundColor White
    Write-Host ""
    Write-Host "🛑 Detener servicios:" -ForegroundColor Cyan
    Write-Host "   docker compose down" -ForegroundColor White
    Write-Host ""
    
    # Esperar a que los servicios estén listos
    Write-Host "⏳ Esperando a que los servicios estén listos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Verificar salud de Elasticsearch
    $maxRetries = 10
    $retry = 0
    $esReady = $false
    
    while ($retry -lt $maxRetries -and -not $esReady) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:9200/_cluster/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $esReady = $true
                Write-Host "   ✅ Elasticsearch está listo" -ForegroundColor Green
            }
        } catch {
            $retry++
            Write-Host "   ⏳ Esperando Elasticsearch ($retry/$maxRetries)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        }
    }
    
    if ($esReady) {
        Write-Host ""
        Write-Host "🎉 Todo está listo!" -ForegroundColor Green
        Write-Host "   Abre http://localhost:8501 en tu navegador" -ForegroundColor Cyan
        
        # Preguntar si quiere abrir el navegador
        $openBrowser = Read-Host "¿Abrir el navegador automáticamente? (S/n)"
        if ($openBrowser -ne "n" -and $openBrowser -ne "N") {
            Start-Process "http://localhost:8501"
        }
    } else {
        Write-Host ""
        Write-Host "⚠️  Elasticsearch está tardando más de lo esperado" -ForegroundColor Yellow
        Write-Host "   Verifica los logs con: docker compose logs elasticsearch" -ForegroundColor Cyan
    }
    
} else {
    Write-Host ""
    Write-Host "❌ Error al iniciar los servicios" -ForegroundColor Red
    Write-Host "   Revisa los logs con: docker compose logs" -ForegroundColor Yellow
    exit 1
}
