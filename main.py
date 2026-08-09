import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import os
import threading
from keep_alive import keep_alive


# ================= الإعدادات الأساسية =================
# سيقوم Render بقراءة التوكن من المتغيرات البيئية
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_USERNAME = "@ZenoX_Tools"
ADMIN_ID = 6043858925

# ملاحظة: خادم Flask الخاص بإبقاء البوت حيًا موجود بالفعل في keep_alive.py
# ويُستدعى عبر keep_alive() في الأسفل، لذا لا حاجة لتكراره هنا.

# ================= طبقة خدمة البريد المؤقت (mail.tm أساسي + 1secmail احتياطي) =================
# 1secmail معروفة بعدم الاستقرار (403 / انقطاع متكرر) خصوصًا من IP استضافات مجانية مشتركة.
# لذلك نعتمد mail.tm كخدمة رئيسية أكثر استقرارًا، ونحتفظ بـ1secmail كخطة بديلة تلقائية.

MAILTM_BASE = "https://api.mail.tm"


def _mailtm_create_account():
    """ينشئ حساب mail.tm جديد ويعيد (email, password, token)."""
    domains_resp = requests.get(f"{MAILTM_BASE}/domains", timeout=10)
    domains_resp.raise_for_status()
    domains = domains_resp.json().get("hydra:member", [])
    if not domains:
        raise RuntimeError("لا توجد دومينات متاحة على mail.tm حاليًا")
    domain = domains[0]["domain"]

    login = generate_random_login()
    password = generate_random_login(14)
    address = f"{login}@{domain}"

    create_resp = requests.post(
        f"{MAILTM_BASE}/accounts",
        json={"address": address, "password": password},
        timeout=10,
    )
    create_resp.raise_for_status()

    token_resp = requests.post(
        f"{MAILTM_BASE}/token",
        json={"address": address, "password": password},
        timeout=10,
    )
    token_resp.raise_for_status()
    token = token_resp.json().get("token")

    return {"provider": "mailtm", "address": address, "password": password, "token": token}


