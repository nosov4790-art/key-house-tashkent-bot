
import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🤝 Предложение сотрудничества"],
        ["🔑 Сдать / Снять"],
        ["🏠 Купить / Продать"],
    ],
    resize_keyboard=True,
)

PROPERTY_MENU = ReplyKeyboardMarkup(
    [["🏠 Дом", "🏢 Квартира"], ["⬅️ Назад"]],
    resize_keyboard=True,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте! Добро пожаловать в KEY HOUSE | Tashkent 🏡\n"
        "Недвижимость, которую хочется назвать домом.\n\n"
        "Выберите, чем мы можем помочь:",
        reply_markup=MAIN_MENU,
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    if text == "⬅️ Назад":
        context.user_data.clear()
        await update.message.reply_text("Главное меню:", reply_markup=MAIN_MENU)
        return

    if text in ("🔑 Сдать / Снять", "🏠 Купить / Продать"):
        context.user_data.clear()
        context.user_data["request_type"] = text
        await update.message.reply_text(
            "Что вас интересует?",
            reply_markup=PROPERTY_MENU,
        )
        return

    if text == "🤝 Предложение сотрудничества":
        context.user_data.clear()
        context.user_data["request_type"] = text
        context.user_data["stage"] = "details"
        await update.message.reply_text(
            "Расскажите о предложении сотрудничества. "
            "Укажите имя и удобный способ связи."
        )
        return

    if text in ("🏠 Дом", "🏢 Квартира"):
        context.user_data["property_type"] = text
        context.user_data["stage"] = "district"
        await update.message.reply_text(
            "Какой район Ташкента вас интересует? Напишите район или «Любой»."
        )
        return

    stage = context.user_data.get("stage")

    if stage == "district":
        context.user_data["district"] = text
        context.user_data["stage"] = "budget"
        await update.message.reply_text(
            "Укажите бюджет и валюту. Например: до 70000 USD "
            "или 500 USD в месяц."
        )
        return

    if stage == "budget":
        context.user_data["budget"] = text
        context.user_data["stage"] = "details"
        await update.message.reply_text(
            "Напишите ваше имя и комментарий. Номер телефона можно "
            "отправить следующим сообщением или пропустить."
        )
        return

    if stage == "details":
        context.user_data["details"] = text
        context.user_data["stage"] = "phone"
        await update.message.reply_text(
            "Поделитесь телефоном кнопкой ниже или нажмите «Пропустить»."
            ,
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton("📱 Поделиться телефоном", request_contact=True)],
                    ["Пропустить"],
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )
        return

    if stage == "phone":
        if text == "Пропустить":
            context.user_data["phone"] = "Не предоставлен"
            await finish_request(update, context)
        else:
            context.user_data["details"] = (
                context.user_data.get("details", "") + "\nДополнительно: " + text
            )
            await update.message.reply_text(
                "Если хотите, поделитесь телефоном кнопкой или нажмите «Пропустить»."
            )
        return

    await update.message.reply_text("Выберите действие в меню:", reply_markup=MAIN_MENU)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    context.user_data["phone"] = contact.phone_number
    await finish_request(update, context)

async def finish_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data
    username = f"@{user.username}" if user.username else "не указан"

    message = (
        "🔔 НОВАЯ ЗАЯВКА — KEY HOUSE\n\n"
        f"Тип обращения: {data.get('request_type', 'не указан')}\n"
        f"Недвижимость: {data.get('property_type', 'не указана')}\n"
        f"Район: {data.get('district', 'не указан')}\n"
        f"Бюджет: {data.get('budget', 'не указан')}\n"
        f"Имя и комментарий: {data.get('details', 'не указаны')}\n"
        f"Телефон: {data.get('phone', 'не предоставлен')}\n"
        f"Telegram: {username}\n"
        f"Telegram ID: {user.id}"
    )

    if GROUP_ID:
        try:
            await context.bot.send_message(chat_id=int(GROUP_ID), text=message)
        except Exception:
            logging.exception("Не удалось отправить заявку в группу")
            await update.message.reply_text(
                "Возникла ошибка при отправке заявки. Попробуйте позже."
            )
            return
    else:
        logging.warning("GROUP_ID не настроен. Заявка пока не отправлена в группу.")

    await update.message.reply_text(
        "Спасибо за обращение! 🏡 Специалист KEY HOUSE свяжется с вами.",
        reply_markup=MAIN_MENU,
    )
    context.user_data.clear()

def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в настройках хостинга.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
