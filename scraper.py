#!/usr/bin/env python3
"""
Oracle Payslip Scraper
Automatiza la descarga de recibos de nómina del portal de Oracle
"""

import os
import sys
import time
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

    def __init__(self, username: str, password: str, download_path: str = "./downloads", headless: bool = True):
        """
        Inicializa el scraper

        Args:
            username: Email de usuario
            password: Contraseña
            download_path: Carpeta donde guardar los PDFs
            headless: Si True, ejecuta el navegador sin interfaz gráfica
        """
        self.username = username
        self.password = password
        self.download_path = Path(download_path)
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Crear carpetas de descargas si no existen
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.pdf_path = self.download_path / "pdfs"
        self.xml_path = self.download_path / "xmls"
        self.pdf_path.mkdir(parents=True, exist_ok=True)
        self.xml_path.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """Imprime mensaje con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

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
            downloaded = 0
            idx = 0
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

                    self.log(f"\n--- Procesando recibo {idx + 1} (enlaces disponibles: {len(current_links)}) ---")

                    # Si no hay suficientes enlaces cargados, intentar cargar más
                    if idx >= len(current_links):
                        self.log(f"Necesitamos cargar más elementos (idx={idx}, disponibles={len(current_links)})")

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
                            break

                        # Si aún no hay suficientes enlaces después de cargar, terminar
                        if idx >= len(current_links):
                            self.log(f"No hay más recibos disponibles (idx={idx}, enlaces={len(current_links)})")
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

                            # Pequeña pausa entre descargas
                            time.sleep(1)

                        except Exception as e:
                            self.log(f"Error descargando archivo {download_idx + 1}: {str(e)}")

                    if files_downloaded_count > 0:
                        self.log(f"✓ Total de archivos descargados para recibo {idx + 1}: {files_downloaded_count}")
                        downloaded += 1
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

                    time.sleep(3)
                    self.page.wait_for_load_state("networkidle", timeout=30000)
                    time.sleep(2)

                    # IMPORTANTE: Volver a cargar elementos de forma inteligente
                    # Calcular cuántos clics son necesarios basado en el índice actual
                    # Files 0-9: 0 clicks, 10-19: 1 click, 20-29: 2 clicks, etc.
                    clicks_needed = idx // 10

                    self.log(f"Volviendo a cargar elementos (necesarios: {clicks_needed} clics)...")
                    load_more_clicks = 0
                    while load_more_clicks < clicks_needed:
                        load_more_found = False
                        for selector in ['a:has-text("Cargar Más Elementos")', 'a[id*="fchmrlnk"]']:
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
                            break
                    self.log(f"Elementos recargados (clics: {load_more_clicks}/{clicks_needed})")
                    time.sleep(1)

                    # Incrementar el índice para el siguiente archivo
                    idx += 1

                except Exception as e:
                    self.log(f"✗ Error procesando recibo {idx + 1}: {str(e)}")
                    # Intentar volver a la lista usando botón Atrás
                    try:
                        back_selectors = ['a[title="Atrás"]', 'a[class*="svg-universalPanel"]']
                        for sel in back_selectors:
                            if self.page.locator(sel).count() > 0:
                                self.page.locator(sel).first.click()
                                break
                        time.sleep(2)
                        self.page.wait_for_load_state("networkidle", timeout=30000)
                    except:
                        # Si el botón falla, usar URL
                        try:
                            self.page.goto(documents_page_url)
                            time.sleep(2)
                        except:
                            pass

                    # Incrementar índice incluso en caso de error
                    idx += 1
                    continue

            self.log(f"\n=== Descarga completada: {downloaded} recibos procesados exitosamente ===")
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

    # Crear y ejecutar scraper
    scraper = OraclePayslipScraper(
        username=username,
        password=password,
        download_path=download_path,
        headless=headless
    )

    success = scraper.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
