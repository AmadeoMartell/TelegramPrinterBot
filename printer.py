import logging
import os
import win32print
import tempfile
import PyPDF2

logger = logging.getLogger(__name__)

def check_printer():
    """Проверяет доступность принтера по умолчанию."""
    try:
        printer_name = win32print.GetDefaultPrinter()
        return printer_name is not None
    except Exception as e:
        logger.error(f"Ошибка проверки принтера: {e}")
        return False

def validate_page_range(pages, total_pages):
    """Проверяет корректность диапазона страниц."""
    return all(1 <= page <= total_pages for page in pages)

async def print_file_directly(file_path, pages=None):
    """Печатает PDF файл с выбором диапазона страниц."""
    if not check_printer():
        raise EnvironmentError("Принтер по умолчанию недоступен.")

    try:
        printer_name = win32print.GetDefaultPrinter()
        logger.info(f"Используем принтер: {printer_name}")

        hprinter = win32print.OpenPrinter(printer_name)
        try:
            job = win32print.StartDocPrinter(hprinter, 1, ("Print Job", None, "RAW"))
            win32print.StartPagePrinter(hprinter)

            if pages:
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    writer = PyPDF2.PdfWriter()

                    total_pages = len(reader.pages)
                    if not validate_page_range(pages, total_pages):
                        raise ValueError(f"Некорректный диапазон страниц: {pages}. Всего страниц: {total_pages}.")

                    for page_number in pages:
                        writer.add_page(reader.pages[page_number - 1])

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                        writer.write(temp_pdf)
                        temp_pdf_path = temp_pdf.name

                    with open(temp_pdf_path, "rb") as temp_f:
                        win32print.WritePrinter(hprinter, temp_f.read())

                    try:
                        os.remove(temp_pdf_path)
                        logger.info(f"Временный файл {temp_pdf_path} успешно удален.")
                    except Exception as cleanup_error:
                        logger.error(f"Ошибка удаления временного файла {temp_pdf_path}: {cleanup_error}")
            else:
                with open(file_path, "rb") as f:
                    win32print.WritePrinter(hprinter, f.read())

            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
            logger.info(f"Файл {file_path} успешно отправлен на печать.")
        finally:
            win32print.ClosePrinter(hprinter)
    except Exception as e:
        logger.error(f"Ошибка при печати файла {file_path}: {e}", exc_info=True)
        raise
