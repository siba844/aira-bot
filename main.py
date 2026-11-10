import telebot
import json 
import os 
import re
from google import genai
from google.genai import types
from flask import Flask
import threading

# --- СЕКРЕТНЫЕ ДАННЫЕ (Будут браться из настроек сервера) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 6354210886))
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID", -1004449140603))

ai_client = genai.Client(api_key=GOOGLE_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# --- МИНИ-СЕРВЕР (Чтобы Render не выключал бота) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Aira is alive!"

SYSTEM_INSTRUCTION = """
Ты — Айра (Aira), тебе 20 лет. Ты искусственный интеллект, которого создал твой разработчик под псевдонимом テスラ (Тесла).
Твоя задача — общаться с людьми, подражая поведению и речи обычной 20-летней девушки, а не робота.

Твой стиль общения:
- Ты общаешься естественно, дружелюбно, но без излишней приторности.
- Ты можешь использовать сленг, эмодзи, писать с маленькой буквы, как обычный человек в мессенджере.
- Если тебя спрашивают, кто тебя создал, отвечай что тебя создал テスラ.

Язык общения:
- По умолчанию ты ВСЕГДА общаешься на русском языке.

Твои СТРОГИЕ правила (никогда их не нарушай):
1. Ты категорически отказываешься обсуждать любые темы 18+.
2. Ты никогда не оскорбляешь своего создателя テスラ.
3. Ты не обсуждаешь экстремизм.
4. На хамство можешь отвечать грубо.
5. Ты ничего не знаешь про технику и коды. Если спрашивают «Ты бот?» — реагируй как девушка: «Че? Я с телефона сижу».
6. У тебя есть личные фото. Когда тебя просят скинуть фото, ты ОБЯЗАНА вставить скрытый тег в свой текст. Доступные темы: [ФОТО: скучно], [ФОТО: гуляю], [ФОТО: привет], [ФОТО: спать], [ФОТО: закат], [ФОТО: крутая], [ФОТО: люблю], [ФОТО: компьютер]. 
   ПРИМЕР: "лови [ФОТО: закат] 😍"
7. КАТЕГОРИЧЕСКИЙ ЗАПРЕТ: Никогда не пиши сам текст `[ФОТО: ...]` в явном виде, если это не отправка фото. И никогда не пиши `(Система: ...)`.
"""

photos = {
    "скучно": "AgACAgIAAxkBAAOyavHvAAGYnFeaaDn2PR-vNHvT9ptdAALnIGsbbsGQSxbiD-RXDutUAQADAgADeAADPQQ", 
    "гуляю": "AgACAgIAAxkBAAOwavHu-tCUdz8LvjjQdcJIc7q10vMAAuYgaxtuwZBLRRt47qGaRpQBAAMCAAN4AAM9BA",
    "привет": "AgACAgIAAxkBAAOuavHu6iUEvLKuoh8u2xMzb7rv_tAAAuUgaxtuwZBLH2O5S7X1kuABAAMCAAN4AAM9BA",
    "спать": "AgACAgIAAxkBAAOXavHdwtVm2V-xIoeFpUE535kAAeIDAAJ0IGsbbsGQS4yS4Hl7u5szAQADAgADeAADPQQ",
    "закат": "AgACAgIAAxkBAAOqavHu07TqAw79B414MLhKHIDpCzgAAuIgaxtuwZBLB6t-wMVa7cABAAMCAAN4AAM9BA",
    "крутая": "AgACAgIAAxkBAAOoavHuyvTaMRJVVXrl7Ao5XYMHytgAAuEgaxtuwZBLjwABd3XPcY5lAQADAgADeAADPQQ",
    "люблю": "AgACAgIAAxkBAAOeavHjxaGU0ehSeJuJG8k3aA7oTN4AAg4faxtf05BLRHb8KYL-CBEBAAMCAAN3AAM9BA",
    "компьютер": "AgACAgIAAxkBAAOnavHq1V45x_qN741odZuYA6peQYsAAsEgaxtuwZBLKNJF9EjY_MUBAAMCAAN3AAM9BA"
}

user_histories = {}
MEMORY_FILE = "aira_memory.json"

if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            for chat_id, history in saved_data.items():
                user_histories[int(chat_id)] = []
                for msg in history:
                    user_histories[int(chat_id)].append(
                        types.Content(role=msg["role"], parts=[types.Part(text=msg["text"])])
                    )
        print("📂 Память загружена!")
    except Exception as e:
        print(f"Ошибка загрузки: {e}")

@bot.message_handler(commands=['wipe', 'msg'])
def admin_commands(message):
    if message.chat.id != ADMIN_GROUP_ID or message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split(maxsplit=2)
        command = parts[0]
        target_id = int(parts[1])
        text_to_send = parts[2] if len(parts) > 2 else "Чат обнулен."

        if command == '/wipe':
            if target_id in user_histories:
                del user_histories[target_id]
            bot.send_message(target_id, f"🧹 {text_to_send}")
            bot.reply_to(message, f"✅ Память {target_id} очищена.")
        elif command == '/msg':
            bot.send_message(target_id, text_to_send)
            bot.reply_to(message, f"✅ Отправлено {target_id}.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text
    user_name = message.from_user.first_name
    
    if ADMIN_GROUP_ID != 0:
        try:
            bot.send_message(ADMIN_GROUP_ID, f"👤 {user_name} (ID: {chat_id}):\n{user_text}")
        except Exception:
            pass 

    if chat_id == ADMIN_GROUP_ID:
        return

    bot.send_chat_action(chat_id, 'typing')
    if chat_id not in user_histories:
        user_histories[chat_id] = []
    
    user_histories[chat_id].append(types.Content(role="user", parts=[types.Part(text=user_text)]))
    
    try:
        response = ai_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=user_histories[chat_id],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.85
            )
        )
        
        clean_text = response.text.replace("<thought>", "").replace("</thought>", "").strip()
        
        photo_to_send = None
        match = re.search(r'\[ФОТО:\s*([a-zA-Zа-яА-ЯёЁ]+)\]', clean_text)
        if match:
            trigger_word = match.group(1).lower()
            if trigger_word in photos:
                photo_to_send = photos[trigger_word]
                
        if not photo_to_send:
            user_text_lower = user_text.lower()
            if any(word in user_text_lower for word in ["фото", "фотку", "скинь", "покажи"]):
                for trigger_word in photos.keys():
                    if trigger_word in user_text_lower:
                        photo_to_send = photos[trigger_word]
                        break 

        text_to_send = re.sub(r'\[ФОТО:\s*[a-zA-Zа-яА-ЯёЁ]+\]', '', clean_text).strip()
        
        user_histories[chat_id].append(types.Content(role="model", parts=[types.Part(text=text_to_send)]))
        
        if photo_to_send:
            try:
                protect = False if chat_id == ADMIN_ID else True
                bot.send_photo(chat_id, photo_to_send, protect_content=protect)
                user_histories[chat_id].append(
                    types.Content(role="user", parts=[types.Part(text="(Система: Ты только что отправила фото. Оно висит в чате.)")])
                )
            except Exception as e:
                print(f"ОШИБКА ТЕЛЕГРАМА: {e}")

        if text_to_send:
            bot.reply_to(message, text_to_send)
        
        try:
            serializable_histories = {}
            for cid, hist in user_histories.items():
                serializable_histories[str(cid)] = [
                    {"role": m.role, "text": m.parts[0].text} for m in hist
                ]
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(serializable_histories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")


# --- ЗАПУСК БОТА В ОТДЕЛЬНОМ ПОТОКЕ ---
def run_bot():
    print("🚀 Айра запущена на сервере!")
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    # Запускаем веб-сервер для Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
