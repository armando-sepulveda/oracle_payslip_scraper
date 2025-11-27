# Oracle Payslip Scraper

Herramienta automatizada para descargar recibos de nómina del portal de Oracle Cloud.

## Características

- Automatización completa del proceso de login y descarga
- **Continuación automática desde el último recibo descargado**
- Renombrado inteligente de archivos con nombres incompletos
- Manejo seguro de credenciales con variables de entorno
- Múltiples estrategias para detectar elementos en la página
- Screenshots automáticos para debugging
- Logging detallado del proceso
- Modo headless para ejecución en segundo plano

## Requisitos

- Python 3.9 o superior
- Poetry (gestor de dependencias)
- Conexión a internet

## Instalación

### 1. Instalar Poetry (si no lo tienes)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

O en macOS con Homebrew:

```bash
brew install poetry
```

### 2. Clonar/Navegar al proyecto

```bash
cd oracle_payslip_scraper
```

### 3. Instalar dependencias

```bash
poetry install
```

### 4. Instalar navegadores de Playwright

```bash
poetry run playwright install chromium
```

## Configuración

### 1. Crear archivo de credenciales

Copia el archivo de ejemplo y edítalo con tus credenciales:

```bash
cp .env.example .env
```

### 2. Editar el archivo .env

Abre el archivo `.env` y configura tus credenciales:

```env
ORACLE_USERNAME=armando.sepulveda@banregio.com
ORACLE_PASSWORD=TuContraseñaAquí

# Configuración opcional
HEADLESS=true
DOWNLOAD_PATH=./downloads
FORCE_RESTART=false  # true para reiniciar desde el principio, false para continuar
```

**IMPORTANTE:**
- Nunca compartas el archivo `.env`
- Nunca lo subas a git (ya está en .gitignore)
- Mantén tus credenciales seguras

## Uso

### Modo básico (headless)

```bash
poetry run python scraper.py
```

El script automáticamente **continuará desde el último recibo descargado** si fue interrumpido previamente.

### Reiniciar descarga desde el principio

Si quieres volver a descargar todos los recibos desde cero:

```bash
FORCE_RESTART=true poetry run python scraper.py
```

### Ver el navegador en acción (debugging)

Para ver qué está haciendo el script, ejecuta en modo no-headless:

```bash
HEADLESS=false poetry run python scraper.py
```

### Personalizar la carpeta de descargas

```bash
DOWNLOAD_PATH=./mis_recibos poetry run python scraper.py
```

## Ajuste de Selectores

El script incluye múltiples estrategias para detectar elementos en la página, pero **es probable que necesites ajustar los selectores** según la estructura real del portal de Oracle.

### Cómo ajustar selectores:

1. **Ejecuta el script en modo no-headless:**
   ```bash
   HEADLESS=false poetry run python scraper.py
   ```

2. **Observa dónde falla** el proceso

3. **Inspecciona la página:**
   - Abre las herramientas de desarrollo del navegador (F12)
   - Usa el selector de elementos (icono de flecha)
   - Identifica el selector CSS correcto

4. **Actualiza los selectores en `scraper.py`:**

   Busca estas secciones en el código:

   ```python
   # Selectores de login (líneas ~80-100)
   username_selectors = [
       'input[type="text"][name*="username" i]',
       # Añade tus selectores aquí
   ]

   # Selectores de recibos (líneas ~200-220)
   payslip_selectors = [
       'a:has-text("PDF")',
       # Añade tus selectores aquí
   ]
   ```

### Screenshots para debugging

El script guarda automáticamente screenshots cuando hay errores:

- `error_login_page.png` - Página de login
- `error_after_login.png` - Después del intento de login
- `payslip_page.png` - Página de recibos
- `payslips_page.html` - HTML completo para análisis

Revisa estos archivos en la carpeta `downloads/` para identificar problemas.

## Estructura del Proyecto

```
oracle_payslip_scraper/
├── scraper.py              # Script principal
├── rename_existing_files.py # Script para renombrar archivos existentes
├── pyproject.toml          # Dependencias del proyecto
├── .env                    # Credenciales (NO SUBIR A GIT)
├── .env.example            # Plantilla de credenciales
├── .gitignore              # Archivos a ignorar en git
├── README.md               # Este archivo
└── downloads/              # Archivos descargados
    ├── .scraper_progress.json  # Progreso de descarga (auto-generado)
    ├── pdfs/               # Recibos en PDF
    └── xmls/               # Recibos en XML
```

