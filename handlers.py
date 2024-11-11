import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from utils import save_file_for_user, remove_file, remove_user_folder_if_empty, convert_docx_to_pdf_with_word
from printer import print_file_directly, validate_page_range
import asyncio
import logging
import PyPDF2
import tempfile

logger = logging.getLogger(__name__)

async def start(update: Update, context):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Отправь мне PDF или DOCX файл, и я помогу их распечатать. "
        "После загрузки выберите файл и настройте диапазон страниц с помощью команды /print."
    )
    logger.info(f"Пользователь {update.effective_user.id} начал работу с ботом.")

async def choose_pages(update: Update, context):
    """Обработчик команды /print."""
    user_id = update.effective_user.id
    files = context.user_data.get("files", [])
    if not files:
        await update.message.reply_text("Вы еще не загрузили файлы. Пожалуйста, отправьте хотя бы один файл.")
        return

    keyboard = [
        [InlineKeyboardButton(file["name"], callback_data=f"file_{i}")] for i, file in enumerate(files)
    ]
    await update.message.reply_text(
        "Выберите файл для настройки печати:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def file_selected(update: Update, context):
    """Обработчик нажатия кнопки выбора файла."""
    query = update.callback_query
    await query.answer()

    file_index = int(query.data.split("_")[1])
    context.user_data["selected_file"] = file_index

    await query.edit_message_text(
        "Введите диапазон страниц для печати (например, '1-5' или '1,3,5'). "
        "Для печати всех страниц введите 'all'."
    )

async def handle_page_selection(update: Update, context):
    """Обработчик выбора диапазона страниц."""
    page_input = update.message.text.strip()
    selected_file_index = context.user_data.get("selected_file")
    if selected_file_index is None:
        await update.message.reply_text("Сначала выберите файл с помощью команды /print.")
        return

    user_id = update.effective_user.id
    files = context.user_data.get("files", [])
    file_info = files[selected_file_index]

    temp_pdf_path = None  # Переменная для временного файла
    try:
        if page_input.lower() == "all":
            pages = None
        else:
            pages = []
            for part in page_input.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    pages.extend(range(start, end + 1))
                else:
                    pages.append(int(part))

        if file_info["type"] == "docx":
            temp_pdf_path = tempfile.mktemp(suffix=".pdf")
            await asyncio.to_thread(convert_docx_to_pdf_with_word, file_info["path"], temp_pdf_path)
            pdf_path = temp_pdf_path
        else:
            pdf_path = file_info["path"]

        # Проверка диапазона страниц
        try:
            with open(pdf_path, "rb") as f:
                total_pages = len(PyPDF2.PdfReader(f).pages)
                if pages and not validate_page_range(pages, total_pages):
                    logger.warning(f"Некорректный диапазон страниц от {user_id}: {page_input}")
                    await update.message.reply_text(
                        f"Некорректный диапазон страниц: {page_input}. В документе всего {total_pages} страниц."
                    )
                    return
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {pdf_path}: {e}", exc_info=True)
            await update.message.reply_text("Ошибка при обработке файла. Возможно, файл поврежден или недействителен.")
            return

        # Печать файла
        await print_file_directly(pdf_path, pages)

        # Удаление обработанного файла
        try:
            remove_file(file_info["path"])  # Удаление оригинального файла после успешной печати
            del files[selected_file_index]
            remove_user_folder_if_empty(user_id)
        except Exception as cleanup_error:
            logger.error(f"Ошибка при удалении пользовательского файла после печати: {cleanup_error}")

        await update.message.reply_text("Файл успешно распечатан и удален.")

    except ValueError as e:
        logger.error(f"Ошибка диапазона от пользователя {user_id}: {e}")
        await update.message.reply_text(f"Ошибка диапазона страниц: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}", exc_info=True)
        await update.message.reply_text(f"Ошибка: {e}")
    finally:
        # Гарантированное удаление временных файлов
        try:
            if temp_pdf_path:
                remove_file(temp_pdf_path)
        except Exception as cleanup_error:
            logger.error(f"Ошибка при удалении временных файлов: {cleanup_error}")

async def handle_file(update: Update, context):
    """Обработчик загрузки файла."""
    file = update.message.document
    user_id = update.effective_user.id
    if file:
        file_extension = os.path.splitext(file.file_name)[-1].lower()
        if file_extension in [".pdf", ".docx"]:
            file_path = await save_file_for_user(user_id, file, file_extension)
            context.user_data.setdefault("files", []).append({
                "name": file.file_name,
                "path": file_path,
                "type": file_extension.lstrip(".")
            })
            logger.info(f"Файл {file.file_name} сохранен для пользователя {user_id}.")
            await update.message.reply_text(
                f"Файл {file.file_name} успешно загружен. Используйте /print для настройки печати."
            )
        else:
            await update.message.reply_text("Этот формат не поддерживается. Отправьте файл в формате PDF или DOCX.")
    else:
        await update.message.reply_text("Это не файл. Пожалуйста, отправьте документ.")
