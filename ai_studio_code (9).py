import sqlite3
import datetime
import telebot
from telebot import types

# ================= কনফিগারেশন =================
TOKEN = '8963139551:AAEeMGjRrdOvoqeFGb3wWtmJ047yZWj2TTI'
ADMIN_ID = 7743673373  # অ্যাডমিন চ্যাট আইডি
DB_NAME = 'earning_bot_v4.db'
# ===============================================

bot = telebot.TeleBot(TOKEN)
BOT_USERNAME = ""

# --- ডেটাবেজ সেটআপ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ইউজার টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER,
            last_daily TEXT,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    
    # সেটিংস টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # ডায়নামিক চ্যানেল টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            channel_id TEXT,
            url TEXT
        )
    ''')
    
    # উইথড্র টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            details TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    ''')
    
    # ডিফল্ট সেটিংস
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '50.0')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('refer_bonus', '5.0')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('daily_bonus', '1.0')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notice', 'স্বাগতম আমাদের কালারফুল আর্নিং বটে! বন্ধুদের রেফার করে প্রতিদিন আয় করুন।')")
    
    # প্রাথমিক চ্যানেল সেটআপ
    cursor.execute("SELECT COUNT(*) FROM channels")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO channels (name, channel_id, url) VALUES (?, ?, ?)", 
                       ("📢 অফিসিয়াল চ্যানেল", "@test16575", "https://t.me/test16575"))
        
    conn.commit()
    conn.close()

init_db()

# --- ডেটাবেজ হেল্পার ---
def get_setting(key, default_val):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else str(default_val)
    except:
        return str(default_val)

def update_setting(key, val):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(val)))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, channel_id, url FROM channels')
    ch_list = cursor.fetchall()
    conn.close()
    return ch_list

def add_channel_to_db(name, ch_id, url):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO channels (name, channel_id, url) VALUES (?, ?, ?)', (name, ch_id, url))
    conn.commit()
    conn.close()

def delete_channel_from_db(ch_id_num):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE id = ?', (ch_id_num,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, name, username, balance, referrals, referred_by, last_daily, is_banned FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, name, username, balance, referrals, is_banned FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def add_user(user_id, name, username, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, name, username, balance, referrals, referred_by, last_daily, is_banned) VALUES (?, ?, ?, 0.0, 0, ?, NULL, 0)', (user_id, name, username, referrer_id))
    conn.commit()
    conn.close()

