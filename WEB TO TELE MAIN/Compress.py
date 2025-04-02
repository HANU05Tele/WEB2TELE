from flask import Flask, request, send_from_directory, render_template, jsonify
import os
import subprocess
import threading
import re
import asyncio
from werkzeug.utils import secure_filename
from telethon import TelegramClient
from telethon.sessions import StringSession  # For in-memory session
from tqdm import tqdm  # Added for smooth progress bar
from queue import Queue  # Added for queue support
import time  # Added for timing

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB Limit

# Folder Configurations
UPLOAD_FOLDER = 'uploads'
COMPRESSED_FOLDER = 'compressed'
OVERLAY_IMAGE = 'overlay.png'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)

# Use thread-safe dictionaries for progress tracking
from threading import Lock
compression_progress = {}
upload_progress = {}
progress_lock = Lock()  # Lock to ensure thread-safe updates
task_queue = Queue()  # Queue for sequential processing

# Telegram API credentials
API_ID = "18243234"  # Replace with your API_ID
API_HASH = "46af394088cc0a920cf3f41f5991eed0"  # Replace with your API_HASH
BOT_TOKEN = "6212871672:AAEA5KiA6yTFwv75TzJCl2db7---dEsAqys"
CHAT_ID = -1001708633832  # Integer chat ID

# Initialize Telethon Client with an in-memory session and single loop
client = TelegramClient(StringSession(), API_ID, API_HASH)
loop = asyncio.new_event_loop()  # Create a new event loop
asyncio.set_event_loop(loop)     # Set it as the current loop

# Start the client once at startup
async def start_client():
    await client.start(bot_token=BOT_TOKEN)
    print("Telegram client started successfully!")

loop.run_until_complete(start_client())

