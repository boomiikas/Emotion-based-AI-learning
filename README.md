# 🧠 EmotiLearn AI
## Emotion-Adaptive Learning Platform for Grade 6–7

---

## Quick Start (Open in Browser — No Setup Needed)

Just open `frontend/index.html` in any browser!

**Demo Login Credentials:**
| Role    | Username      | Password |
|---------|--------------|----------|
| Student | `alex123`     | `pass123` |
| Student | `priya456`    | `pass123` |
| Teacher | `ms_johnson`  | `pass123` |
| Parent  | `parent_alex` | `pass123` |

---

## Full Stack Setup

### Prerequisites
- Python 3.10+
- MongoDB (local or Atlas)
- Node.js 18+ (optional, for React dev server)

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your MongoDB URL and JWT secret

# Seed the database
python seed.py

# Start the API server
uvicorn main:app --reload --port 8000
```

### 2. (Optional) Train the CNN Model

```bash
# Download FER2013 dataset from Kaggle:
# https://www.kaggle.com/datasets/msambare/fer2013
# Place fer2013.csv in backend/data/

mkdir -p backend/models
python backend/train.py
# Model will be saved to backend/models/emotion_cnn.h5
```

### 3. Open the App

Open `frontend/index.html` directly, OR serve it:

```bash
# Simple Python server
cd frontend
python -m http.server 3000
# Open: http://localhost:3000
```

---

## Project Structure

```
emotilearn/
│
├── frontend/
│   └── index.html              ← Complete single-file app (open directly)
│
├── backend/
│   ├── main.py                 ← FastAPI app + all API routes
│   ├── emotion_engine.py       ← OpenCV + CNN emotion detection
│   ├── adaptive_engine.py      ← Emotion → content adaptation rules
│   ├── seed.py                 ← Database seeder + schema docs
│   ├── requirements.txt
│   └── models/
│       └── emotion_cnn.h5      ← Trained model (after running train.py)
│
└── README.md
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    BROWSER (Student)                     │
│  ┌──────────────┐    ┌───────────────────────────────┐  │
│  │  Webcam Feed │───▶│       Emotion Panel            │  │
│  │  (getUserMedia)   │  CNN Confidence Bars           │  │
│  └──────────────┘    │  Adaptive Actions Display      │  │
│                       └───────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Adaptive Lesson Content                │  │
│  │  Normal ──▶ Confused: simpler explanation          │  │
│  │          ──▶ Bored: quiz auto-launches             │  │
│  │          ──▶ Frustrated: hint + slow pace          │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │ WebSocket / REST API
         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Auth (JWT)   │  │ Emotion      │  │ Adaptive     │  │
│  │ User Mgmt    │  │ Engine       │  │ Engine       │  │
│  └──────────────┘  │ OpenCV +     │  │ Rules-based  │  │
│                     │ CNN (Keras)  │  │ content      │  │
│                     └──────────────┘  └──────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              MongoDB                              │   │
│  │  users │ progress │ sessions │ quiz_results       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Features

### Student
- ✅ Login / Register
- ✅ Subject & topic selection (Math, Science, English)
- ✅ Adaptive learning session with live emotion monitoring
- ✅ Webcam integration (real camera OR simulated)
- ✅ CNN emotion detection → adaptive content
- ✅ 10-question quizzes with instant feedback
- ✅ Progress tracking with charts
- ✅ Badges & achievements
- ✅ Profile editing

### Teacher
- ✅ Student monitoring dashboard
- ✅ Live emotion status per student
- ✅ Class analytics & emotion distribution
- ✅ Performance reports table
- ✅ AI-generated intervention recommendations

### Parent
- ✅ Child progress overview
- ✅ Emotion insights & explanations
- ✅ Quiz result history
- ✅ AI-generated parental guidance
- ✅ Full progress report

---

## Emotion-Adaptive Logic

| Detected Emotion | AI Action                          |
|-----------------|-------------------------------------|
| 😊 **Focused**  | Continue lesson at current pace     |
| 😕 **Confused** | Show simpler explanation + examples |
| 😤 **Frustrated**| Provide hints + slow pace          |
| 😴 **Bored**    | Auto-launch interactive quiz        |
| 😄 **Happy**    | Celebrate + advance to next topic   |

---

## API Endpoints

| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | `/api/auth/register`              | Register user            |
| POST   | `/api/auth/login`                 | Login                    |
| GET    | `/api/auth/me`                    | Get current user         |
| GET    | `/api/subjects`                   | List all subjects        |
| GET    | `/api/topics/{topic_id}/lesson`   | Get lesson content       |
| POST   | `/api/sessions/start`             | Start learning session   |
| POST   | `/api/sessions/{id}/emotion`      | Submit webcam frame      |
| POST   | `/api/sessions/{id}/end`          | End session              |
| POST   | `/api/quiz/submit`                | Submit quiz result       |
| GET    | `/api/progress/{user_id}`         | Get student progress     |
| GET    | `/api/teacher/students`           | Teacher: all students    |
| GET    | `/api/teacher/analytics`          | Teacher: analytics       |
| GET    | `/api/parent/child-progress`      | Parent: child data       |
| WS     | `/ws/emotion/{session_id}`        | Real-time emotion stream |

API docs: http://localhost:8000/docs

---

## Tech Stack

| Layer         | Technology                    |
|---------------|-------------------------------|
| Frontend      | Vanilla HTML/CSS/JS (or React)|
| Backend       | Python FastAPI                |
| Database      | MongoDB (Motor async driver)  |
| Auth          | JWT (PyJWT + bcrypt)          |
| Computer Vision | OpenCV                      |
| ML Model      | TensorFlow/Keras CNN          |
| Dataset       | FER2013 (35,887 images)       |
| Real-time     | WebSockets                    |