## Sistema de Continuación

El scraper guarda automáticamente su progreso en `.scraper_progress.json`. Si el proceso se interrumpe:

### Ventajas:
- ✅ **No pierde progreso** si hay un error o interrupción
- ✅ **Ahorra tiempo** al no redescargar archivos existentes
- ✅ **Retoma automáticamente** desde el último recibo procesado

### Cómo funciona:
1. Después de cada descarga exitosa, guarda el índice actual
2. Al reiniciar, verifica si existe progreso guardado
3. Continúa desde el último punto guardado
4. Al completar todo, elimina el archivo de progreso

### Reiniciar manualmente:
```bash
# Opción 1: Variable de entorno
FORCE_RESTART=true poetry run python scraper.py

# Opción 2: Eliminar archivo de progreso
rm downloads/.scraper_progress.json
```

## Renombrado de Archivos

Algunos recibos de Oracle se descargan con nombres incompletos (ej: `14.pdf`, `23.xml`). El scraper:

1. **Detecta automáticamente** archivos con solo el número de día
2. **Extrae la fecha** del contenido del XML de nómina
3. **Renombra** con el formato completo: `Recibo Nomina YYYY_M_D.ext`

### Para archivos ya descargados:
```bash
poetry run python rename_existing_files.py
```

## Troubleshooting

### Error: "Credenciales no encontradas"

- Verifica que el archivo `.env` existe
- Verifica que las variables están correctamente definidas
- No dejes espacios alrededor del `=`

### Error: "No se pudo encontrar el campo de usuario/contraseña"

- Los selectores CSS necesitan ajuste
- Ejecuta en modo no-headless para inspeccionar la página
- Actualiza los selectores en `scraper.py`

### Error: "Login falló"

- Verifica tus credenciales
- Verifica que no haya autenticación de dos factores activa
- Revisa el screenshot `error_after_login.png`

### Error: "No se encontraron enlaces de descarga"

- Los selectores de recibos necesitan ajuste
- Revisa `payslip_page.png` y `payslips_page.html`
- Actualiza los `payslip_selectors` en el código

### El navegador no se abre en modo no-headless

- Verifica que Playwright instaló correctamente los navegadores:
  ```bash
  poetry run playwright install chromium --force
  ```

## Seguridad

### Buenas prácticas:

1. **Nunca compartas tu archivo `.env`**
2. **No subas credenciales a git**
3. **Usa contraseñas fuertes y únicas**
4. **Considera usar un gestor de contraseñas**
5. **Revisa regularmente tu actividad de login en Oracle**

### Términos de servicio:

- Asegúrate de que el uso de este script no viole las políticas de tu empresa
- Este script es para uso personal exclusivamente
- Úsalo de manera responsable

## Limitaciones

- Requiere ajuste de selectores según la estructura del portal
- No funciona con autenticación de dos factores (2FA)
- Puede romperse si Oracle actualiza su interfaz
- Requiere conexión a internet estable

## Mantenimiento

Si Oracle actualiza su portal y el script deja de funcionar:

1. Ejecuta en modo no-headless para ver el problema
2. Revisa los screenshots generados
3. Actualiza los selectores CSS necesarios
4. Prueba nuevamente

## Mejoras Futuras

Posibles mejoras que puedes implementar:

- Filtrar recibos por fecha
- Renombrar archivos con formato específico
- Enviar notificaciones cuando hay nuevos recibos
- Programar ejecución automática (cron/Task Scheduler)
- Soporte para múltiples usuarios
- Interfaz gráfica (GUI)

## Soporte

Si encuentras problemas:

1. Revisa la sección de Troubleshooting
2. Revisa los logs y screenshots generados
3. Ejecuta en modo no-headless para debugging
4. Ajusta los selectores según sea necesario

## Licencia

Este proyecto es de uso personal. Úsalo bajo tu propia responsabilidad.

---

**Nota importante:** Este script automatiza el acceso a un portal corporativo. Asegúrate de:
- Tener autorización para usar automatización
- Cumplir con las políticas de tu empresa
- Usar de manera responsable y ética