def add_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def deduct_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = MAX(0.0, balance - ?) WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_refer_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def set_user_ban_status(user_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

# --- চ্যানেল জয়েন চেক ---
def is_user_joined(user_id):
    channels = get_channels()
    for ch in channels:
        ch_id = ch[2]
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status not in ['creator', 'administrator', 'member', 'restricted']:
                return False
        except Exception:
            return False
    return True

# --- চ্যানেল জয়েন ইনলাইন কিবোর্ড ---
def force_sub_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    channels = get_channels()
    for ch in channels:
        markup.add(types.InlineKeyboardButton(text=f"✨ {ch[1]}", url=ch[3]))
    markup.add(types.InlineKeyboardButton(text="⚡ জয়েন সম্পন্ন হয়েছে ভেরিফাই করুন ⚡", callback_data="check_join"))
    return markup

# ================= 🎨 কালারফুল মেইন মেনু =================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # ১ম সারি: নীল ও সবুজ বাটন
    btn_wallet = types.KeyboardButton("💰 আমার ওয়ালেট", style="primary")
    btn_daily = types.KeyboardButton("🎁 দৈনিক বোনাস", style="success")
    
    # ২য় সারি: সবুজ ও নীল বাটন
    btn_refer = types.KeyboardButton("🔗 রেফারেল লিংক", style="success")
    btn_leaderboard = types.KeyboardButton("🏆 লিডারবোর্ড", style="primary")
    
    # ৩য় সারি: নীল ও সবুজ বাটন
    btn_notice = types.KeyboardButton("📢 নোটিশ বোর্ড", style="primary")
    btn_rules = types.KeyboardButton("📜 নিয়মাবলী", style="success")
    
    # ৪র্থ সারি (ফুল উইডথ): লাল বাটন
    btn_withdraw = types.KeyboardButton("💸 টাকা উত্তোলন (WITHDRAWAL)", style="danger")
    
    markup.row(btn_wallet, btn_daily)
    markup.row(btn_refer, btn_leaderboard)
    markup.row(btn_notice, btn_rules)
    markup.row(btn_withdraw)
    return markup


# ================= 👑 সহজ অ্যাডমিন মেনু =================
def admin_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("📊 বট পরিসংখ্যান", callback_data="admin_stats")
    b2 = types.InlineKeyboardButton("👥 সকল ইউজার লিস্ট", callback_data="admin_all_users")
    b3 = types.InlineKeyboardButton("➕ নতুন চ্যানেল যোগ", callback_data="admin_add_channel")
    b4 = types.InlineKeyboardButton("📋 চ্যানেল লিস্ট ও ডিলিট", callback_data="admin_list_channel")
    b5 = types.InlineKeyboardButton("📢 ব্রডকাস্ট মেসেজ", callback_data="admin_broadcast")
    b6 = types.InlineKeyboardButton("📝 নোটিশ আপডেট", callback_data="admin_update_notice")
    b7 = types.InlineKeyboardButton("⚙️ উইথড্র লিমিট", callback_data="admin_set_withdraw")
    b8 = types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="admin_set_refer")
    b9 = types.InlineKeyboardButton("💎 ডেইলি বোনাস", callback_data="admin_set_daily")
    b10 = types.InlineKeyboardButton("🔍 ইউজার চেক", callback_data="admin_check_user")
    b11 = types.InlineKeyboardButton("➕ ব্যালেন্স যোগ/কাটা", callback_data="admin_balance_manage")
    b12 = types.InlineKeyboardButton("🚫 ব্যান/আনব্যান", callback_data="admin_ban_manage")
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(b5, b6)
    markup.add(b7, b8)
    markup.add(b9, b10)
    markup.add(b11, b12)
    return markup


