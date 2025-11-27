#!/usr/bin/env python3
"""
Script para renombrar archivos existentes con nombres incompletos
Procesa archivos que solo tienen el día como nombre (ej: 14.pdf, 23.xml)
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


def log(message: str):
    """Imprime mensaje con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def extract_date_from_xml(xml_path: Path) -> tuple:
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

        log(f"⚠ No se encontró fecha en el XML: {xml_path.name}")
        return None

    except Exception as e:
        log(f"Error leyendo XML {xml_path.name}: {str(e)}")
        return None


def rename_xml_files(xml_path: Path):
    """Renombra archivos XML con nombres incompletos"""
    renamed_count = 0

    for xml_file in xml_path.glob("*.xml"):
        # Verificar si el nombre es solo un número (día)
        if xml_file.stem.isdigit():
            log(f"\n📄 Procesando XML: {xml_file.name}")

            # Extraer fecha del contenido del XML
            date_info = extract_date_from_xml(xml_file)

            if date_info:
                year, month, day = date_info
                new_filename = f"Recibo Nomina {year}_{month}_{day}.xml"
                new_filepath = xml_file.parent / new_filename

                # Verificar si ya existe un archivo con ese nombre
                if new_filepath.exists():
                    log(f"⚠ Ya existe un archivo con el nombre: {new_filename}")
                    continue

                # Renombrar el archivo
                xml_file.rename(new_filepath)
                log(f"✓ Renombrado a: {new_filename}")
                renamed_count += 1
            else:
                log(f"✗ No se pudo extraer la fecha del XML: {xml_file.name}")

    return renamed_count


def rename_pdf_files(pdf_path: Path, xml_path: Path):
    """Renombra archivos PDF con nombres incompletos usando sus XMLs correspondientes"""
    renamed_count = 0

    for pdf_file in pdf_path.glob("*.pdf"):
        # Verificar si el nombre es solo un número (día)
        if pdf_file.stem.isdigit():
            log(f"\n📄 Procesando PDF: {pdf_file.name}")

            # Buscar XML correspondiente
            day_number = pdf_file.stem
            xml_file = xml_path / f"{day_number}.xml"

            # Intentar primero con el XML renombrado
            if not xml_file.exists():
                # Buscar XMLs que ya fueron renombrados y terminan con el mismo día
                found_xml = None
                for renamed_xml in xml_path.glob(f"Recibo Nomina *_{day_number}.xml"):
                    found_xml = renamed_xml
                    break

                if found_xml:
                    # Extraer año y mes del nombre del XML renombrado
                    # Formato: "Recibo Nomina YYYY_M_D.xml"
                    parts = found_xml.stem.replace("Recibo Nomina ", "").split('_')
                    if len(parts) == 3:
                        year, month, day = parts
                        new_filename = f"Recibo Nomina {year}_{month}_{day}.pdf"
                        new_filepath = pdf_file.parent / new_filename

                        # Verificar si ya existe
                        if new_filepath.exists():
                            log(f"⚠ Ya existe un archivo con el nombre: {new_filename}")
                            continue

                        pdf_file.rename(new_filepath)
                        log(f"✓ Renombrado a: {new_filename} (usando XML renombrado)")
                        renamed_count += 1
                        continue

            # Si existe el XML original, extraer la fecha de él
            if xml_file.exists():
                date_info = extract_date_from_xml(xml_file)

                if date_info:
                    year, month, day = date_info
                    new_filename = f"Recibo Nomina {year}_{month}_{day}.pdf"
                    new_filepath = pdf_file.parent / new_filename

                    # Verificar si ya existe
                    if new_filepath.exists():
                        log(f"⚠ Ya existe un archivo con el nombre: {new_filename}")
                        continue

                    pdf_file.rename(new_filepath)
                    log(f"✓ Renombrado a: {new_filename}")
                    renamed_count += 1
                else:
                    log(f"✗ No se pudo extraer la fecha del XML: {xml_file.name}")
            else:
                log(f"✗ No se encontró XML correspondiente para: {pdf_file.name}")

    return renamed_count


def main():
    """Función principal"""
    log("=== Iniciando renombrado de archivos existentes ===\n")

    # Definir rutas
    downloads_path = Path("./downloads")
    xml_path = downloads_path / "xmls"
    pdf_path = downloads_path / "pdfs"

    # Verificar que existan las carpetas
    if not xml_path.exists():
        log(f"ERROR: No se encontró la carpeta de XMLs: {xml_path}")
        return

    if not pdf_path.exists():
        log(f"ERROR: No se encontró la carpeta de PDFs: {pdf_path}")
        return

    # Procesar XMLs primero
    log("=" * 60)
    log("PASO 1: Renombrando archivos XML")
    log("=" * 60)
    xml_renamed = rename_xml_files(xml_path)

    # Procesar PDFs
    log("\n" + "=" * 60)
    log("PASO 2: Renombrando archivos PDF")
    log("=" * 60)
    pdf_renamed = rename_pdf_files(pdf_path, xml_path)

    # Resumen
    log("\n" + "=" * 60)
    log("RESUMEN")
    log("=" * 60)
    log(f"✓ XMLs renombrados: {xml_renamed}")
    log(f"✓ PDFs renombrados: {pdf_renamed}")
    log(f"✓ Total de archivos renombrados: {xml_renamed + pdf_renamed}")
    log("\n=== Proceso completado ===")


if __name__ == "__main__":
    main()