def _mailtm_get_messages(token):
    resp = requests.get(
        f"{MAILTM_BASE}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("hydra:member", [])


def _mailtm_get_message_detail(token, message_id):
    resp = requests.get(
        f"{MAILTM_BASE}/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _onesecmail_create_account():
    resp = requests.get(
        "https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1",
        timeout=10,
    )
    resp.raise_for_status()
    address = resp.json()[0]
    login, domain = address.split("@")
    return {"provider": "1secmail", "address": address, "login": login, "domain": domain}


def _onesecmail_get_messages(login, domain):
    resp = requests.get(
        "https://www.1secmail.com/api/v1/",
        params={"action": "getMessages", "login": login, "domain": domain},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _onesecmail_get_message_detail(login, domain, message_id):
    resp = requests.get(
        "https://www.1secmail.com/api/v1/",
        params={"action": "readMessage", "login": login, "domain": domain, "id": message_id},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def create_temp_email():
    """يحاول mail.tm أولاً، وإن فشل يتحول تلقائيًا إلى 1secmail."""
    try:
        return _mailtm_create_account()
    except Exception as e:
        print(f"[mail.tm] فشل الإنشاء، التحويل إلى 1secmail: {e}")
        return _onesecmail_create_account()


def get_inbox(mailbox):
    if mailbox["provider"] == "mailtm":
        return _mailtm_get_messages(mailbox["token"])
    return _onesecmail_get_messages(mailbox["login"], mailbox["domain"])


def get_message_detail(mailbox, message_id):
    if mailbox["provider"] == "mailtm":
        return _mailtm_get_message_detail(mailbox["token"], message_id)
    return _onesecmail_get_message_detail(mailbox["login"], mailbox["domain"], message_id)


def generate_random_login(length: int = 10):
    import random
    import string
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


# ================= قواعد البيانات المؤقتة =================
user_emails = {} # لتخزين البريد النشط لكل مستخدم
user_last_action = {} # للحد من الطلبات (Rate Limiting)

# ================= دوال مساعدة =================

# 1. التحقق من الاشتراك الإجباري
def check_subscription(user_id):
    if user_id == ADMIN_ID: # تجاوز الأدمن من الفحص
        return True
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        # في حال لم يكن البوت مشرفاً في القناة
        return False

# 2. نظام الحد من الطلبات (Rate Limit)
def is_rate_limited(user_id):
    current_time = time.time()
    if user_id in user_last_action:
        # السماح بطلب واحد كل 3 ثوانٍ لحماية السيرفر
        if current_time - user_last_action[user_id] < 3:
            return True
    user_last_action[user_id] = current_time
    return False

# ================= أوامر البوت =================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # فحص الاشتراك
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌟 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ **عذراً عزيزي!**\n\nيجب عليك الاشتراك في قناة البوت الرسمية لتتمكن من استخدامه.\nاشترك ثم اضغط على زر التحقق.", reply_markup=markup, parse_mode="Markdown")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📨 إنشاء بريد عشوائي", callback_data="generate_email"))
    markup.add(InlineKeyboardButton("👨‍💻 المطور", url="tg://user?id=6043858925"))
    
    welcome_text = (
        "👋 **أهلاً بك في بوت البريد المؤقت الذكي!**\n\n"
        "أنا هنا لمساعدتك في إنشاء عناوين بريد إلكتروني وهمية بضغطة زر لحماية بريدك الأساسي من الرسائل المزعجة (Spam).\n\n"
        "👇 اضغط على الزر بالأسفل للبدء."
    )
    bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ================= التعامل مع الأزرار =================

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    # نظام الحماية من الضغط المستمر
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
        try:
            mailbox = create_temp_email()
        except Exception as e:
            print(f"[generate_email] فشل كل مزودي الخدمة: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ تعذر إنشاء البريد حاليًا (كل الخدمات معطلة مؤقتًا)، حاول بعد قليل.",
                show_alert=True,
            )
            return

        user_emails[user_id] = mailbox  # حفظ بيانات البريد الكاملة (بما فيها التوكن إن وجد)
        email = mailbox["address"]

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 فحص صندوق الوارد", callback_data="check_inbox"))
        markup.add(InlineKeyboardButton("🗑️ تغيير البريد", callback_data="generate_email"))

        text = f"✅ **تم إنشاء بريدك بنجاح:**\n\n`{email}`\n\n(اضغط على البريد لنسخه)\nاستخدم هذا البريد للتسجيل، ثم اضغط على فحص صندوق الوارد."

        # تعديل الرسالة السابقة بدلاً من إرسال رسالة جديدة لتجربة مستخدم أفضل
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "check_inbox":
        if user_id not in user_emails:
            bot.answer_callback_query(call.id, "⚠️ لم تقم بإنشاء بريد بعد!", show_alert=True)
            return
            
        mailbox = user_emails[user_id]
        email = mailbox["address"]

        # فحص الرسائل
        try:
            req = get_inbox(mailbox)
        except Exception as e:
            print(f"[check_inbox] getMessages error: {e}")
            bot.answer_callback_query(
                call.id, "❌ تعذر الاتصال بخدمة البريد، حاول لاحقًا.", show_alert=True
            )
            return

        if len(req) == 0:
            bot.answer_callback_query(call.id, "📭 صندوق الوارد فارغ. لم تصل أي رسائل بعد.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "📬 توجد رسائل جديدة!", show_alert=False)
            for msg in req:
                msg_id = msg['id']
                # جلب محتوى الرسالة
                try:
                    read_msg = get_message_detail(mailbox, msg_id)
                except Exception as e:
                    print(f"[check_inbox] readMessage error: {e}")
                    bot.send_message(user_id, f"⚠️ تعذر جلب محتوى رسالة.")
                    continue

                sender = read_msg.get('from', 'غير معروف')
                if isinstance(sender, dict):  # mail.tm يعيد from كـ {address, name}
                    sender = sender.get('address', 'غير معروف')
                subject = read_msg.get('subject', 'بدون عنوان')
                body = read_msg.get('textBody') or read_msg.get('text') or 'لا يوجد نص'
                if isinstance(body, list):  # بعض الحقول قد تأتي كقائمة
                    body = "\n".join(body)
                if len(body) > 3000:
                    body = body[:3000] + "\n... (تم اقتصاص النص)"

                msg_text = f"📨 **رسالة جديدة!**\n\n**من:** `{sender}`\n**الموضوع:** {subject}\n\n**المحتوى:**\n{body}"
                bot.send_message(user_id, msg_text, parse_mode="Markdown")

# ================= تشغيل البوت والخادم =================
if __name__ == "__main__":
    # استدعاء السيرفر الوهمي لاستقبال النقرات
    keep_alive()
    
    print("Bot is running...")
    # تشغيل البوت
    bot.infinity_polling(timeout=10, long_polling_timeout=5)





