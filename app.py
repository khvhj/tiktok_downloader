
from flask import Flask, request, render_template, send_file, jsonify
import yt_dlp
import os
import uuid
import threading
import time
import shutil
import subprocess

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
TOKENS_FILE = os.path.join(BASE_DIR, 'tokens_map.txt')
MAX_AGE_SECONDS = 30 * 60

# تنظيف المجلد عند التشغيل
if os.path.exists(DOWNLOAD_DIR):
    shutil.rmtree(DOWNLOAD_DIR)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

if not os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, "w") as f:
        pass

def save_token(token, filename):
    with open(TOKENS_FILE, "a") as f:
        f.write(f"{token},{filename}\n")

def get_filename_from_token(token):
    if not os.path.exists(TOKENS_FILE):
        return None
    with open(TOKENS_FILE, "r") as f:
        for line in f:
            saved_token, saved_file = line.strip().split(",", 1)
            if saved_token == token:
                return saved_file
    return None

def cleanup_old_files():
    while True:
        time.sleep(300)
        now = time.time()
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, "r") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                token, filepath = line.strip().split(",", 1)
                if os.path.exists(filepath):
                    file_age = now - os.path.getmtime(filepath)
                    if file_age > MAX_AGE_SECONDS:
                        try:
                            os.remove(filepath)
                        except:
                            pass
                    else:
                        new_lines.append(line)
            with open(TOKENS_FILE, "w") as f:
                f.writelines(new_lines)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route("/", methods=["GET", "POST"])
def index():
    token = None
    error = None

    if request.method == "POST":
        url = request.form.get("url")
        format_choice = request.form.get("format", "mp4")

        if url:
            try:
                token = str(uuid.uuid4())
                ext = "mp3" if format_choice == "mp3" else "mp4"
                filename = os.path.join(DOWNLOAD_DIR, f"{token}.{ext}")
                cookie_path = os.path.join(BASE_DIR, 'all_cookies.txt')

                ydl_opts = {
                    'quiet': True,
                    'outtmpl': filename,
                    'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
                    'noplaylist': True,
                    'no_cache_dir': True,
                }

                if format_choice == "mp3":
                    ydl_opts.update({
                        'format': 'bestaudio',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '128',
                        }]
                    })
                else:
                    ydl_opts.update({
                        'format': 'bv*+ba/best',
                        'merge_output_format': 'mp4'
                    })

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                save_token(token, filename)
            except Exception as e:
                print("Download Error:", e)
                error = "⚠️ حدث خطأ أثناء التحميل"
        else:
            error = "يرجى إدخال رابط صحيح."

    return render_template("index.html", token=token, error=error)

@app.route("/download/<token>")
def download_video(token):
    filepath = get_filename_from_token(token)
    if not filepath or not os.path.exists(filepath):
        return "❌ الرابط غير صالح أو انتهت صلاحيته."
    ext = os.path.splitext(filepath)[1].lower()
    mimetype = 'audio/mpeg' if ext == '.mp3' else 'video/mp4'
    return send_file(filepath, as_attachment=True, mimetype=mimetype)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
