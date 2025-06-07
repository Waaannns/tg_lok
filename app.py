import re, imaplib, email as email_lib, threading, chardet, logging
from bs4 import BeautifulSoup as bs
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes
from loguru import logger as log

log.remove()
log.add(
    sink=lambda msg: print(msg, end=""),  
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
    colorize=True  
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = "8186587728:AAFZF6tGcbqg4rWbYJHJZ8IYV0Bs5tymAn0"
ADMIN_ID = "939096118"

IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "botml9799@gmail.com"
EMAIL_PASSWORD = "bnxl wsyu qhli groa"

class Imap:
    def __init__(self):
        self.wi = EMAIL_ACCOUNT
        self.no = EMAIL_PASSWORD
        self.imap = IMAP_SERVER
        self.mail = None
        self.lock = threading.Lock()

    def connect(self):
        self.mail = imaplib.IMAP4_SSL(self.imap)

    def login(self):
        try:
            self.connect()
            self.mail.login(self.wi, self.no)
        except imaplib.IMAP4.error as e:
            log.error(f"Login Failed: {e}")
            return False
        return True
    
    def logout(self):
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass
            self.mail = None

    def get_latest_url(self, email):
        with self.lock:
            if not self.login():
                return None

            try:
                self.mail.select('inbox')
                result, data = self.mail.search(None, f'(UNSEEN TO "{email}")')
                if result != 'OK':
                    log.error("Gagal mencari email")
                    return "Gagal mencari email"

                mail_ids = data[0].split()
                if not mail_ids:
                    log.error("Tidak ada email di kotak masuk")
                    return "Tidak ada email di kotak masuk"

                email_terbaru_id = mail_ids[-1]
                result, data = self.mail.fetch(email_terbaru_id, '(RFC822)')
                if result != 'OK':
                    log.error("Gagal mengambil email terbaru")
                    return "Gagal mengambil email terbaru"

                email_mentah = data[0][1]
                msg = email_lib.message_from_bytes(email_mentah)

                decoded_text = None
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/html':
                            isi_email = part.get_payload(decode=True)
                            encoding = chardet.detect(isi_email)['encoding']
                            decoded_text = isi_email.decode(encoding)
                            break
                else:
                    isi_email = msg.get_payload(decode=True).decode('utf-8')
                    decoded_text = isi_email

                # Tandai email sebagai telah dibaca
                self.mail.store(email_terbaru_id, '+FLAGS', '\\Seen')
                self.mail.expunge()

                return decoded_text
            finally:
                self.logout()

# Inisialisasi IMAP Handler
imap_handler = Imap()

# Fungsi untuk mengirim log aktivitas ke admin
async def send_log_to_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    await context.bot.send_message(chat_id=ADMIN_ID, text=message)

# Fungsi untuk memulai bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_message = f"🔹 {user.full_name} (ID: {user.id}) memulai bot."
    log.info(log_message)
    
    # Kirim log ke admin
    await send_log_to_admin(context, log_message)

    await update.message.reply_text("Halo! Kirimkan alamat email yang ingin kamu cari.")

# Menerima input email dari pengguna
async def fetch_email_by_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    recipient_email = update.message.text.strip()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        await update.message.reply_text("⚠️ Harap masukkan alamat email yang valid.")
        return

    log_message = f"📧 {user.full_name} (ID: {user.id}) mencari email: {recipient_email}"
    log.info(log_message)
    
    # Kirim log ke admin
    await send_log_to_admin(context, log_message)

    await update.message.reply_text(f"🔍 Mencari email untuk `{recipient_email}`...")

    email_content = imap_handler.get_latest_url(recipient_email)
    
    if not email_content:
        await update.message.reply_text("⚠️ Email tidak ditemukan atau terjadi kesalahan.")
        return

    # Bersihkan HTML
    soup = bs(email_content, "html.parser")
    clean_text = soup.get_text(separator=" ").strip()

    # Pastikan pesan tidak melebihi batas Telegram (4096 karakter)
    if len(clean_text) > 4096:
        clean_text = clean_text[:4090] + "..."

    await update.message.reply_text(f"Email : {recipient_email}\n\nIsi Pesan : \n{clean_text}")

# Menjalankan bot dengan asyncio
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_email_by_recipient))
    application.run_polling()

if __name__ == "__main__":
    main()
