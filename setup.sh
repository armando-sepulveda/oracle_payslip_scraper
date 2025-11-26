#!/bin/bash
# Script de instalación rápida para Oracle Payslip Scraper

echo "🚀 Instalando Oracle Payslip Scraper..."
echo ""

# Verificar si Poetry está instalado
if ! command -v poetry &> /dev/null
then
    echo "❌ Poetry no está instalado"
    echo "Por favor instala Poetry primero:"
    echo "  curl -sSL https://install.python-poetry.org | python3 -"
    echo "o con Homebrew:"
    echo "  brew install poetry"
    exit 1
fi

echo "✓ Poetry encontrado"
echo ""

# Instalar dependencias
echo "📦 Instalando dependencias de Python..."
poetry install

if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias"
    exit 1
fi

echo "✓ Dependencias instaladas"
echo ""

# Instalar navegadores de Playwright
echo "🌐 Instalando navegadores de Playwright..."
poetry run playwright install chromium

if [ $? -ne 0 ]; then
    echo "❌ Error instalando navegadores"
    exit 1
fi

echo "✓ Navegadores instalados"
echo ""

# Verificar archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado"
    echo "Copiando .env.example a .env..."
    cp .env.example .env
    echo "⚠️  Por favor edita el archivo .env con tus credenciales antes de ejecutar el scraper"
else
    echo "✓ Archivo .env encontrado"
fi

echo ""
echo "✅ Instalación completada"
echo ""
echo "Para ejecutar el scraper:"
echo "  poetry run python scraper.py"
echo ""
echo "Para ver el navegador en acción (debugging):"
echo "  HEADLESS=false poetry run python scraper.py"