async def send_large_file(filepath, filename, original_filepath, compress_time, download_time):
    global upload_progress
    print(f"🚀 Uploading {filename} to Telegram...")
    try:
        upload_start = time.time()
        with open(filepath, 'rb', buffering=0) as f:  # Unbuffered for speed
            file_size = os.path.getsize(filepath)
            # pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Uploading {filename}", leave=False)  # Commented out to reduce overhead
            def progress_callback(sent, total):
                progress = int((sent / total) * 100)
                with progress_lock:
                    upload_progress[filename] = progress
                # pbar.update(sent - pbar.n)  # Uncomment if you want tqdm back
            uploaded_file = await client.upload_file(
                f,
                file_name=filename,
                progress_callback=progress_callback,
                part_size_kb=512  # Max chunk size for Telegram
            )
        upload_time = time.time() - upload_start

        # Calculate stats
        original_size = os.path.getsize(original_filepath) / (1024 * 1024)  # MB
        compressed_size = file_size / (1024 * 1024)  # MB
        compress_percent = ((original_size - compressed_size) / original_size) * 100

        # Format caption with stats
        caption = (
            f"Compressed File: {filename}\n"
            f"Original Size: {original_size:.2f} MB\n"
            f"Compressed Size: {compressed_size:.2f} MB\n"
            f"Compressed Percentage: {compress_percent:.2f}%\n"
            f"Downloaded in {download_time:.0f}s\n"
            f"Compressed in {compress_time:.0f}s\n"
            f"Uploaded in {upload_time:.0f}s"
        )
        await client.send_file(CHAT_ID, uploaded_file, caption=caption)
        with progress_lock:
            upload_progress[filename] = 100
        # pbar.close()  # Uncomment if using tqdm
        print("✅ File uploaded successfully!")

        # Delete files after successful upload
        os.remove(original_filepath)  # Delete from uploads folder
        os.remove(filepath)  # Delete from compressed folder
        print(f"🗑️ Deleted {original_filepath} and {filepath}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        with progress_lock:
            upload_progress[filename] = -1

def upload_to_telegram(filepath, filename, original_filepath, compress_time, download_time):
    with progress_lock:
        upload_progress[filename] = 0  # Initialize progress
    loop.run_until_complete(send_large_file(filepath, filename, original_filepath, compress_time, download_time))

def track_progress(filename, process, compressed_filepath, compressed_filename, original_filepath, download_time):
    global compression_progress
    with progress_lock:
        compression_progress[filename] = 0
    compress_start = time.time()

    total_duration = None
    pbar = tqdm(total=100, unit='%', desc=f"Compressing {filename}", leave=False)

    for line in iter(process.stderr.readline, ''):
        line = line.strip()
        print(line)

        if "Duration" in line:
            duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
            if duration_match:
                hours, minutes, seconds = map(float, duration_match.groups())
                total_duration = (hours * 3600) + (minutes * 60) + seconds

        elif "time=" in line and total_duration:
            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if time_match:
                h, m, s = map(float, time_match.groups())
                current_time = (h * 3600) + (m * 60) + s
                progress = int((current_time / total_duration) * 100)
                with progress_lock:
                    compression_progress[filename] = min(progress, 100)
                pbar.update(compression_progress[filename] - pbar.n)

    process.wait()
    with progress_lock:
        compression_progress[filename] = 100
    pbar.update(100 - pbar.n)
    pbar.close()  # Close progress bar when done
    compress_time = time.time() - compress_start

    upload_to_telegram(compressed_filepath, compressed_filename, original_filepath, compress_time, download_time)

def process_task(filepath, resolution, crf, codec):
    filename = os.path.basename(filepath)
    download_time = 0  # Since file is already saved

    compressed_filename = f"[HV CARTOONS] {filename} @HV_CARTOONS_TELUGU_2.mkv"
    compressed_filepath = os.path.join(COMPRESSED_FOLDER, compressed_filename)

    with progress_lock:
        compression_progress[filename] = 0
        upload_progress[compressed_filename] = 0  # Reset upload progress

    ffmpeg_command = [
        'ffmpeg', '-y', '-i', filepath, '-i', OVERLAY_IMAGE,
        "-filter_complex", "[1:v]scale=900:-1[wm];[0:v][wm]overlay=main_w-overlay_w-10:main_h-overlay_h-10[out]",
        '-map', '[out]', '-map', '0:a?',
        '-c:v', codec, '-crf', crf, '-preset', 'ultrafast',
        '-c:a', 'aac', '-b:a', '128k',
        '-s', resolution,
        '-metadata', 'title=Visit For More Cartoons [t.me/HV_CARTOONS_TELUGU_2]',
        compressed_filepath
    ]

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    track_progress(filename, process, compressed_filepath, compressed_filename, filepath, download_time)

def process_queue():
    while not task_queue.empty():
        task = task_queue.get()
        process_task(*task)
        task_queue.task_done()

@app.route('/')
def index():
    return render_template('compress.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global compression_progress, upload_progress
    files = request.files.getlist("video")
    resolution = request.form.get("resolution", "1280x720")
    crf = request.form.get("crf", "27")
    codec = request.form.get("codec", "libx264")

    responses = []

    for file in files:
        if file.filename == '':
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        download_start = time.time()
        file.save(filepath)
        download_time = time.time() - download_start  # Not used in queue, but kept for consistency

        compressed_filename = f"[HV CARTOONS] {filename} @HV_CARTOONS_TELUGU_2.mkv"
        task_queue.put((filepath, resolution, crf, codec))
        responses.append({"filename": filename, "compressed_filename": compressed_filename})

    if task_queue.qsize() == len(files):
        threading.Thread(target=process_queue, daemon=True).start()

    return jsonify(responses)

@app.route('/progress/<filename>', methods=['GET'])
def get_progress(filename):
    with progress_lock:  # Ensure thread-safe access
        compression = compression_progress.get(filename, 0)
        upload = upload_progress.get(filename, 0)
        compressed_filename = f"[HV CARTOONS] {filename} @HV_CARTOONS_TELUGU_2.mkv"
        if filename in compression_progress and compressed_filename in upload_progress:
            upload = upload_progress.get(compressed_filename, 0)
    return jsonify({
        "compression": compression,
        "upload": upload
    })

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(COMPRESSED_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)