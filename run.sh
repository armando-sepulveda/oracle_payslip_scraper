#!/bin/bash
# Script para ejecutar el scraper fácilmente

# Verificar que las dependencias están instaladas
if [ ! -d ".venv" ] && [ ! -f "poetry.lock" ]; then
    echo "⚠️  Dependencias no instaladas. Ejecuta primero:"
    echo "  ./setup.sh"
    exit 1
fi

# Verificar archivo .env
if [ ! -f .env ]; then
    echo "❌ Archivo .env no encontrado"
    echo "Copia .env.example a .env y configura tus credenciales:"
    echo "  cp .env.example .env"
    exit 1
fi

echo "🚀 Ejecutando Oracle Payslip Scraper..."
echo ""

poetry run python scraper.py

echo ""
echo "✅ Proceso completado"
