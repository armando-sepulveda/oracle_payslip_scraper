#!/usr/bin/env python3
"""
Oracle Payslip Scraper
Automatiza la descarga de recibos de nómina del portal de Oracle
"""

import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from playwright.sync_api import (
    Browser,
    Page,
    Playwright,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


class OraclePayslipScraper:
    """Scraper para descargar recibos de nómina de Oracle Cloud"""

    def __init__(self, username: str, password: str, download_path: str = "./downloads", headless: bool = True, force_restart: bool = False):
        """
        Inicializa el scraper

        Args:
            username: Email de usuario
            password: Contraseña
            download_path: Carpeta donde guardar los PDFs
            headless: Si True, ejecuta el navegador sin interfaz gráfica
            force_restart: Si True, ignora el progreso guardado y reinicia desde el principio
        """
        self.username = username
        self.password = password
        self.download_path = Path(download_path)
        self.headless = headless
        self.force_restart = force_restart
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Crear carpetas de descargas si no existen
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.pdf_path = self.download_path / "pdfs"
        self.xml_path = self.download_path / "xmls"
        self.pdf_path.mkdir(parents=True, exist_ok=True)
        self.xml_path.mkdir(parents=True, exist_ok=True)

        # Archivo para guardar el progreso
        self.progress_file = self.download_path / ".scraper_progress.json"

    def log(self, message: str):
        """Imprime mensaje con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def save_progress(self, idx: int, downloaded: int):
        """Guarda el progreso actual de la descarga"""
        try:
            progress_data = {
                "last_index": idx,
                "total_downloaded": downloaded,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.log(f"⚠ Error guardando progreso: {str(e)}")

    def load_progress(self) -> tuple:
        """Carga el progreso guardado
        
        Returns:
            Tupla (last_index, total_downloaded) o (0, 0) si no hay progreso guardado
        """
        if self.force_restart:
            self.log("🔄 Reinicio forzado: ignorando progreso guardado")
            # Eliminar archivo de progreso si existe
            if self.progress_file.exists():
                self.progress_file.unlink()
            return (0, 0)

        if not self.progress_file.exists():
            return (0, 0)

        try:
            with open(self.progress_file, 'r') as f:
                progress_data = json.load(f)
            
            last_index = progress_data.get('last_index', 0)
            total_downloaded = progress_data.get('total_downloaded', 0)
            last_updated = progress_data.get('last_updated', 'desconocido')

            self.log(f"📊 Progreso encontrado: último índice={last_index}, descargados={total_downloaded}")
            self.log(f"📅 Última actualización: {last_updated}")
            
            return (last_index, total_downloaded)
        except Exception as e:
            self.log(f"⚠ Error cargando progreso: {str(e)}")
            return (0, 0)

    def clear_progress(self):
        """Elimina el archivo de progreso"""
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
                self.log("✓ Archivo de progreso eliminado")
        except Exception as e:
            self.log(f"⚠ Error eliminando progreso: {str(e)}")

    def rename_payslip_file(self, filepath: Path) -> Optional[str]:
        """
        Renombra un archivo de recibo que solo tiene el día como nombre
        extrayendo la fecha completa del XML correspondiente o de la página

        Args:
            filepath: Ruta del archivo a renombrar

        Returns:
            Nuevo nombre del archivo si se renombró exitosamente, None en caso contrario
        """
        try:
            extension = filepath.suffix.lower()
            original_name = filepath.name

            # Estrategia 1: Si es un XML, extraer la fecha directamente del contenido
            if extension == '.xml':
                date_info = self.extract_date_from_xml(filepath)
                if date_info:
                    year, month, day = date_info
                    new_filename = f"Recibo Nomina {year}_{month}_{day}.xml"
                    new_filepath = filepath.parent / new_filename

                    # Verificar si ya existe un archivo con ese nombre
                    if new_filepath.exists() and new_filepath != filepath:
                        self.log(f"⚠ Ya existe {new_filename}, eliminando duplicado...")
                        filepath.unlink()  # Eliminar el archivo duplicado
                        return None

                    # Renombrar el archivo
                    filepath.rename(new_filepath)
                    return new_filename

            # Estrategia 2: Si es un PDF, buscar el XML correspondiente
            elif extension == '.pdf':
                # Buscar XML con el mismo nombre base (solo el día)
                day_number = filepath.stem
                xml_file = self.xml_path / f"{day_number}.xml"

                if xml_file.exists():
                    date_info = self.extract_date_from_xml(xml_file)
                    if date_info:
                        year, month, day = date_info
                        new_filename = f"Recibo Nomina {year}_{month}_{day}.pdf"
                        new_filepath = filepath.parent / new_filename

                        # Verificar si ya existe un archivo con ese nombre
                        if new_filepath.exists() and new_filepath != filepath:
                            self.log(f"⚠ Ya existe {new_filename}, eliminando duplicado...")
                            filepath.unlink()  # Eliminar el archivo duplicado
                            return None

                        # Renombrar el archivo
                        filepath.rename(new_filepath)
                        return new_filename

            # Estrategia 3: Intentar extraer fecha de la página de detalle
            date_info = self.extract_date_from_page()
            if date_info:
                year, month, day = date_info
                new_filename = f"Recibo Nomina {year}_{month}_{day}{extension}"
                new_filepath = filepath.parent / new_filename

                filepath.rename(new_filepath)
                return new_filename

            self.log(f"⚠ No se pudo extraer fecha para renombrar: {original_name}")
            return None

        except Exception as e:
            self.log(f"Error renombrando archivo {filepath.name}: {str(e)}")
            return None

    def extract_date_from_xml(self, xml_path: Path) -> Optional[tuple]:
        """
        Extrae la fecha de un archivo XML de nómina de Oracle

        Args:
            xml_path: Ruta del archivo XML

        Returns:
            Tupla (año, mes, día) o None si no se pudo extraer
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Definir namespaces comunes en XMLs de CFDI de nómina
            namespaces = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4',
                'cfdi3': 'http://www.sat.gob.mx/cfd/3',
                'nomina12': 'http://www.sat.gob.mx/nomina12'
            }

            date_str = None

            # PRIORIDAD 1: Buscar FechaPago en el elemento Nomina (más preciso)
            # Esto es la fecha real del pago de nómina
            for nomina_elem in root.findall('.//nomina12:Nomina', namespaces):
                if 'FechaPago' in nomina_elem.attrib:
                    date_str = nomina_elem.attrib['FechaPago']
                    break

            # PRIORIDAD 2: Si no hay FechaPago, usar Fecha del Comprobante
            if not date_str and 'Fecha' in root.attrib:
                date_str = root.attrib['Fecha']

            if date_str:
                # Parsear la fecha (formato común: "2024-04-23T12:00:00" o "2024-04-23")
                date_part = date_str.split('T')[0]  # Separar la parte de fecha de la hora
                parts = date_part.split('-')

                if len(parts) == 3:
                    year = parts[0]
                    month = parts[1].lstrip('0')  # Quitar ceros a la izquierda
                    day = parts[2].lstrip('0')    # Quitar ceros a la izquierda
                    return (year, month, day)

            self.log(f"⚠ No se encontró fecha en el XML: {xml_path.name}")
            return None

        except Exception as e:
            self.log(f"Error leyendo XML {xml_path.name}: {str(e)}")
            return None

    def extract_date_from_page(self) -> Optional[tuple]:
        """
        Intenta extraer la fecha de la página de detalle actual

        Returns:
            Tupla (año, mes, día) o None si no se pudo extraer
        """
        try:
            # Buscar elementos de texto que contengan fechas en la página
            # Común en páginas de Oracle: "Fecha: DD/MM/YYYY" o similar
            page_text = self.page.content()

            # Patrones comunes de fecha
            import re
            patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            ]

            for pattern in patterns:
                match = re.search(pattern, page_text)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Determinar el orden basado en el patrón
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                            year, month, day = groups
                        else:  # DD/MM/YYYY o DD-MM-YYYY
                            day, month, year = groups

                        # Normalizar (quitar ceros a la izquierda)
                        month = str(int(month))
                        day = str(int(day))

                        return (year, month, day)

            return None

        except Exception as e:
            self.log(f"Error extrayendo fecha de la página: {str(e)}")
            return None


    def start_browser(self, playwright: Playwright):
        """Inicia el navegador"""
        self.log("Iniciando navegador...")
        self.browser = playwright.chromium.launch(headless=self.headless)

        # Crear contexto con permisos para descargas
        context = self.browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 900}
        )

        self.page = context.new_page()
        self.log("Navegador iniciado correctamente")

    def login(self):
        """Realiza el login en Oracle"""
        self.log("Navegando a la página de login...")

        try:
            # Navegar a la página de login
            self.page.goto("https://ehyn.login.us6.oraclecloud.com/", timeout=60000)
            self.log("Página de login cargada")

            # Esperar a que cargue el formulario de login
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)  # Pequeña pausa adicional

            # NOTA: Estos selectores pueden necesitar ajustes según la estructura real del sitio
            # Inspecciona la página con las herramientas de desarrollo del navegador

            # Intentar encontrar el campo de usuario (múltiples estrategias)
            self.log("Ingresando credenciales...")

            # Estrategia 1: Por ID común de Oracle
            username_selectors = [
                'input[type="text"][name*="username" i]',
                'input[type="text"][name*="user" i]',
                'input[type="email"]',
                'input#userid',
                'input#username',
                'input[name="ssousername"]',
                'input[autocomplete="username"]',
            ]

            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input#password',
                'input[name="ssopassword"]',
            ]

            button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Sign In")',
                'button:has-text("Iniciar")',
                'button:has-text("Login")',
            ]

            # Intentar llenar el usuario
            username_filled = False
            for selector in username_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, self.username)
                        username_filled = True
                        self.log(f"Usuario ingresado usando selector: {selector}")
                        break
                except Exception:
                    continue

            if not username_filled:
                self.log("ERROR: No se pudo encontrar el campo de usuario")
                self.log("Por favor, inspecciona la página y actualiza los selectores")
                self.page.screenshot(path=str(self.download_path / "error_login_page.png"))
                return False

            time.sleep(1)

            # Intentar llenar la contraseña
            password_filled = False
            for selector in password_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, self.password)
                        password_filled = True
                        self.log(f"Contraseña ingresada usando selector: {selector}")
                        break
                except Exception:
                    continue

            if not password_filled:
                self.log("ERROR: No se pudo encontrar el campo de contraseña")
                self.page.screenshot(path=str(self.download_path / "error_password_page.png"))
                return False

            time.sleep(1)

            # Intentar hacer clic en el botón de login
            button_clicked = False
            for selector in button_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.log(f"Haciendo clic en botón de login: {selector}")
                        self.page.click(selector)
                        button_clicked = True
                        break
                except Exception:
                    continue

            if not button_clicked:
                self.log("ERROR: No se pudo encontrar el botón de login")
                self.page.screenshot(path=str(self.download_path / "error_button_page.png"))
                return False

            # Esperar a que se complete el login
            self.log("Esperando respuesta del servidor...")
            self.page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(3)

            # Verificar si el login fue exitoso
            current_url = self.page.url
            self.log(f"URL actual después del login: {current_url}")

            if "login" in current_url.lower():
                self.log("ERROR: Parece que el login falló (aún en página de login)")
                self.page.screenshot(path=str(self.download_path / "error_after_login.png"))
                return False

            self.log("Login exitoso")
            return True

        except PlaywrightTimeoutError as e:
            self.log(f"ERROR: Timeout durante el login: {str(e)}")
            self.page.screenshot(path=str(self.download_path / "error_timeout.png"))
            return False
        except Exception as e:
            self.log(f"ERROR durante el login: {str(e)}")
            self.page.screenshot(path=str(self.download_path / "error_exception.png"))
            return False

    def navigate_to_payslips(self):
        """Navega a la página de recibos de nómina"""
        self.log("Navegando a la página de información personal...")

        try:
            # Navegar a la página de información personal
            info_url = "https://ehyn.fa.us6.oraclecloud.com/hcmUI/faces/FndOverview?fnd=%3B%3B%3B%3Bfalse%3B256%3B%3B%3B&fndGlobalItemNodeId=PER_HCMPEOPLETOP_FUSE_PER_INFO"

            self.page.goto(info_url, timeout=60000)
            self.page.wait_for_load_state("networkidle")
            time.sleep(3)

            self.log("Página de información personal cargada")
            self.page.screenshot(path=str(self.download_path / "personal_info_page.png"))

            # Hacer clic en "Registros de documentos"
            self.log("Buscando sección de Registros de documentos...")

            # Múltiples selectores para encontrar el enlace de documentos
            document_selectors = [
                'a:has-text("Registros de documentos")',
                'div:has-text("Registros de documentos")',
                'span:has-text("Registros de documentos")',
                '*:has-text("Registros de documentos")',
            ]

            clicked = False
            for selector in document_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.log(f"Encontrado con selector: {selector}")
                        # Esperar a que sea clickeable
                        self.page.locator(selector).first.click(timeout=10000)
                        clicked = True
                        self.log("Clic en Registros de documentos exitoso")
                        break
                except Exception as e:
                    self.log(f"Intento fallido con selector {selector}: {str(e)}")
                    continue

            if not clicked:
                self.log("ERROR: No se pudo hacer clic en Registros de documentos")
                return False

            # Esperar a que cargue la nueva página
            self.page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(3)

            self.log("Página de documentos cargada")
            self.page.screenshot(path=str(self.download_path / "documents_page.png"))

            return True

        except Exception as e:
            self.log(f"ERROR al navegar a recibos: {str(e)}")
            self.page.screenshot(path=str(self.download_path / "error_navigate_payslips.png"))
            return False

    def download_payslips(self):
        """Descarga todos los recibos de nómina disponibles"""
        self.log("Preparando para buscar recibos de nómina...")

        try:
            # PASO 1: Quitar el filtro de "Nómina" que está excluyendo los documentos
            self.log("Quitando filtro de exclusión de Nómina...")

            # Buscar el filtro con la X para cerrarlo
            filter_selectors = [
                'a[title="Eliminar filtro: Nómina"]',  # Selector exacto del botón X
                'a[title*="Eliminar filtro: Nómina"]',
                'a[title*="Eliminar filtro"]img[alt*="Nómina"]',
                'span:has-text("Nómina") + a',  # Backup: enlace junto al texto
            ]

            filter_removed = False
            for selector in filter_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.log(f"Encontrado filtro con selector: {selector}")
                        self.page.locator(selector).first.click()
                        filter_removed = True
                        self.log("✓ Filtro de Nómina removido")
                        time.sleep(2)
                        break
                except Exception as e:
                    self.log(f"Intento fallido con selector {selector}: {str(e)}")
                    continue

            if not filter_removed:
                self.log("ADVERTENCIA: No se pudo quitar el filtro automáticamente")
                self.log("Intentando continuar de todas formas...")

            # Esperar a que se recarguen los documentos
            self.page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(2)

            # Guardar la URL de la página de documentos para volver después
            documents_page_url = self.page.url
            self.log(f"URL de documentos guardada: {documents_page_url}")

            # Tomar screenshot después de quitar filtro
            self.page.screenshot(path=str(self.download_path / "after_filter_removal.png"))
            time.sleep(2)

            # PASO 2: Buscar recibos de nómina y procesarlos incrementalmente
            self.log("Iniciando descarga de recibos...")

            # Guardar HTML para debugging
            html_content = self.page.content()
            with open(self.download_path / "documents_full.html", "w", encoding="utf-8") as f:
                f.write(html_content)

            # Buscar los botones de "Ver más detalles" (icono de lentes)
            payslip_link_selectors = [
                'a[title="Ver más detalles"]',
                'img[alt="Ver más detalles"]',
                'img[src*="func_glasses"]',
            ]

            # Selectores para "Cargar Más Elementos"
            load_more_selectors = [
                'a:has-text("Cargar Más Elementos")',
                'a:has-text("Load More")',
                'a[id*="fchmrlnk"]',
                'button:has-text("Cargar Más")',
            ]

            # PASO 3: Hacer clic en cada recibo, ir a su página de detalle y descargar
            # Procesar hasta 250 archivos (límite de seguridad)
            
            # Cargar progreso previo
            idx, downloaded = self.load_progress()
            
            if idx > 0:
                self.log(f"\n▶ Continuando desde el recibo #{idx + 1}...")
                self.log(f"Ya se han descargado {downloaded} recibos previamente\n")
            else:
                self.log(f"\n▶ Iniciando descarga desde el principio...\n")
            
            max_files = 250

            while idx < max_files:
                try:
                    # Esperar un poco para asegurar que la página cargó completamente
                    time.sleep(2)

                    # Relocalizar los enlaces disponibles actualmente
                    current_links = []
                    for selector in payslip_link_selectors:
                        try:
                            current_links = self.page.locator(selector).all()
                            if current_links:
                                break
                        except Exception:
                            continue

                    # Calcular el índice relativo dentro de los enlaces cargados
                    # idx es absoluto, pero current_links solo tiene los elementos visibles
                    # Necesitamos cargar suficientes elementos para alcanzar el índice actual
                    clicks_needed = idx // 10  # Cada "Cargar Más" añade ~10 elementos
                    
                    self.log(f"\n--- Procesando recibo {idx + 1} (enlaces disponibles: {len(current_links)}, clics necesarios: {clicks_needed}) ---")

                    # Si no hay suficientes enlaces cargados, cargar más hasta tener suficientes
                    while len(current_links) <= idx:
                        self.log(f"Cargando más elementos (idx={idx}, disponibles={len(current_links)})...")

                        # Intentar hacer clic en "Cargar Más Elementos"
                        load_more_clicked = False
                        for selector in load_more_selectors:
                            try:
                                if self.page.locator(selector).count() > 0:
                                    load_more_button = self.page.locator(selector).first
                                    if load_more_button.is_visible(timeout=2000):
                                        self.log("Haciendo clic en 'Cargar Más Elementos'...")
                                        load_more_button.click()
                                        load_more_clicked = True
                                        time.sleep(2)
                                        self.page.wait_for_load_state("networkidle", timeout=15000)
                                        time.sleep(1)

                                        # Relocalizar enlaces después de cargar más
                                        for sel in payslip_link_selectors:
                                            try:
                                                current_links = self.page.locator(sel).all()
                                                if current_links:
                                                    self.log(f"Después de cargar: {len(current_links)} enlaces disponibles")
                                                    break
                                            except Exception:
                                                continue
                                        break
                            except Exception:
                                continue

                        # Si no se pudo hacer clic en "Cargar Más", no hay más elementos
                        if not load_more_clicked:
                            self.log(f"No se encontró botón 'Cargar Más'. Terminando descarga.")
                            # Terminar el bucle principal
                            idx = max_files
                            break

                    # Verificar que tenemos suficientes enlaces después de cargar
                    if idx >= len(current_links):
                        self.log(f"No hay más recibos disponibles después de cargar (idx={idx}, enlaces={len(current_links)})")
                        break

                    # Hacer clic en el enlace del recibo
                    self.log(f"Haciendo clic en el recibo {idx + 1}...")
                    current_links[idx].click()
                    time.sleep(3)

                    # Esperar a que cargue la página de detalle
                    self.page.wait_for_load_state("networkidle", timeout=30000)
                    time.sleep(2)

                    self.log("Página de detalle cargada")
                    self.page.screenshot(path=str(self.download_path / f"detail_page_{idx + 1}.png"))

                    # Buscar y descargar AMBOS archivos: XML y PDF
                    # En la página de detalle, buscar todos los archivos descargables
                    files_downloaded_count = 0

                    # Buscar archivos XML
                    xml_links = self.page.locator('span:has-text(".xml")').all()
                    self.log(f"Encontrados {len(xml_links)} archivos XML")

                    # Buscar archivos PDF
                    pdf_links = self.page.locator('span:has-text(".pdf")').all()
                    self.log(f"Encontrados {len(pdf_links)} archivos PDF")

                    # Buscar todos los iconos de descarga
                    download_icons = self.page.locator('img[src*="download"]').all()
                    self.log(f"Total de iconos de descarga encontrados: {len(download_icons)}")

                    # Descargar todos los archivos y clasificarlos por extensión
                    for download_idx in range(len(download_icons)):
                        try:
                            # Re-localizar los iconos en cada iteración
                            download_icons = self.page.locator('img[src*="download"]').all()

                            if download_idx >= len(download_icons):
                                break

                            self.log(f"Descargando archivo {download_idx + 1}/{len(download_icons)}...")

                            with self.page.expect_download(timeout=20000) as download_info:
                                download_icons[download_idx].click()

                            download = download_info.value
                            filename = download.suggested_filename or f"archivo_{idx + 1}_{download_idx + 1}"

                            # Detectar si el archivo tiene solo el número de día (ej: "14.pdf" o "23.xml")
                            # y necesita ser renombrado con el formato completo
                            needs_rename = False
                            if filename.lower().endswith(('.xml', '.pdf')):
                                # Verificar si el nombre es solo un número (día)
                                name_without_ext = filename.rsplit('.', 1)[0]
                                if name_without_ext.isdigit():
                                    needs_rename = True
                                    self.log(f"⚠ Archivo con nombre incompleto detectado: {filename}")

                            # Clasificar por extensión y guardar en la carpeta correcta
                            if filename.lower().endswith('.xml'):
                                filepath = self.xml_path / filename
                                self.log(f"✓ Descargado XML: {filename}")
                                files_downloaded_count += 1
                            elif filename.lower().endswith('.pdf'):
                                filepath = self.pdf_path / filename
                                self.log(f"✓ Descargado PDF: {filename}")
                                files_downloaded_count += 1
                            else:
                                # Guardar otros archivos en downloads/
                                filepath = self.download_path / filename
                                self.log(f"✓ Descargado otro archivo: {filename}")
                                files_downloaded_count += 1

                            download.save_as(filepath)

                            # Si necesita renombrado, intentar extraer la fecha
                            if needs_rename:
                                new_filename = self.rename_payslip_file(filepath)
                                if new_filename:
                                    self.log(f"✓ Archivo renombrado a: {new_filename}")

                            # Pequeña pausa entre descargas
                            time.sleep(1)

                        except Exception as e:
                            self.log(f"Error descargando archivo {download_idx + 1}: {str(e)}")

                    if files_downloaded_count > 0:
                        self.log(f"✓ Total de archivos descargados para recibo {idx + 1}: {files_downloaded_count}")
                        downloaded += 1
                        
                        # Guardar progreso después de cada descarga exitosa
                        self.save_progress(idx + 1, downloaded)
                    else:
                        self.log(f"✗ No se pudo descargar ningún archivo para recibo {idx + 1}")
                        self.page.screenshot(path=str(self.download_path / f"no_download_{idx + 1}.png"))

                    # Volver a la lista de recibos usando el botón Atrás
                    self.log("Haciendo clic en botón Atrás para volver a la lista...")
                    back_button_selectors = [
                        'a[title="Atrás"]',
                        'a[title="Atrás"][class*="svg-universalPanel"]',
                        '#_FOpt1\\:_FOr1\\:0\\:_FONSr2\\:0\\:MAnt2\\:0\\:dorDUpl\\:UPsp1\\:SPdonei',
                    ]

                    back_clicked = False
                    for back_sel in back_button_selectors:
                        try:
                            if self.page.locator(back_sel).count() > 0:
                                self.log(f"Encontrado botón Atrás con selector: {back_sel}")
                                self.page.locator(back_sel).first.click()
                                back_clicked = True
                                break
                        except Exception as e:
                            self.log(f"Error con selector {back_sel}: {str(e)}")

                    if not back_clicked:
                        self.log("No se encontró botón Atrás, usando navegación por URL...")
                        self.page.goto(documents_page_url)

                    # Esperar a que la página se cargue completamente
                    time.sleep(3)
                    self.page.wait_for_load_state("networkidle", timeout=30000)
                    time.sleep(2)
                    
                    # CRÍTICO: Verificar que volvimos a la lista correctamente
                    # Intentar relocalizar los enlaces de recibos
                    self.log("Verificando que la lista de recibos se cargó correctamente...")
                    verification_attempts = 0
                    max_verification_attempts = 3
                    
                    while verification_attempts < max_verification_attempts:
                        # Intentar encontrar enlaces de recibos
                        temp_links = []
                        for selector in payslip_link_selectors:
                            try:
                                temp_links = self.page.locator(selector).all()
                                if temp_links and len(temp_links) > 0:
                                    self.log(f"✓ Lista verificada: {len(temp_links)} enlaces encontrados")
                                    break
                            except Exception:
                                continue
                        
                        if temp_links and len(temp_links) > 0:
                            break
                        
                        # Si no encontramos enlaces, esperar y reintentar
                        verification_attempts += 1
                        if verification_attempts < max_verification_attempts:
                            self.log(f"⚠ No se encontraron enlaces, reintentando ({verification_attempts}/{max_verification_attempts})...")
                            time.sleep(3)
                            self.page.wait_for_load_state("networkidle", timeout=15000)
                        else:
                            self.log("❌ No se pudo verificar la lista después de volver. Usando navegación por URL...")
                            self.page.goto(documents_page_url)
                            time.sleep(3)
                            self.page.wait_for_load_state("networkidle", timeout=30000)
                            time.sleep(2)

                    # IMPORTANTE: Después de volver, necesitamos recargar los elementos
                    # La página vuelve al estado inicial (solo 10 elementos visibles)
                    # Necesitamos hacer clic en "Cargar Más" suficientes veces para
                    # tener visible el siguiente elemento que vamos a procesar
                    
                    # El siguiente índice será idx + 1
                    next_idx = idx + 1
                    clicks_needed = next_idx // 10
                    
                    if clicks_needed > 0:
                        self.log(f"Recargando elementos para el siguiente recibo (necesarios: {clicks_needed} clics)...")
                        load_more_clicks = 0
                        while load_more_clicks < clicks_needed:
                            load_more_found = False
                            for selector in load_more_selectors:
                                try:
                                    if self.page.locator(selector).count() > 0:
                                        load_more_button = self.page.locator(selector).first
                                        if load_more_button.is_visible(timeout=2000):
                                            load_more_button.click()
                                            load_more_found = True
                                            load_more_clicks += 1
                                            time.sleep(2)
                                            self.page.wait_for_load_state("networkidle", timeout=15000)
                                            time.sleep(1)
                                            break
                                except Exception:
                                    continue
                            if not load_more_found:
                                self.log(f"⚠ No se pudo encontrar botón 'Cargar Más' (clic {load_more_clicks + 1}/{clicks_needed})")
                                break
                        self.log(f"Elementos recargados (clics realizados: {load_more_clicks}/{clicks_needed})")
                    
                    time.sleep(1)

                    # Incrementar el índice para el siguiente archivo
                    idx += 1

                except Exception as e:
                    self.log(f"✗ Error procesando recibo {idx + 1}: {str(e)}")
                    self.page.screenshot(path=str(self.download_path / f"error_recibo_{idx + 1}.png"))
                    
                    # Intentar volver a la lista usando botón Atrás
                    try:
                        self.log("Intentando volver a la lista después del error...")
                        back_selectors = ['a[title="Atrás"]', 'a[class*="svg-universalPanel"]']
                        back_recovered = False
                        
                        for sel in back_selectors:
                            if self.page.locator(sel).count() > 0:
                                self.page.locator(sel).first.click()
                                back_recovered = True
                                time.sleep(2)
                                self.page.wait_for_load_state("networkidle", timeout=30000)
                                break
                        
                        # Si el botón falla, usar URL
                        if not back_recovered:
                            self.log("Recuperando usando navegación por URL...")
                            self.page.goto(documents_page_url)
                            time.sleep(3)
                            self.page.wait_for_load_state("networkidle", timeout=30000)
                            time.sleep(2)
                    except Exception as recovery_error:
                        self.log(f"⚠ Error durante la recuperación: {str(recovery_error)}")
                        # Intentar navegar directamente a la URL de documentos
                        try:
                            self.page.goto(documents_page_url)
                            time.sleep(3)
                            self.page.wait_for_load_state("networkidle", timeout=30000)
                        except:
                            pass

                    # Incrementar índice incluso en caso de error
                    idx += 1
                    continue

            self.log(f"\n=== Descarga completada: {downloaded} recibos procesados exitosamente ===")
            
            # Limpiar archivo de progreso al completar
            self.clear_progress()
            
            return downloaded > 0

        except Exception as e:
            self.log(f"ERROR durante la descarga: {str(e)}")
            self.page.screenshot(path=str(self.download_path / "error_download.png"))
            return False

    def run(self):
        """Ejecuta el proceso completo de scraping"""
        self.log("=== Iniciando Oracle Payslip Scraper ===")

        try:
            with sync_playwright() as playwright:
                # Iniciar navegador
                self.start_browser(playwright)

                # Login
                if not self.login():
                    self.log("ERROR: Fallo en el login. Revisa las credenciales y los selectores.")
                    return False

                # Navegar a recibos
                if not self.navigate_to_payslips():
                    self.log("ERROR: No se pudo acceder a la página de recibos")
                    return False

                # Descargar recibos
                if not self.download_payslips():
                    self.log("ADVERTENCIA: Hubo problemas al descargar los recibos")
                    self.log("Revisa los screenshots y el HTML guardado para ajustar los selectores")

                self.log("=== Proceso completado ===")
                self.log(f"Archivos guardados en: {self.download_path.absolute()}")

                # Pausa para ver el resultado (solo en modo no-headless)
                if not self.headless:
                    self.log("Navegador abierto - Presiona Ctrl+C para cerrar")
                    time.sleep(300)  # 5 minutos de espera

                return True

        except KeyboardInterrupt:
            self.log("Proceso interrumpido por el usuario")
            return False
        except Exception as e:
            self.log(f"ERROR inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.browser:
                try:
                    self.browser.close()
                    self.log("Navegador cerrado")
                except Exception:
                    pass  # Ignorar errores al cerrar el navegador


def main():
    """Función principal"""
    # Cargar variables de entorno
    load_dotenv()

    # Obtener credenciales
    username = os.getenv("ORACLE_USERNAME")
    password = os.getenv("ORACLE_PASSWORD")

    if not username or not password:
        print("ERROR: Credenciales no encontradas")
        print("Asegúrate de crear un archivo .env con ORACLE_USERNAME y ORACLE_PASSWORD")
        sys.exit(1)

    # Configuración
    headless = os.getenv("HEADLESS", "true").lower() == "true"
    download_path = os.getenv("DOWNLOAD_PATH", "./downloads")
    force_restart = os.getenv("FORCE_RESTART", "false").lower() == "true"

    # Crear y ejecutar scraper
    scraper = OraclePayslipScraper(
        username=username,
        password=password,
        download_path=download_path,
        headless=headless,
        force_restart=force_restart
    )

    success = scraper.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
