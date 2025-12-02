import os
import time
import json
import random
import threading
import smtplib
import imaplib
import email
from datetime import datetime, timedelta
from email.mime.text import MIMEText

# Install otomatis jika belum ada modul
try:
    from telebot import TeleBot, types
except ImportError:
    os.system("pip install pyTelegramBotAPI")
    from telebot import TeleBot, types

# ---------------- WARNA & CONSOLE ----------------
R = "\033[91m"  # Red
G = "\033[92m"  # Green
Y = "\033[93m"  # Yellow
B = "\033[94m"  # Blue
C = "\033[96m"  # Cyan
W = "\033[97m"  # White
RESET = "\033[0m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    clear_screen()
    print(f"""{C}
    ██████╗  █████╗ ██████╗  █████╗ 
    ██╔══██╗██╔══██╗██╔══██╗██╔══██╗
    ██████╔╝███████║██████╔╝███████║
    ██╔══██╗██╔══██║██╔══██╗██╔══██║
    ██║  ██║██║  ██║██║  ██║██║  ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
    {W}>> {R}NO-ENV VERSION {W}<<
    {Y}Powered by @R4raaasukamatcha{RESET}
    """)

def log_print(text, type="INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": G, "ERROR": R, "WARN": Y, "INPUT": C}
    col = colors.get(type, W)
    print(f"{W}[{now}] {col}[{type}]{W} {text}")

# ---------------- CONFIG SYSTEM (PENGGANTI .ENV) ----------------
CONFIG_FILE = "config_bot.json"
DATA_FILE = "data_bot.json"
IMAGE_URL = "https://files.catbox.moe/dyw1pr.jpeg"

def load_config():
    """Meminta input user via console jika config belum ada"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    
    # Jika file tidak ada, minta input
    banner()
    print(f"{Y}[!] Konfigurasi belum ditemukan. Silakan isi data:{RESET}\n")
    
    token = input(f"{C}[?] Masukkan Bot Token: {RESET}").strip()
    owner = input(f"{C}[?] Masukkan ID Owner (Angka): {RESET}").strip()
    
    print(f"\n{W}--- SETUP EMAIL SMTP (GMAIL) ---{RESET}")
    print(f"{Y}Info: Gunakan Password Aplikasi (App Password), bukan password login biasa.{RESET}")
    
    email_acc = input(f"{C}[?] Masukkan Email Gmail: {RESET}").strip()
    pass_acc = input(f"{C}[?] Masukkan App Password: {RESET}").strip()
    
    config_data = {
        "bot_token": token,
        "owner_id": owner,
        "accounts": [{"email": email_acc, "pass": pass_acc}]
    }
    
    # Simpan ke file
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
        
    print(f"\n{G}[SUCCESS] Data tersimpan! Memulai bot...{RESET}")
    time.sleep(2)
    return config_data

# Load Config
CFG = load_config()
BOT_TOKEN = CFG['bot_token']
MAIN_OWNER_ID = CFG['owner_id']
ACCOUNTS = CFG['accounts']
SUPPORT_EMAIL = "android@support.whatsapp.com"

bot = TeleBot(BOT_TOKEN)

# ---------------- DATA PERSISTENCE ----------------
DEFAULT_DATA = {
    "premium": {},
    "owners": [],
    "groups": [],
    "config": {"maintenance": False, "cooldown": 120}
}

cooldowns = {}
start_time = time.time()

def load_data():
    if os.path.exists(DATA_FILE):
        try: return json.load(open(DATA_FILE))
        except: return DEFAULT_DATA.copy()
    return DEFAULT_DATA.copy()

def save_data(d):
    with open(DATA_FILE, "w") as f: json.dump(d, f, indent=2)

data = load_data()

# ---------------- HELPERS ----------------
def get_uptime():
    return str(timedelta(seconds=int(time.time() - start_time)))

def is_owner(uid):
    uid = str(uid)
    return uid == str(MAIN_OWNER_ID) or uid in data['owners']

def get_role(uid):
    if is_owner(uid): return "OWNER"
    if str(uid) in data['premium']: return "PREMIUM"
    return "NO ROLE"

def notify_owner_log(text):
    log_print(text, "INFO")
    try: bot.send_message(MAIN_OWNER_ID, f"🔔 <b>LOG:</b> {text}", parse_mode="HTML")
    except: pass

# ---------------- SMTP ENGINE ----------------
def send_email_smtp(acc, nomor):
    log_print(f"Mengirim email ke {nomor} via {acc['email']}...", "WARN")
    body = (f"Helo pihak WhatsApp, perkenalkan nama saya (panns) saya ingin mengajukan banding "
            f"tentang mendaftar nomor telefon, saat registrasi muncul teks (login tidak tersedia) "
            f"mohon untuk memperbaiki masalah tersebut, nomor saya {nomor}")
    msg = MIMEText(body)
    msg["From"] = acc["email"]
    msg["To"] = SUPPORT_EMAIL
    msg["Subject"] = "Banding WhatsApp"
    
    try:
        srv = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
        srv.starttls()
        srv.login(acc["email"], acc["pass"])
        srv.sendmail(acc["email"], SUPPORT_EMAIL, msg.as_string())
        srv.quit()
        log_print(f"Email TERKIRIM ke {nomor}", "INFO")
        return True, None
    except Exception as e:
        log_print(f"Email GAGAL: {e}", "ERROR")
        return False, str(e)

def check_imap(acc, after_ts, chat_id, nomor):
    log_print(f"Memulai Watcher IMAP untuk {nomor}...", "INFO")
    end = time.time() + 180
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com")
        M.login(acc["email"], acc["pass"])
        while time.time() < end:
            M.select("INBOX")
            stat, msgs = M.search(None, 'ALL')
            if stat == "OK":
                for mid in reversed(msgs[0].split()[-3:]):
                    _, d = M.fetch(mid, "(RFC822)")
                    em = email.message_from_bytes(d[0][1])
                    if "whatsapp" in (em.get("From") or "").lower():
                        log_print(f"BALASAN DITEMUKAN untuk {nomor}", "INFO")
                        text = f"🔔 <b>BALASAN DITERIMA!</b>\nNomor: {nomor}\nSubjek: {em.get('Subject')}"
                        bot.send_message(chat_id, text, parse_mode="HTML")
                        return
            time.sleep(10)
    except Exception as e:
        log_print(f"IMAP Error: {e}", "ERROR")

# ---------------- COMMANDS ----------------

@bot.message_handler(commands=['start'])
def cmd_start(m):
    log_print(f"User {m.from_user.id} start bot", "INFO")
    intro = bot.reply_to(m, "⏳ <b>WELCOME TO BOT...</b>", parse_mode="HTML")
    time.sleep(1)
    try: bot.edit_message_text("⚡ <b>POWERED BY @R4raaasukamatcha</b>", m.chat.id, intro.message_id, parse_mode="HTML")
    except: pass
    time.sleep(1)
    try: bot.delete_message(m.chat.id, intro.message_id)
    except: pass

    capt = f"""
