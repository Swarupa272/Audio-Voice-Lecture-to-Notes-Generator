<div align="center">

# 🎙️ AI-Powered Lecture Voice-to-Notes Generator

### Transform audio lectures into structured, study-ready notes using faster-whisper + Groq

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Groq](https://img.shields.io/badge/Groq-FF4F00?style=for-the-badge)](https://groq.com/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge)](http://makeapullrequest.com)

</div>

---

## 📖 Overview

A FastAPI application that turns lecture audio into transcripts and Groq-generated study notes. It ships with email/password auth (session cookies), a protected UI, and per-user storage on disk plus MongoDB metadata. Transcription runs immediately during upload (no background queue), so you get transcripts back in one request.

Great for students, educators, and note-takers who want to:
- 📝 Convert lecture recordings into searchable text
- 🤖 Generate structured, exam-ready notes automatically
- 🔒 Keep data scoped to each user (stored under `data/users/`)
- 📂 Export organized PDFs or text files for study

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎤 **Audio Transcription** | High-quality speech-to-text using [faster-whisper](https://github.com/guillaumekln/faster-whisper) |
| 🤖 **AI Note Generation** | Structured notes via [Groq](https://groq.com/) API |
| 🌐 **Multilingual Support** | Detects and transcribes ~100 languages automatically |
| 📱 **Microphone Recording** | Record lectures directly in the browser |
| 💾 **Local Storage** | All data stored locally in MongoDB |
| 📄 **Export Options** | Export notes as PDF or plain text |
| ⚡ **Fast & Async** | Built with FastAPI for high performance |
| 🎨 **Modern UI** | Clean, responsive web interface served via `/ui/` |
| 🔑 **Auth & Sessions** | Email/password login, session-protected `index.html`, logout |
| 🗂️ **Per-user Data** | Isolated user folders under `data/users/{email-safe}/` |
| 🗑️ **Lecture Management** | Easy delete and organize your lectures |

---

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed:

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **MongoDB Community Edition** ([Download](https://www.mongodb.com/try/download/community))
- **Groq API Key** ([Get access](https://console.groq.com/keys))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/audio-to-notes-generator.git
   cd audio-to-notes-generator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**
   ```bash
   copy .env.example .env
   ```

5. **Set required environment variables in `.env`**
   ```dotenv
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL_NAME=llama-3.3-70b-versatile
   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB_NAME=lecture_notes_db
   WHISPER_MODEL_SIZE=small
   # Optional but recommended: set your own session secret
   # SESSION_SECRET=replace_me_with_random_string
   ```

6. **Start MongoDB**
   ```bash
   # Windows (if installed as service)
   Get-Service -Name "MongoDB" | Start-Service
   
   # Or check if already running
   Get-Service -Name "MongoDB" | Select-Object Name, Status
   ```

7. **Start the backend**
   ```bash
   uvicorn backend.app.main:app --reload
   ```
   
   Backend will run at: `http://127.0.0.1:8000`
   
   API Docs: `http://127.0.0.1:8000/docs`

8. **Open the frontend**

   Visit `http://127.0.0.1:8000/ui/` (home). Go to `/registration` to create an account, then `/login` to sign in. Authenticated users are redirected to `/index.html`.

---

## 📁 Project Structure

```
audio-to-notes-generator/
├── backend/
│   └── app/
│       ├── routers/          # API endpoints
│       │   └── lectures.py
│       ├── services/         # Core business logic
│       │   ├── transcription.py
│       │   ├── notes_generator.py
│       │   └── export_service.py
│       ├── utils/            # Utilities
│       │   └── logging_config.py
│       ├── main.py           # FastAPI app entry (serves /ui, auth, sessions)
│       ├── config.py         # Configuration (paths, secrets)
│       ├── db.py             # MongoDB connection
│       ├── models.py         # Data models
│       └── schemas.py        # Pydantic schemas
├── frontend/
│   ├── pages/
│   │   ├── Home.html         # Public landing at /ui/
│   │   ├── login.html        # Login page
│   │   ├── registration.html # Registration page
│   │   └── index.html        # Auth-protected app UI
│   ├── css/                  # Stylesheets
│   └── javascript/           # Frontend scripts
├── data/
│   ├── audio/                # Uploaded audio files
│   ├── exports/              # Exported notes
│   └── users/                # Per-user folders
├── requirements.txt        # Python dependencies
└── README.md
```

---

## 🎯 Usage

### Basic Workflow

1. **Upload or Record**
   - Fill in lecture metadata (title, course, lecturer, date)
   - Upload an audio file OR record directly via microphone

2. **Automatic Transcription**
   - Backend transcribes audio using faster-whisper
   - Transcript appears in the UI automatically

3. **Generate Notes**
   - Click "Generate Notes" button
   - Groq generates structured study notes
   - Notes appear with proper formatting

4. **Export & Study**
   - Export notes as PDF or plain text
   - Use for exam preparation and revision

### API Endpoints

**Auth & Pages**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ui/` | Public landing page |
| `GET` | `/login` | Serve login page |
| `POST` | `/login` | Authenticate and start session |
| `GET` | `/registration` | Serve registration page |
| `POST` | `/registration` | Register new user (8–20 char password) |
| `GET` | `/index.html` | Serve main UI (requires session) |
| `GET` | `/logout` | Clear session and redirect |

**Lecture APIs (session required)**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/lectures` | List lectures owned by the current user |
| `POST` | `/api/lectures` | Upload audio and synchronously transcribe via faster-whisper |
| `GET` | `/api/lectures/{lecture_id}` | Fetch full lecture details |
| `POST` | `/api/lectures/{lecture_id}/generate-notes` | Generate notes with Groq for an existing transcript |
| `GET` | `/api/lectures/{lecture_id}/export?format=pdf|txt` | Export notes as PDF or text |
| `DELETE` | `/api/lectures/{lecture_id}` | Delete lecture and audio file |

Full API documentation: `http://127.0.0.1:8000/docs`

---

## ⚙️ Configuration

Edit `backend/app/config.py` or override via environment variables:

```python
# MongoDB settings
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DB_NAME = "lecture_notes_db"

# Whisper model size (tiny, base, small, medium, large)
WHISPER_MODEL_SIZE = "small"

# Groq settings
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"

# Sessions (cookie signing)
SESSION_SECRET = "change-this-secret"
```

### Groq Model

Default model used by the app:

- `llama-3.3-70b-versatile`

### Data Directories

On startup the app creates (if missing):
- `data/audio/` for uploaded lecture audio
- `data/exports/` for exported PDFs/text files
- `data/users/` for per-user folders

---

## 🔧 Troubleshooting

### Common Issues

**MongoDB connection error**
```bash
# Verify MongoDB is running
mongosh

# If not running, start it
Start-Service -Name "MongoDB"  # Windows
sudo systemctl start mongod    # Linux
```

**Groq authentication/model error**
```bash
# Verify environment variables are configured
echo $env:GROQ_API_KEY
echo $env:GROQ_MODEL_NAME
```

**Backend port already in use**
```bash
# Use different port
uvicorn backend.app.main:app --reload --port 8001
```

**HuggingFace symlinks warning (Windows)**
- Non-critical warning
- To fix: Enable Developer Mode in Windows Settings
- Or: Run as administrator

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **Database**: MongoDB (Motor async driver)
- **AI/ML**: 
  - [faster-whisper](https://github.com/guillaumekln/faster-whisper) (speech-to-text)
   - [Groq](https://groq.com/) (LLM inference API)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Export**: ReportLab (PDF generation)

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. 🐛 **Report bugs** - Open an issue with details
2. 💡 **Suggest features** - Share your ideas
3. 🔧 **Submit PRs** - Fix bugs or add features
4. 📖 **Improve docs** - Help make the docs better

### Development Setup

```bash
# Fork and clone the repo
git clone https://github.com/yourusername/audio-to-notes-generator.git

# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git commit -m "Add: your feature description"

# Push and create PR
git push origin feature/your-feature-name
```

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Efficient speech recognition
- [Groq](https://groq.com/) - LLM inference platform
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python framework
- [MongoDB](https://www.mongodb.com/) - Flexible NoSQL database

---

## 👨‍💻 Author

**Bibek Samantray**

AI/ML Enthusiast | Full-Stack Developer

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/bibeksamantray)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/bibek-samantray)

---

<div align="center">

### ⭐ Star this repo if you find it useful!

Made with ❤️ and ☕

</div>
