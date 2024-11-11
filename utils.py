import os
import tempfile
import logging
import ctypes
import comtypes.client

logger = logging.getLogger(__name__)

def get_user_temp_folder(user_id):
    """Создает папку для хранения временных файлов пользователя."""
    folder = os.path.join(tempfile.gettempdir(), str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder

async def save_file_for_user(user_id, file, file_extension):
    """Сохраняет файл пользователя во временную папку."""
    folder = get_user_temp_folder(user_id)
    file_path = os.path.join(folder, file.file_name)
    new_file = await file.get_file()
    with open(file_path, "wb") as f:
        await new_file.download_to_drive(file_path)
    return file_path

def remove_file(file_path):
    """Удаляет конкретный файл."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Файл {file_path} успешно удален.")
        except Exception as e:
            logger.error(f"Ошибка удаления файла {file_path}: {e}")

def remove_user_folder_if_empty(user_id):
    """Удаляет папку пользователя, если она пуста."""
    folder = get_user_temp_folder(user_id)
    if os.path.exists(folder) and not os.listdir(folder):
        try:
            os.rmdir(folder)
            logger.info(f"Папка {folder} успешно удалена.")
        except Exception as e:
            logger.error(f"Ошибка удаления папки {folder}: {e}")

def convert_docx_to_pdf_with_word(docx_path, output_path):
    """Конвертирует DOCX в PDF через Microsoft Word."""
    ctypes.windll.ole32.CoInitialize(None)
    try:
        word = comtypes.client.CreateObject('Word.Application')
        word.Visible = False
        try:
            doc = word.Documents.Open(docx_path)
            doc.SaveAs(output_path, FileFormat=17)
            doc.Close()
            logger.info(f"Файл {docx_path} успешно конвертирован в {output_path}")
        except Exception as e:
            logger.error(f"Ошибка при конвертации DOCX в PDF: {e}", exc_info=True)
            raise
        finally:
            word.Quit()
    finally:
        ctypes.windll.ole32.CoUninitialize()
