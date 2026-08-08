import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import os
from keep_alive import keep_alive

# ================= الإعدادات الأساسية =================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_USERNAME = "@ZenoX_Tools"
ADMIN_ID = 6043858925

# ================= حيلة تخطي حظر موقع الإيميلات =================
# هذا سيجعل السيرفر يبدو كمتصفح حقيقي لتجنب الحظر
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# ================= قواعد البيانات المؤقتة =================
user_emails = {} 
user_last_action = {} 

# ================= دوال مساعدة =================
def check_subscription(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

def is_rate_limited(user_id):
    current_time = time.time()
    if user_id in user_last_action:
        if current_time - user_last_action[user_id] < 3:
            return True
    user_last_action[user_id] = current_time
    return False

# ================= أوامر البوت =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌟 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ **عذراً عزيزي!**\n\nيجب عليك الاشتراك في قناة البوت الرسمية لتتمكن من استخدامه.\nاشترك ثم اضغط على زر التحقق.", reply_markup=markup, parse_mode="Markdown")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📨 إنشاء بريد عشوائي", callback_data="generate_email"))
    markup.add(InlineKeyboardButton("👨‍💻 المطور", url=f"tg://user?id={ADMIN_ID}"))
    
    welcome_text = (
        "👋 **أهلاً بك في بوت البريد المؤقت الذكي!**\n\n"
        "أنا هنا لمساعدتك في إنشاء عناوين بريد إلكتروني وهمية بضغطة زر لحماية بريدك الأساسي من الرسائل المزعجة (Spam).\n\n"
        "👇 اضغط على الزر بالأسفل للبدء."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ================= التعامل مع الأزرار الشفافة =================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    if is_rate_limited(user_id):
        bot.answer_callback_query(call.id, "⏳ يرجى الانتظار قليلاً بين الطلبات!", show_alert=True)
        return

    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح! يمكنك الآن استخدام البوت.", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)

    elif call.data == "generate_email":
        bot.answer_callback_query(call.id, "⏳ جاري إنشاء بريد جديد...")
        
        try:
            req = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1", headers=HEADERS, timeout=15).json()
            email = req[0]
            user_emails[user_id] = email 
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 فحص صندوق الوارد", callback_data="check_inbox"))
            markup.add(InlineKeyboardButton("🗑️ تغيير البريد", callback_data="generate_email"))
            
            text = f"✅ **تم إنشاء بريدك بنجاح:**\n\n`{email}`\n\n(اضغط على البريد لنسخه)\nاستخدم هذا البريد للتسجيل، ثم اضغط على فحص صندوق الوارد."
            
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")
        
        except requests.exceptions.RequestException:
            bot.send_message(call.message.chat.id, "⚠️ **عذراً!** يبدو أن موقع الإيميلات يواجه ضغطاً حالياً. يرجى الانتظار والمحاولة لاحقاً.")

    elif call.data == "check_inbox":
        if user_id not in user_emails:
            bot.answer_callback_query(call.id, "⚠️ لم تقم بإنشاء بريد بعد!", show_alert=True)
            return
            
        bot.answer_callback_query(call.id, "⏳ جاري فحص الرسائل...")
        email = user_emails[user_id]
        login, domain = email.split("@")
        
        try:
            req = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}", headers=HEADERS, timeout=15).json()
            
            if len(req) == 0:
                bot.send_message(call.message.chat.id, "📭 صندوق الوارد فارغ. لم تصل أي رسائل بعد.")
            else:
                for msg in req:
                    msg_id = msg['id']
                    read_msg = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}", headers=HEADERS, timeout=15).json()
                    
                    sender = read_msg.get('from', 'غير معروف')
                    subject = read_msg.get('subject', 'بدون عنوان')
                    body = read_msg.get('textBody', 'لا يوجد نص')
                    
                    msg_text = f"📨 **رسالة جديدة!**\n\n**من:** `{sender}`\n**الموضوع:** {subject}\n\n**المحتوى:**\n{body}"
                    bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")
        
        except requests.exceptions.RequestException:
            bot.send_message(call.message.chat.id, "⚠️ **حدث خطأ!** فشل الاتصال بخادم الرسائل.")

# ================= تشغيل البوت والخادم =================
if __name__ == "__main__":
    keep_alive()
    print("Bot is running with Transparent Inline Keyboards and API Bypass...")
    bot.infinity_polling(timeout=20, long_polling_timeout=5)