# ================== 👑 অ্যাডমিন প্যানেল হ্যান্ডলার ==================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ **এক্সেস ডিনাইড!** আপনি অ্যাডমিন নন।", parse_mode="Markdown")
        return

    bot.send_message(
        ADMIN_ID,
        "👑 **সহজ অ্যাডমিন কন্ট্রোল প্যানেল**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "যেকোনো অপশন পরিচালনা করতে নিচে ক্লিক করুন:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback(call):
    if call.message.chat.id != ADMIN_ID:
        return

    # ১. পরিসংখ্যান
    if call.data == "admin_stats":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*), SUM(balance), SUM(referrals) FROM users')
        stats = cursor.fetchone()
        conn.close()

        total_users = stats[0] or 0
        total_balance = stats[1] or 0.0
        total_referrals = stats[2] or 0

        text = (
            f"📊 **বটের রিয়েলটাইম পরিসংখ্যান:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 মোট ইউজার: **{total_users} জন**\n"
            f"💎 মোট ওয়ালেট ব্যালেন্স: **{total_balance:.2f} ৳**\n"
            f"🔗 মোট সফল রেফার: **{total_referrals} টি**\n\n"
            f"⚙️ উইথড্র লিমিট: **{float(get_setting('min_withdraw', 50)):.2f} ৳**\n"
            f"🎁 রেফার বোনাস: **{float(get_setting('refer_bonus', 5)):.2f} ৳**\n"
            f"💎 ডেইলি বোনাস: **{float(get_setting('daily_bonus', 1)):.2f} ৳**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

    # ২. ইউজার লিস্ট
    elif call.data == "admin_all_users":
        users = get_all_users()
        if not users:
            bot.send_message(ADMIN_ID, "❌ কোনো ইউজার নেই।")
            return

        text = "👥 **ইউজার লিস্ট (সর্বশেষ ৩০ জন):**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for u in users[-30:]:
            u_id, name, username, bal, refs, banned = u
            status = "🚫" if banned else "✅"
            u_name = f"@{username}" if username else "নাই"
            text += f"{status} **{name}** (ID: `{u_id}`)\n🔗 {u_name} | 💰 {bal:.2f} ৳ | 👥 {refs} রেফার\n──────────────────────\n"
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

    # ৩. নতুন চ্যানেল যোগ
    elif call.data == "admin_add_channel":
        msg = bot.send_message(
            ADMIN_ID,
            "➕ **নতুন চ্যানেল যুক্ত করার নিয়ম:**\n\n"
            "নিচের মতো করে একটি মেসেজ লিখে পাঠান:\n"
            "`চ্যানেলের নাম | @চ্যানেল_ইউজারনেম | চ্যানেলের লিংক`\n\n"
            "**উদাহরণ:**\n"
            "`📢 আমাদের সাপোর্ট চ্যানেল | @test16575 | https://t.me/test16575`\n\n"
            "⚠️ _মনে রাখবেন: বটকে অবশ্যই ওই চ্যানেলে অ্যাডমিন বানাতে হবে!_",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_add_new_channel)

    # ৪. চ্যানেল লিস্ট ও ডিলিট
    elif call.data == "admin_list_channel":
        channels = get_channels()
        if not channels:
            bot.send_message(ADMIN_ID, "❌ বর্তমানে কোনো চ্যানেল যুক্ত নেই।")
            return
        
        markup = types.InlineKeyboardMarkup()
        for ch in channels:
            markup.add(types.InlineKeyboardButton(f"🗑️ ডিলিট: {ch[1]} ({ch[2]})", callback_data=f"del_ch_{ch[0]}"))
        
        bot.send_message(ADMIN_ID, "📋 **যুক্ত থাকা চ্যানেলসমূহ:**\nযেকোনো চ্যানেল সরাতে নিচের বাটনে ক্লিক করুন:", reply_markup=markup)

    # ৫. ব্রডকাস্ট
    elif call.data == "admin_broadcast":
        msg = bot.send_message(ADMIN_ID, "📢 **যে বার্তাটি সবার কাছে পাঠাতে চান তা লিখে বা ফরোয়ার্ড করে দিন:**")
        bot.register_next_step_handler(msg, process_broadcast)

    # ৬. নোটিশ আপডেট
    elif call.data == "admin_update_notice":
        msg = bot.send_message(ADMIN_ID, "📝 **নতুন নোটিশ লিখে পাঠান:**")
        bot.register_next_step_handler(msg, process_update_notice)

    # ৭. উইথড্র লিমিট
    elif call.data == "admin_set_withdraw":
        msg = bot.send_message(ADMIN_ID, f"⚙️ বর্তমান উইথড্র সীমা: **{get_setting('min_withdraw', 50)} ৳**\nনতুন লিমিট লিখে পাঠান:")
        bot.register_next_step_handler(msg, lambda m: process_change_single_setting(m, 'min_withdraw', "উইথড্র সীমা"))

    # ৮. রেফার বোনাস
    elif call.data == "admin_set_refer":
        msg = bot.send_message(ADMIN_ID, f"🎁 বর্তমান রেফার বোনাস: **{get_setting('refer_bonus', 5)} ৳**\nনতুন রেফার বোনাস লিখে পাঠান:")
        bot.register_next_step_handler(msg, lambda m: process_change_single_setting(m, 'refer_bonus', "রেফার বোনাস"))

    # ৯. ডেইলি বোনাস
    elif call.data == "admin_set_daily":
        msg = bot.send_message(ADMIN_ID, f"💎 বর্তমান ডেইলি বোনাস: **{get_setting('daily_bonus', 1)} ৳**\nনতুন ডেইলি বোনাস লিখে পাঠান:")
        bot.register_next_step_handler(msg, lambda m: process_change_single_setting(m, 'daily_bonus', "ডেইলি বোনাস"))

    # ১০. ইউজার চেক
    elif call.data == "admin_check_user":
        msg = bot.send_message(ADMIN_ID, "🔍 যে ইউজারের তথ্য চেক করবেন তার **চ্যাট আইডি (Chat ID)** পাঠান:")
        bot.register_next_step_handler(msg, process_check_user)

    # ১১. ব্যালেন্স ম্যানেজমেন্ট
    elif call.data == "admin_balance_manage":
        msg = bot.send_message(
            ADMIN_ID,
            "💵 **ব্যালেন্স যোগ বা কর্তন করার নিয়ম:**\n\n"
            "যোগ করতে: `+ চ্যাট_আইডি পরিমাণ` (যেমন: `+ 7743673373 20`)\n"
            "কাটতে: `- চ্যাট_আইডি পরিমাণ` (যেমন: `- 7743673373 10`)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_balance_quick)

    # ১২. ব্যান ম্যানেজমেন্ট
    elif call.data == "admin_ban_manage":
        msg = bot.send_message(
            ADMIN_ID,
            "🚫 **ইউজার ব্যান / আনব্যান করার নিয়ম:**\n\n"
            "ব্যান করতে: `ban চ্যাট_আইডি`\n"
            "আনব্যান করতে: `unban চ্যাট_আইডি`",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_ban_quick)


# --- চ্যানেল ডিলিট হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("del_ch_"))
def handle_channel_deletion(call):
    if call.message.chat.id != ADMIN_ID:
        return
    ch_db_id = int(call.data.split("_")[2])
    delete_channel_from_db(ch_db_id)
    bot.edit_message_text("✅ চ্যানেলটি সফলভাবে মুছে ফেলা হয়েছে!", chat_id=ADMIN_ID, message_id=call.message.message_id)


# --- অ্যাডমিন প্রসেসিং ফাংশনসমূহ ---
def process_add_new_channel(message):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) != 3:
            bot.send_message(ADMIN_ID, "❌ ফরম্যাট ভুল! অনুগ্রহ করে `নাম | @ইউজারনেম | লিংক` আকারে লিখুন।")
            return
        
        name, ch_id, url = parts[0], parts[1], parts[2]
        add_channel_to_db(name, ch_id, url)
        bot.send_message(ADMIN_ID, f"🎉 **চ্যানেল সফলভাবে যুক্ত হয়েছে!**\n\n📢 নাম: {name}\n🆔 আইডি: `{ch_id}`\n🔗 লিংক: {url}", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ ত্রুটি: {e}")

def process_balance_quick(message):
    try:
        parts = message.text.split()
        action, target_id, amount = parts[0], int(parts[1]), float(parts[2])
        if not get_user(target_id):
            bot.send_message(ADMIN_ID, "❌ এই আইডির ইউজার পাওয়া যায়নি!")
            return

        if action == "+":
            add_balance(target_id, amount)
            bot.send_message(ADMIN_ID, f"✅ ইউজার `{target_id}` এর একাউন্টে **+{amount:.2f} ৳** যোগ করা হয়েছে!")
            try:
                bot.send_message(target_id, f"🎁 **অভিনন্দন!** অ্যাডমিন আপনার ওয়ালেটে **+{amount:.2f} ৳** যুক্ত করেছেন।", parse_mode="Markdown")
            except:
                pass
        elif action == "-":
            deduct_balance(target_id, amount)
            bot.send_message(ADMIN_ID, f"✅ ইউজার `{target_id}` এর একাউন্ট থেকে **-{amount:.2f} ৳** কেটে নেওয়া হয়েছে!")
        else:
            bot.send_message(ADMIN_ID, "❌ চিহ্নের স্থানে `+` অথবা `-` দিন!")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ ভুল ফরম্যাট! উদাহরণ: `+ 7743673373 20`")

def process_ban_quick(message):
    try:
        action, target_id = message.text.split()
        target_id = int(target_id)
        if not get_user(target_id):
            bot.send_message(ADMIN_ID, "❌ ইউজার খুঁজে পাওয়া যায়নি!")
            return

        if action.lower() == "ban":
            set_user_ban_status(target_id, 1)
            bot.send_message(ADMIN_ID, f"🚫 ইউজার `{target_id}` কে সফলভাবে **ব্যান** করা হয়েছে!")
        elif action.lower() == "unban":
            set_user_ban_status(target_id, 0)
            bot.send_message(ADMIN_ID, f"🔓 ইউজার `{target_id}` কে সফলভাবে **আনব্যান** করা হয়েছে!")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ ভুল ফরম্যাট! উদাহরণ: `ban 7743673373`")

def process_update_notice(message):
    update_setting('notice', message.text)
    bot.send_message(ADMIN_ID, "✅ **নোটিশ সফলভাবে আপডেট হয়েছে!**", parse_mode="Markdown")

def process_change_single_setting(message, key, title):
    try:
        val = float(message.text)
        update_setting(key, val)
        bot.send_message(ADMIN_ID, f"✅ **সফল!** নতুন {title}: **{val:.2f} ৳**", parse_mode="Markdown")
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ শুধু সংখ্যা লিখুন!")

def process_broadcast(message):
    users = get_all_users()
    sent_count = 0
    bot.send_message(ADMIN_ID, f"🚀 মোট {len(users)} জনের কাছে ব্রডকাস্ট পাঠানো শুরু হয়েছে...")

    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=ADMIN_ID, message_id=message.message_id)
            sent_count += 1
        except:
            pass

    bot.send_message(ADMIN_ID, f"✅ **ব্রডকাস্ট সম্পন্ন!** সফলভাবে পৌঁছেছে `{sent_count}` জনের কাছে।", parse_mode="Markdown")

def process_check_user(message):
    try:
        target_id = int(message.text)
        user = get_user(target_id)
        if user:
            text = (
                f"👤 **ইউজারের তথ্য:**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 চ্যাট আইডি: `{user[0]}`\n"
                f"📛 নাম: **{user[1]}**\n"
                f"🔗 ইউজারনেম: @{user[2] if user[2] else 'নাই'}\n"
                f"💵 ব্যালেন্স: **{user[3]:.2f} ৳**\n"
                f"👥 রেফারেল: **{user[4]} জন**\n"
                f"🚫 ব্যান স্ট্যাটাস: {'ব্যানড' if user[7] else 'একটিভ'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, "❌ এই চ্যাট আইডির কোনো ইউজার পাওয়া যায়নি!")
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ সঠিক আইডি লিখুন!")


# ================== 👤 কালারফুল ইউজার ইন্টারফেস ==================
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.chat.id
        name = message.from_user.first_name or "বন্ধু"
        username = message.from_user.username

        user = get_user(user_id)
        if user and len(user) > 7 and user[7] == 1:
            bot.send_message(user_id, "🚫 **দুঃখিত! আপনার একাউন্টটি ব্যান করা হয়েছে।**", parse_mode="Markdown")
            return

        if not user:
            referrer_id = None
            args = message.text.split()
            if len(args) > 1:
                try:
                    ref = int(args[1])
                    if ref != user_id:
                        referrer_id = ref
                except ValueError:
                    pass
            add_user(user_id, name, username, referrer_id)
        
        if not is_user_joined(user_id):
            bot.send_message(
                user_id,
                f"👋 **হ্যালো {name}!**\n\n"
                f"⚠️ **বটটি ব্যবহার করতে নিচের চ্যানেলগুলোতে জয়েন থাকতে হবে:**\n\n"
                f"নিচের চ্যানেলগুলোতে জয়েন করার পর **'⚡ জয়েন সম্পন্ন হয়েছে ভেরিফাই করুন ⚡'** বাটনে চাপ দিন:",
                reply_markup=force_sub_keyboard(),
                parse_mode="Markdown"
            )
            return

        bot.send_message(
            user_id,
            f"🎉 **স্বাগতম {name}!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"আমাদের কালারফুল আর্নিং বটে আপনাকে স্বাগতম। বন্ধুদের রেফার করে এবং ডেইলি বোনাস নিয়ে আয় করুন আকর্ষণীয় টাকা! 💸\n\n"
            f"👇 নিচের কালারফুল মেনু থেকে অপশন বেছে নিন:",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Start Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.message.chat.id
    name = call.from_user.first_name or "বন্ধু"

    if is_user_joined(user_id):
        try:
            bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        except:
            pass
        
        user = get_user(user_id)
        refer_bonus = float(get_setting('refer_bonus', 5.0))

        if user and len(user) > 5 and user[5]:
            ref_id = user[5]
            add_balance(ref_id, refer_bonus)
            add_refer_count(ref_id)
            try:
                bot.send_message(ref_id, f"🎉 **অভিনন্দন!**\nআপনার রেফারেল থেকে **{name}** সফলভাবে জয়েন করেছে।\n🎁 আপনার ওয়ালেটে **+{refer_bonus:.2f} ৳** যোগ হয়েছে!", parse_mode="Markdown")
            except:
                pass
            conn = sqlite3.connect(DB_NAME)
            conn.cursor().execute('UPDATE users SET referred_by = NULL WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()

        bot.send_message(user_id, "✅ **অভিনন্দন! ভেরিফিকেশন সফল হয়েছে।**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি! সবগুলো চ্যানেলে জয়েন করে আবার চেষ্টা করুন।", show_alert=True)

# --- ইউজার মেনু হ্যান্ডলার ---
@bot.message_handler(func=lambda msg: True)
def menu_handler(message):
    try:
        user_id = message.chat.id
        name = message.from_user.first_name or "বন্ধু"

        user = get_user(user_id)
        if user and len(user) > 7 and user[7] == 1:
            bot.send_message(user_id, "🚫 **আপনার একাউন্টটি ব্যান করা হয়েছে।**", parse_mode="Markdown")
            return

        if not is_user_joined(user_id):
            bot.send_message(user_id, "⚠️ **বট চালু রাখতে আমাদের চ্যানেলে যুক্ত থাকতে হবে!**", reply_markup=force_sub_keyboard(), parse_mode="Markdown")
            return

        if not user:
            add_user(user_id, name, message.from_user.username)
            user = get_user(user_id)

        balance = user[3] if len(user) > 3 else 0.0
        referrals = user[4] if len(user) > 4 else 0
        refer_bonus = float(get_setting('refer_bonus', 5.0))
        min_withdraw = float(get_setting('min_withdraw', 50.0))
        daily_bonus = float(get_setting('daily_bonus', 1.0))

        # ১. ওয়ালেট ব্যালেন্স
        if message.text == "💰 আমার ওয়ালেট":
            text = (
                f"👤 **আপনার ওয়ালেট বিবরণী:**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 চ্যাট আইডি: `{user_id}`\n"
                f"💵 মোট ব্যালেন্স: **{balance:.2f} ৳**\n"
                f"👥 সফল রেফার: **{referrals} জন**\n"
                f"🎯 উইথড্র স্ট্যাটাস: {'✅ উইথড্রযোগ্য' if balance >= min_withdraw else '❌ অপর্যাপ্ত'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            bot.send_message(user_id, text, parse_mode="Markdown")

        # ২. ডেইলি বোনাস
        elif message.text == "🎁 দৈনিক বোনাস":
            now = datetime.datetime.now()
            last_daily_str = user[6] if len(user) > 6 else None
            
            can_claim = False
            if not last_daily_str:
                can_claim = True
            else:
                try:
                    last_daily = datetime.datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
                    if (now - last_daily).total_seconds() >= 86400:
                        can_claim = True
                except:
                    can_claim = True

            if can_claim:
                add_balance(user_id, daily_bonus)
                conn = sqlite3.connect(DB_NAME)
                conn.cursor().execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))
                conn.commit()
                conn.close()
                bot.send_message(user_id, f"🎉 **অভিনন্দন!**\nআপনি আজকের দৈনিক বোনাস **+{daily_bonus:.2f} ৳** পেয়েছেন!", parse_mode="Markdown")
            else:
                time_left = 86400 - (now - last_daily).total_seconds()
                hours = int(time_left // 3600)
                mins = int((time_left % 3600) // 60)
                bot.send_message(user_id, f"⏳ **আপনি ইতিমধ্যে আজকের বোনাস নিয়েছেন!**\nপরবর্তী বোনাস পাবেন: **{hours} ঘণ্টা {mins} মিনিট** পর।", parse_mode="Markdown")

        # ৩. রেফারেল লিংক
        elif message.text == "🔗 রেফারেল লিংক":
            refer_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            text = (
                f"🚀 **আপনার ইউনিক রেফারেল লিংক:**\n"
                f"`{refer_link}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎁 প্রতি সফল রেফারে পাবেন: **{refer_bonus:.2f} ৳**\n"
                f"📢 লিংকটি বন্ধুদের সাথে শেয়ার করুন!"
            )
            bot.send_message(user_id, text, parse_mode="Markdown")

        # ৪. লিডারবোর্ড
        elif message.text == "🏆 লিডারবোর্ড":
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('SELECT name, referrals FROM users WHERE is_banned = 0 ORDER BY referrals DESC LIMIT 10')
            top_users = cursor.fetchall()
            conn.close()

            text = "🏆 **সেরা ১০ জন টপ রেফারার:**\n━━━━━━━━━━━━━━━━━━━━━━\n"
            rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for idx, (t_name, t_refs) in enumerate(top_users):
                emoji = rank_emojis[idx] if idx < len(rank_emojis) else "👤"
                text += f"{emoji} **{t_name}** ➔ **{t_refs}** টি রেফার\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━\n🔥 বন্ধুদের বেশি বেশি রেফার করে শীর্ষে আসুন!"
            bot.send_message(user_id, text, parse_mode="Markdown")

        # ৫. টাকা উত্তোলন (WITHDRAWAL)
        elif message.text == "💸 টাকা উত্তোলন (WITHDRAWAL)":
            if balance < min_withdraw:
                bot.send_message(
                    user_id,
                    f"❌ **অপর্যাপ্ত ব্যালেন্স!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 আপনার ব্যালেন্স: **{balance:.2f} ৳**\n"
                    f"🎯 সর্বনিম্ন উত্তোলন: **{min_withdraw:.2f} ৳**\n\n"
                    f"উইথড্র করতে আরও বন্ধুদের রেফার করুন।",
                    parse_mode="Markdown"
                )
            else:
                msg = bot.send_message(
                    user_id,
                    f"✅ **আপনার ব্যালেন্স:** **{balance:.2f} ৳**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"টাকা তুলতে আপনার **পেমেন্ট মেথড (bKash/Nagad), নাম্বার এবং অ্যামাউন্ট** লিখে পাঠান:\n\n"
                    f"_(উদাহরণ: bKash Personal 017XXXXXXXX {balance:.2f} Tk)_",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, process_withdraw_step, balance)

        # ৬. নোটিশ বোর্ড
        elif message.text == "📢 নোটিশ বোর্ড":
            notice_text = get_setting('notice', 'বর্তমানে কোনো নতুন নোটিশ নেই।')
            text = (
                f"📢 **অফিসিয়াল নোটিশ বোর্ড:**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{notice_text}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            bot.send_message(user_id, text, parse_mode="Markdown")

        # ৭. নিয়মাবলী
        elif message.text == "📜 নিয়মাবলী":
            text = (
                f"📜 **আর্নিং ও পেমেন্টের নিয়মাবলী:**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"১. রেফার লিংক বন্ধুদের শেয়ার করলে পাবেন **{refer_bonus:.2f} ৳**।\n"
                f"২. প্রতিদিন ফ্রি বোনাস নিতে **🎁 দৈনিক বোনাস** বাটনে চাপুন।\n"
                f"৩. ওয়ালেটে **{min_withdraw:.2f} ৳** হলেই উত্তোলন করা যাবে।\n"
                f"৪. কোনো ফেক রেফার করলে সাথে সাথে ব্যান করা হবে।"
            )
            bot.send_message(user_id, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Menu Error: {e}")


# --- উইথড্র প্রসেসিং ও ওয়ান-ক্লিক অ্যাডমিন অ্যাকশন ---
def process_withdraw_step(message, current_balance):
    user_id = message.chat.id
    payment_details = message.text
    name = message.from_user.first_name or "বন্ধু"
    username = message.from_user.username

    # ক্যানসেল চেক
    if payment_details in ["💰 আমার ওয়ালেট", "🎁 দৈনিক বোনাস", "🔗 রেফারেল লিংক", "🏆 লিডারবোর্ড", "💸 টাকা উত্তোলন (WITHDRAWAL)", "📢 নোটিশ বোর্ড", "📜 নিয়মাবলী"]:
        bot.send_message(user_id, "❌ উত্তোলন প্রক্রিয়া বাতিল করা হয়েছে।", reply_markup=main_menu())
        return

    deduct_balance(user_id, current_balance)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO withdrawals (user_id, amount, details) VALUES (?, ?, ?)', (user_id, current_balance, payment_details))
    withdraw_id = cursor.lastrowid
    conn.commit()
    conn.close()

    bot.send_message(
        user_id,
        "🎉 **আপনার উইথড্র রিকোয়েস্টটি সফলভাবে জমা হয়েছে!**\nঅ্যাডমিন যাচাই করে পেমেন্ট পাঠিয়ে দেবে। 💖",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    b_accept = types.InlineKeyboardButton("✅ পেইড (Paid)", callback_data=f"wd_pay_{withdraw_id}_{user_id}_{current_balance}")
    b_reject = types.InlineKeyboardButton("❌ রিজেক্ট (Refund)", callback_data=f"wd_rej_{withdraw_id}_{user_id}_{current_balance}")
    admin_markup.add(b_accept, b_reject)

    admin_alert = (
        f"🚨 **নতুন উইথড্র আবেদন!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 উইথড্র আইডি: `#{withdraw_id}`\n"
        f"👤 নাম: **{name}**\n"
        f"🆔 চ্যাট আইডি: `{user_id}`\n"
        f"🔗 ইউজার: @{username if username else 'নাই'}\n"
        f"💰 উত্তোলনের পরিমাণ: **{current_balance:.2f} ৳**\n"
        f"📝 পেমেন্ট তথ্য:\n`{payment_details}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    try:
        bot.send_message(ADMIN_ID, admin_alert, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception as e:
        print(f"অ্যাডমিন মেসেজ এরর: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_"))
def handle_withdraw_decision(call):
    if call.message.chat.id != ADMIN_ID:
        return

    data = call.data.split("_")
    action = data[1]
    wd_id = data[2]
    u_id = int(data[3])
    amount = float(data[4])

    if action == "pay":
        bot.edit_message_text(
            chat_id=ADMIN_ID,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n✅ **স্ট্যাটাস: পেইড (টাকা পরিশোধিত)**",
            parse_mode="Markdown"
        )
        try:
            bot.send_message(u_id, f"🎉 **অভিনন্দন! আপনার {amount:.2f} ৳ উইথড্র রিকোয়েস্টটি পরিশোধ করা হয়েছে।** ওয়ালেট চেক করুন। 💖", parse_mode="Markdown")
        except:
            pass

    elif action == "rej":
        add_balance(u_id, amount)
        bot.edit_message_text(
            chat_id=ADMIN_ID,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n❌ **স্ট্যাটাস: রিজেক্টেড (ব্যালেন্স ফেরত দেওয়া হয়েছে)**",
            parse_mode="Markdown"
        )
        try:
            bot.send_message(u_id, f"❌ **দুঃখিত! আপনার {amount:.2f} ৳ উইথড্র রিকোয়েস্টটি বাতিল করা হয়েছে এবং টাকা ব্যালেন্সে ফেরত দেওয়া হয়েছে।**", parse_mode="Markdown")
        except:
            pass


# --- বট স্টার্ট ---
if __name__ == "__main__":
    try:
        bot_info = bot.get_me()
        BOT_USERNAME = bot_info.username
        print(f"✨ @{BOT_USERNAME} কালারফুল বট সফলভাবে চালু হয়েছে...")
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Bot Polling Error: {e}")