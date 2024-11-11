from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers import start, choose_pages, handle_file, file_selected, handle_page_selection
import logging
import configparser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", mode="a")]
)

# Загрузка конфигурации
config = configparser.ConfigParser()
config.read("config.ini")

def main():
    try:
        TOKEN = config["telegram"]["token"]
    except KeyError:
        logging.error("Токен бота не найден в файле config.ini")
        return

    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("print", choose_pages))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(CallbackQueryHandler(file_selected, pattern=r"^file_\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_page_selection))

    application.run_polling()

if __name__ == "__main__":
    main()
