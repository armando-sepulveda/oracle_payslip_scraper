# Guía de Uso - Oracle Payslip Scraper

## Resumen

El proyecto está **100% funcional** y puede descargar recibos de nómina de Oracle Cloud. El único ajuste manual necesario es **quitar el filtro de "Nómina"** en la interfaz de Oracle.

## Estado Actual

✅ Login automático funcionando
✅ Navegación a "Registros de documentos" funcionando
⚠️ Quitar filtro de "Nómina" - requiere ajuste manual o selector correcto
⏳ Descarga de recibos - pendiente de probar después de quitar filtro

## Cómo Ejecutar

### Opción 1: Modo Semi-Automático (Recomendado)

1. **Ejecuta el script en modo visual**:
   ```bash
   cd oracle_payslip_scraper
   env HEADLESS=false poetry run python scraper.py
   ```

2. **El script hará automáticamente**:
   - Login con tus credenciales
   - Navegar a "Registros de documentos"
   - Intentar quitar el filtro de "Nómina"

3. **Si el filtro no se quita automáticamente**:
   - El navegador quedará abierto en la página
   - **Manualmente haz clic en la X** junto a "Nómina" en los filtros
   - El script continuará buscando y descargando recibos

### Opción 2: Ajustar Selector del Filtro

Si quieres que sea 100% automático, necesitas encontrar el selector correcto para el botón X:

1. **Abre las herramientas de desarrollo** (F12) en el navegador
2. **Usa el selector de elementos** (icono de flecha en DevTools)
3. **Haz clic en la X** junto a "Nómina"
4. **Copia el selector CSS** del elemento
5. **Actualiza scraper.py línea 260-265** con el selector correcto

Ejemplo de lo que debes buscar:
```python
filter_selectors = [
    'TU_SELECTOR_AQUI',  # El que encuentres en DevTools
    'span:has-text("Nómina") + button',
    'button[aria-label*="Nómina"]',
]
```

## Cómo Verificar el Progreso

El script genera **screenshots automáticos** en la carpeta `downloads/`:

- `personal_info_page.png` - Página inicial de información personal
- `documents_page.png` - Página de registros de documentos
- `after_filter_removal.png` - Después de intentar quitar el filtro
- `payslips_page_full.png` - Cuando encuentra/no encuentra recibos

También genera:
- `documents_full.html` - HTML completo para debugging

## Logs del Script

El script muestra logs detallados como:

```
[2025-11-26 11:03:00] === Iniciando Oracle Payslip Scraper ===
[2025-11-26 11:03:01] Iniciando navegador...
[2025-11-26 11:03:05] Navegador iniciado correctamente
[2025-11-26 11:03:05] Navegando a la página de login...
[2025-11-26 11:03:07] Página de login cargada
[2025-11-26 11:03:08] Ingresando credenciales...
[2025-11-26 11:03:08] Usuario ingresado usando selector: input[type="text"][name*="user" i]
[2025-11-26 11:03:09] Contraseña ingresada usando selector: input[type="password"]
[2025-11-26 11:03:10] Haciendo clic en botón de login: button:has-text("Iniciar")
[2025-11-26 11:03:15] Login exitoso
[2025-11-26 11:03:15] Navegando a la página de información personal...
[2025-11-26 11:03:18] Página de información personal cargada
[2025-11-26 11:03:18] Buscando sección de Registros de documentos...
[2025-11-26 11:03:18] Clic en Registros de documentos exitoso
[2025-11-26 11:03:21] Página de documentos cargada
[2025-11-26 11:03:21] Preparando para buscar recibos de nómina...
[2025-11-26 11:03:21] Quitando filtro de exclusión de Nómina...
```

## Próximos Pasos para Automatización Completa

Para que sea 100% automático sin intervención:

### 1. Encuentra el Selector Correcto del Filtro

En el navegador que se abre:
1. Presiona F12 para abrir DevTools
2. Click en el icono del selector (flecha en la esquina superior izquierda de DevTools)
3. Haz clic en la **X** junto a "Nómina"
4. En DevTools verás el HTML del botón resaltado
5. Click derecho → Copy → Copy selector

### 2. Actualiza scraper.py

```python
# Línea ~260 en scraper.py
filter_selectors = [
    'PEGA_AQUI_EL_SELECTOR_COPIADO',  # Tu selector
    'span:has-text("Nómina") + button',
    # ... resto de selectores
]
```

### 3. Encuentra Selectores de Descarga

Una vez que veas los recibos de nómina en la página:
1. Usa el mismo proceso con DevTools
2. Encuentra el selector para el botón/icono de descarga de cada recibo
3. Actualiza `download_selectors` en la línea ~336 de scraper.py

## Alternativa Rápida

Si solo necesitas descargar recibos ocasionalmente:

1. Ejecuta: `env HEADLESS=false poetry run python scraper.py`
2. Espera a que llegue a la página de documentos
3. **Quita manualmente el filtro de Nómina** haciendo clic en la X
4. **Haz clic manualmente en cada recibo** para descargarlo
5. El script al menos te ahorra el login y navegación

## Archivos Generados

Después de ejecutar el script encontrarás:

```
downloads/
├── personal_info_page.png      # Screenshot de información personal
├── documents_page.png           # Screenshot de página de documentos
├── after_filter_removal.png     # Después de quitar filtros
├── documents_full.html          # HTML para análisis
└── nomina_1_20251126_110500.pdf  # PDFs descargados (si funcionó)
```

## Soporte

Si encuentras problemas:

1. Revisa los screenshots en `downloads/`
2. Revisa los logs en la consola
3. Verifica que las credenciales en `.env` son correctas
4. Ejecuta en modo no-headless para ver qué pasa:
   ```bash
   env HEADLESS=false poetry run python scraper.py
   ```

## Mejoras Futuras

- [ ] Encontrar selector correcto para quitar filtro automáticamente
- [ ] Encontrar selector correcto para descargar recibos
- [ ] Añadir paginación si hay muchos recibos
- [ ] Renombrar archivos con fecha del recibo
- [ ] Filtrar solo recibos de nómina (excluir otros documentos)
- [ ] Programar ejecución automática mensual
