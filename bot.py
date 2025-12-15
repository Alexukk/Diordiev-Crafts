import os
import telebot
from dotenv import load_dotenv
from flask import url_for

load_dotenv()

ADMIN_CHAT_ID = os.getenv("ADMIN_ID")

bot = telebot.TeleBot(os.getenv('TOKEN'))


def notifier(order):
    # ⚠️ ПЕРЕВІРТЕ: Переконайтеся, що поле 'source' існує в об'єкті 'order'
    # та в моделі Order в базі даних.
    # Якщо 'source' не встановлено, використовуємо значення за замовчуванням.
    source_of_order = getattr(order, 'source', 'Not given (Field missing)')

    items_list = ""
    for item in order.items.all():
        item_title = getattr(item.product, 'title', 'Unknown Product')
        items_list += f"  - {item_title} (x{item.amount})\n"

    message = (
        f"<b>🚨 NEW ORDER №{order.id} 🚨</b>\n\n"
        f"<b>👤 Client:</b> {order.full_name}\n"
        f"<b>📞 Phone:</b> {order.phone}\n"
        f"<b>📧 email:</b> {order.email}\n"
        f"<b>💬 Contact with:</b> {order.contact_way}\n"

        # ДОДАНО: Джерело, звідки клієнт дізнався про нас
        f"<b>💡 Source:</b> {source_of_order}\n"

        f"<b>💸 Total:</b> ${order.total_price:.2f}\n"
        f"<b>🗓️ Date:</b> {order.date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"<b>🛍️ Products:</b>\n{items_list}\n"

        f"🔗 <a href='{url_for('admin_orders', _external=True)}'>Перейти до замовлень</a>"
    )

    try:
        bot.send_message(
            ADMIN_CHAT_ID,
            message,
            parse_mode='HTML'
        )
    except Exception as e:

        print(f"Помилка відправки Telegram: {e}")