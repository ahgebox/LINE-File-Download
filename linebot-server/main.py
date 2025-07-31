from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, VideoMessage, TextMessage
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from datetime import datetime

# ■ Config
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.getenv("CHANNEL_SECRET")
CHANNEL_ID           = os.getenv("CHANNEL_ID", "Unknown")

BASE_PATH = '/data'  # ใช้สำหรับ Render
PROCESSED_IDS_FILE = os.path.join(BASE_PATH, 'processed_ids.txt')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)
os.makedirs(BASE_PATH, exist_ok=True)

# ■ ฟังก์ชัน: สร้างโฟลเดอร์ /data/YYYY-MM-DD/category
def ensure_category_folder(category):
    today = datetime.now().strftime('%Y-%m-%d')
    folder = os.path.join(BASE_PATH, today, category)
    os.makedirs(folder, exist_ok=True)
    return folder

# ■ ฟังก์ชัน: บันทึกข้อมูลไบต์
def save_bytes(mid, content, category, ext='jpg'):
    folder = ensure_category_folder(category)
    filename = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{mid}.{ext}"
    file_path = os.path.join(folder, filename)
    with open(file_path, 'wb') as f:
        f.write(content)
    print(f"✅ Saved {category.upper()} to", file_path)

# ■ ฟังก์ชัน: เช็กว่าบันทึก MID ไปแล้วหรือยัง
def is_duplicate(mid):
    if not os.path.exists(PROCESSED_IDS_FILE):
        return False
    with open(PROCESSED_IDS_FILE, 'r') as f:
        return mid in f.read()

def mark_processed(mid):
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(mid + '\n')

# ■ LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ■ เมื่อได้รับข้อความ
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    print("✉️ Received TextMessage:", event.message.text)

# ■ เมื่อได้รับรูปภาพ
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    mid = event.message.id
    if is_duplicate(mid): return
    content = line_bot_api.get_message_content(mid).content
    save_bytes(mid, content, 'images', ext='jpg')
    mark_processed(mid)
    print("🖼️ Received ImageMessage")

# ■ เมื่อได้รับวิดีโอ
@handler.add(MessageEvent, message=VideoMessage)
def handle_video(event):
    mid = event.message.id
    if is_duplicate(mid): return
    content = line_bot_api.get_message_content(mid).content
    save_bytes(mid, content, 'videos', ext='mp4')
    mark_processed(mid)
    print("🎞️ Received VideoMessage")

# ■ สรุปรายวันเวลา 18:00
def daily_summary():
    today = datetime.now().strftime('%Y-%m-%d')
    log_dir = os.path.join(BASE_PATH, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'{today}-log.txt')

    images = os.path.join(BASE_PATH, today, 'images')
    videos = os.path.join(BASE_PATH, today, 'videos')
    image_count = len(os.listdir(images)) if os.path.exists(images) else 0
    video_count = len(os.listdir(videos)) if os.path.exists(videos) else 0

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"📅 {today}\n")
        f.write(f"🖼️ รูปภาพ: {image_count} ไฟล์\n")
        f.write(f"🎞️ วิดีโอ: {video_count} ไฟล์\n")
    print("📊 Daily summary saved to", log_file)

# ■ Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(daily_summary, CronTrigger(hour=18, minute=0))
scheduler.start()

# ■ หน้า root
@app.route("/")
def home():
    return "✅ LINE Bot Server is Running on Render!"

# ■ Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
