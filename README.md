# WEB_TO_TELE Bot

This is a Flask-based web application that allows users to upload and compress videos before sending them to Telegram using the Telethon library.

## 🚀 Features
- Upload videos through a web interface.
- Compress videos using FFmpeg.
- Track compression and upload progress.
- Automatically upload compressed files to Telegram.
- Uses `Telethon` for seamless Telegram integration.

## 🛠️ Installation & Deployment

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/HANU05Tele/WEB_TO_TELE.git
cd WEB_TO_TELE
```

### 2️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Set Up Environment Variables  
Create a `.env` file and add your credentials:
```plaintext
BOT_TOKEN=your_telegram_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
```

### 4️⃣ Run Locally  
```bash
python main.py
```
Then open **http://127.0.0.1:5000/** in your browser.

### 5️⃣ Deploy on Railway
- Push your repository to GitHub.
- Deploy on [Railway](https://railway.app/).
- Add required environment variables in Railway's dashboard.

## 📌 Notes
- Ensure **FFmpeg** is installed (`sudo apt install ffmpeg` or `choco install ffmpeg`).
- Replace `your_telegram_bot_token`, `your_api_id`, and `your_api_hash` with real values.

## 🐜 License
This project is for educational purposes only.

---

Made with ❤️ by **[Your Name]**  

