# Script de detención para SRI-DX
# Ejecuta: .\stop.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "     SRI-DX - Deteniendo Servicios             " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Preguntar si quiere eliminar volúmenes
$removeVolumes = Read-Host "¿Deseas eliminar también los datos persistentes? (s/N)"

Write-Host "🛑 Deteniendo contenedores..." -ForegroundColor Yellow

if ($removeVolumes -eq "s" -or $removeVolumes -eq "S") {
    docker compose down -v
    Write-Host "   ✅ Contenedores y volúmenes eliminados" -ForegroundColor Green
    Write-Host "   ⚠️  Los datos de Elasticsearch se han borrado" -ForegroundColor Yellow
} else {
    docker compose down
    Write-Host "   ✅ Contenedores detenidos" -ForegroundColor Green
    Write-Host "   📊 Los datos se conservan para la próxima ejecución" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ Servicios detenidos correctamente" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar nuevamente:" -ForegroundColor Cyan
Write-Host "   .\start.ps1" -ForegroundColor White
Write-Host "   o" -ForegroundColor Cyan
Write-Host "   docker compose up" -ForegroundColor White
Write-Host ""