𝐑𝐀𝐑𝐀 𝐅𝐈𝐗 𝐑𝐄𝐀𝐃 𝐍𝐔𝐌𝐁𝐄𝐑
<blockquote>RUNTIME: {get_uptime()}</blockquote>
<blockquote>DEVELOPER: @R4raaasukamatcha</blockquote>
<blockquote>PENGGUNA: @{m.from_user.username}
ROLE: {get_role(m.from_user.id)}</blockquote>\n\n<blockquote>®ZIYOFFC</blockquote>
"""
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("BANDING", callback_data="menu_banding"),
        types.InlineKeyboardButton("OWNER MENU", callback_data="menu_owner")
    )
    bot.send_photo(m.chat.id, IMAGE_URL, caption=capt, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    if call.data == "menu_owner":
        if not is_owner(call.from_user.id):
            return bot.answer_callback_query(call.id, "❌ KHUSUS OWNER!", show_alert=True)
        bot.edit_message_caption(
            "𝐑𝐀𝐑𝐀 𝐅𝐈𝐗 𝐑𝐄𝐀𝐃 𝐍𝐔𝐌𝐁𝐄𝐑\n\n/addgroup /addprem /delprem /listprem /addown /delown /setjeda /mintance\n\n<blockquote>®ZIYOFFC</blockquote>",
            call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup
        )
    elif call.data == "menu_banding":
        bot.edit_message_caption(
            "𝐑𝐀𝐑𝐀 𝐅𝐈𝐗 𝐑𝐄𝐀𝐃 𝐍𝐔𝐌𝐁𝐄𝐑\n\n/banding +62xxx /me /info /status\n\n<blockquote>®ZIYOFFC</blockquote>",
            call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup
        )

@bot.message_handler(commands=['banding'])
def cmd_banding(m):
    uid = str(m.from_user.id)
    
    # Validasi
    if data['config']['maintenance'] and not is_owner(uid):
        return bot.reply_to(m, "<blockquote>⛔MAINTANCE⛔</blockquote>\n\n<blockquote>MAINTENANCE SERVER</b>\nHubungi @R4raaasukamatchaa</blockquote>\n\n<blockquote>©ZIYOFFC</blockquote>", parse_mode="HTML")

    
    if not is_owner(uid):
        if m.chat.id not in data['groups']: return bot.reply_to(m, "❌ Grup Private.")
        last = cooldowns.get(uid, 0)
        jeda = data['config']['cooldown']
        if time.time() - last < jeda: return bot.reply_to(m, f"⏳ Jeda {int(jeda - (time.time() - last))}s")

    try: nomor = m.text.split()[1]
    except: return bot.reply_to(m, "/banding +62xxx")

    cooldowns[uid] = time.time()
    acc = random.choice(ACCOUNTS)
    
    log_print(f"EXEC: {m.from_user.username} -> {nomor}", "WARN")
    msg = bot.reply_to(m, "🔄 <b>Sending...</b>", parse_mode="HTML")
    ok, err = send_email_smtp(acc, nomor)
    
    if ok:
        detil = f"✅ <b>BANDING DIKIRIM!</b>\nNomor: {nomor}\nSMTP: {acc['email']}"
        bot.edit_message_text(detil, m.chat.id, msg.message_id, parse_mode="HTML")
        threading.Thread(target=check_imap, args=(acc, time.time(), m.chat.id, nomor)).start()
        notify_owner_log(f"Banding OK: {nomor}")
    else:
        bot.edit_message_text(f"❌ Gagal: {err}", m.chat.id, msg.message_id)

@bot.message_handler(commands=['addgroup'])
def f_addg(m):
    if is_owner(m.from_user.id):
        data['groups'].append(m.chat.id)
        save_data(data)
        bot.reply_to(m, "✅ OK")

# ---------------- RUN ----------------
if __name__ == "__main__":
    banner()
    print(f"{C}[SYSTEM] Bot Token & Config Loaded.{RESET}")
    print(f"{C}[SYSTEM] Owner ID: {MAIN_OWNER_ID}{RESET}")
    print(f"{C}[SYSTEM] Bot sedang berjalan...{RESET}\n")
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        log_print(f"Error: {e}", "ERROR")
        