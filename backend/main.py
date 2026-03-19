"""
EmotiLearn AI — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
import jwt, bcrypt, json, asyncio, base64, cv2, numpy as np
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from emotion_engine import EmotionDetector
from adaptive_engine import AdaptiveEngine
import os

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="EmotiLearn AI", version="1.0.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

# ─── Database ─────────────────────────────────────────────────────────────────
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.emotilearn

# ─── Auth ─────────────────────────────────────────────────────────────────────
SECRET = os.getenv("JWT_SECRET", "emotilearn-secret-2026")
security = HTTPBearer()
emotion_detector = EmotionDetector()
adaptive_engine = AdaptiveEngine()

# ─── Models ───────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    role: str  # student | teacher | parent
    grade: Optional[str] = None
    parentId: Optional[str] = None
    childId: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class SessionStart(BaseModel):
    subject: str
    topic: str

class EmotionFrame(BaseModel):
    frame_b64: str  # base64 encoded JPEG frame

class QuizResult(BaseModel):
    topic: str
    subject: str
    score: int
    total: int
    pct: float
    emotions: List[str]

class ProgressUpdate(BaseModel):
    subject: str
    minutes: int
    emotions: List[str]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def check_pw(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def make_token(user_id: str, role: str) -> str:
    payload = {"sub": user_id, "role": role,
               "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET, algorithm="HS256")

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
        user = await db.users.find_one({"_id": payload["sub"]})
        if not user: raise HTTPException(401, "User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")

# ─── Auth Routes ──────────────────────────────────────────────────────────────
@app.post("/api/auth/register")
async def register(data: UserCreate):
    existing = await db.users.find_one({"username": data.username})
    if existing:
        raise HTTPException(400, "Username already taken")
    user_id = f"u_{data.username}_{int(datetime.utcnow().timestamp())}"
    user = {
        "_id": user_id, "username": data.username,
        "password": hash_pw(data.password), "name": data.name,
        "role": data.role, "grade": data.grade,
        "parentId": data.parentId, "childId": data.childId,
        "createdAt": datetime.utcnow().isoformat()
    }
    await db.users.insert_one(user)
    # Create initial progress doc for students
    if data.role == "student":
        await db.progress.insert_one({
            "_id": user_id, "userId": user_id,
            "math": 0, "science": 0, "english": 0,
            "sessions": 0, "totalMinutes": 0,
            "quizzesDone": 0, "avgScore": 0,
            "badges": [], "emotionLog": []
        })
    token = make_token(user_id, data.role)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

@app.post("/api/auth/login")
async def login(data: LoginRequest):
    user = await db.users.find_one({"username": data.username})
    if not user or not check_pw(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(user["_id"], user["role"])
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

@app.get("/api/auth/me")
async def me(user=Depends(get_current_user)):
    return {k: v for k, v in user.items() if k != "password"}

# ─── User Routes ──────────────────────────────────────────────────────────────
@app.get("/api/users/{user_id}")
async def get_user(user_id: str, current=Depends(get_current_user)):
    user = await db.users.find_one({"_id": user_id})
    if not user: raise HTTPException(404, "User not found")
    return {k: v for k, v in user.items() if k != "password"}

@app.put("/api/users/{user_id}")
async def update_user(user_id: str, data: dict, current=Depends(get_current_user)):
    if current["_id"] != user_id:
        raise HTTPException(403, "Forbidden")
    if "password" in data:
        data["password"] = hash_pw(data["password"])
    await db.users.update_one({"_id": user_id}, {"$set": data})
    return {"message": "Updated"}

# ─── Subjects / Curriculum ────────────────────────────────────────────────────
@app.get("/api/subjects")
async def get_subjects(current=Depends(get_current_user)):
    subjects = await db.subjects.find().to_list(100)
    if not subjects:
        # Return default curriculum
        return CURRICULUM
    return subjects

@app.get("/api/subjects/{subject_id}/topics")
async def get_topics(subject_id: str, current=Depends(get_current_user)):
    subject = next((s for s in CURRICULUM if s["id"] == subject_id), None)
    if not subject: raise HTTPException(404, "Subject not found")
    return subject["topics"]

@app.get("/api/topics/{topic_id}/lesson")
async def get_lesson(topic_id: str, current=Depends(get_current_user)):
    lesson = await db.lessons.find_one({"topicId": topic_id})
    if not lesson: raise HTTPException(404, "Lesson not found")
    return lesson

# ─── Sessions ─────────────────────────────────────────────────────────────────
@app.post("/api/sessions/start")
async def start_session(data: SessionStart, current=Depends(get_current_user)):
    session_id = f"sess_{current['_id']}_{int(datetime.utcnow().timestamp())}"
    session = {
        "_id": session_id, "userId": current["_id"],
        "subject": data.subject, "topic": data.topic,
        "startTime": datetime.utcnow().isoformat(),
        "endTime": None, "emotions": [], "adaptations": [],
        "status": "active"
    }
    await db.sessions.insert_one(session)
    return {"sessionId": session_id, "message": "Session started"}

@app.post("/api/sessions/{session_id}/emotion")
async def log_emotion(session_id: str, data: EmotionFrame, current=Depends(get_current_user)):
    """Receive a webcam frame, detect emotion, return adaptation."""
    # Decode frame
    frame_bytes = base64.b64decode(data.frame_b64)
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # Detect emotion
    result = emotion_detector.detect(frame)
    emotion = result.get("emotion", "focused")
    confidence = result.get("confidence", 0.0)
    # Get adaptive action
    adaptation = adaptive_engine.get_adaptation(emotion, data.topic if hasattr(data, 'topic') else '')
    # Save to session
    await db.sessions.update_one(
        {"_id": session_id},
        {"$push": {
            "emotions": {"emotion": emotion, "confidence": confidence, "timestamp": datetime.utcnow().isoformat()},
            "adaptations": adaptation
        }}
    )
    return {"emotion": emotion, "confidence": confidence, "adaptation": adaptation, "emotionProbs": result.get("probs", {})}

@app.post("/api/sessions/{session_id}/end")
async def end_session(session_id: str, current=Depends(get_current_user)):
    session = await db.sessions.find_one({"_id": session_id})
    if not session: raise HTTPException(404)
    end_time = datetime.utcnow().isoformat()
    start = datetime.fromisoformat(session["startTime"])
    end = datetime.utcnow()
    duration_minutes = int((end - start).total_seconds() / 60)
    await db.sessions.update_one(
        {"_id": session_id},
        {"$set": {"endTime": end_time, "status": "completed", "durationMinutes": duration_minutes}}
    )
    # Update progress
    emotion_log = [e["emotion"] for e in session.get("emotions", [])]
    await db.progress.update_one(
        {"_id": current["_id"]},
        {"$inc": {"sessions": 1, "totalMinutes": duration_minutes},
         "$push": {"emotionLog": {"$each": emotion_log}}}
    )
    return {"message": "Session ended", "durationMinutes": duration_minutes, "totalEmotions": len(emotion_log)}

@app.get("/api/sessions/history")
async def session_history(current=Depends(get_current_user)):
    sessions = await db.sessions.find({"userId": current["_id"]}).sort("startTime", -1).limit(20).to_list(20)
    return sessions

# ─── Progress ─────────────────────────────────────────────────────────────────
@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str, current=Depends(get_current_user)):
    prog = await db.progress.find_one({"_id": user_id})
    if not prog: raise HTTPException(404, "Progress not found")
    return prog

@app.put("/api/progress/{user_id}")
async def update_progress(user_id: str, data: ProgressUpdate, current=Depends(get_current_user)):
    subject_key = data.subject[:3].lower()
    await db.progress.update_one(
        {"_id": user_id},
        {"$inc": {subject_key: 5, "totalMinutes": data.minutes},
         "$push": {"emotionLog": {"$each": data.emotions}}}
    )
    return {"message": "Progress updated"}

# ─── Quizzes ──────────────────────────────────────────────────────────────────
@app.post("/api/quiz/submit")
async def submit_quiz(data: QuizResult, current=Depends(get_current_user)):
    result_id = f"qr_{current['_id']}_{int(datetime.utcnow().timestamp())}"
    result = {
        "_id": result_id, "userId": current["_id"],
        "subject": data.subject, "topic": data.topic,
        "score": data.score, "total": data.total, "pct": data.pct,
        "emotions": data.emotions, "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.utcnow().isoformat()
    }
    await db.quiz_results.insert_one(result)
    # Update student progress
    prog = await db.progress.find_one({"_id": current["_id"]})
    if prog:
        quizzes_done = prog.get("quizzesDone", 0) + 1
        avg = round(((prog.get("avgScore", 0) * (quizzes_done - 1)) + data.pct) / quizzes_done)
        badges = prog.get("badges", [])
        if data.pct >= 90 and "quiz_master" not in badges:
            badges.append("quiz_master")
        await db.progress.update_one(
            {"_id": current["_id"]},
            {"$set": {"quizzesDone": quizzes_done, "avgScore": avg, "badges": badges}}
        )
    return {"resultId": result_id, "message": "Quiz result saved"}

@app.get("/api/quiz/results/{user_id}")
async def get_quiz_results(user_id: str, current=Depends(get_current_user)):
    results = await db.quiz_results.find({"userId": user_id}).sort("timestamp", -1).to_list(50)
    return results

# ─── Teacher Endpoints ────────────────────────────────────────────────────────
@app.get("/api/teacher/students")
async def get_teacher_students(current=Depends(get_current_user)):
    if current["role"] != "teacher":
        raise HTTPException(403, "Teachers only")
    students = await db.users.find({"role": "student"}).to_list(100)
    result = []
    for s in students:
        prog = await db.progress.find_one({"_id": s["_id"]}) or {}
        last_session = await db.sessions.find_one(
            {"userId": s["_id"], "status": "active"},
            sort=[("startTime", -1)]
        )
        emotion = "offline"
        if last_session and last_session.get("emotions"):
            emotion = last_session["emotions"][-1]["emotion"]
        result.append({
            "id": s["_id"], "name": s["name"], "grade": s.get("grade"),
            "avgScore": prog.get("avgScore", 0), "sessions": prog.get("sessions", 0),
            "currentEmotion": emotion,
            "math": prog.get("math", 0), "science": prog.get("science", 0), "english": prog.get("english", 0)
        })
    return result

@app.get("/api/teacher/analytics")
async def teacher_analytics(current=Depends(get_current_user)):
    if current["role"] != "teacher":
        raise HTTPException(403, "Teachers only")
    students = await db.users.find({"role": "student"}).to_list(100)
    all_emotions = []
    for s in students:
        prog = await db.progress.find_one({"_id": s["_id"]}) or {}
        all_emotions.extend(prog.get("emotionLog", []))
    emo_counts = {}
    for e in all_emotions:
        emo_counts[e] = emo_counts.get(e, 0) + 1
    total = max(1, sum(emo_counts.values()))
    emotion_pct = {k: round(v/total*100) for k, v in emo_counts.items()}
    return {"emotionDistribution": emotion_pct, "totalStudents": len(students), "totalSessions": sum(emo_counts.values())}

# ─── Parent Endpoints ─────────────────────────────────────────────────────────
@app.get("/api/parent/child-progress")
async def parent_child_progress(current=Depends(get_current_user)):
    if current["role"] != "parent":
        raise HTTPException(403, "Parents only")
    child_id = current.get("childId")
    if not child_id:
        raise HTTPException(404, "No child linked to this account")
    child = await db.users.find_one({"_id": child_id})
    if not child: raise HTTPException(404, "Child not found")
    prog = await db.progress.find_one({"_id": child_id}) or {}
    quiz_results = await db.quiz_results.find({"userId": child_id}).sort("timestamp", -1).limit(10).to_list(10)
    return {"child": {k: v for k, v in child.items() if k != "password"},
            "progress": prog, "recentQuizzes": quiz_results}

# ─── WebSocket for Real-time Emotion ─────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
    async def connect(self, ws: WebSocket, session_id: str):
        await ws.accept()
        self.active[session_id] = ws
    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)
    async def send(self, session_id: str, data: dict):
        if session_id in self.active:
            await self.active[session_id].send_json(data)

ws_manager = ConnectionManager()

@app.websocket("/ws/emotion/{session_id}")
async def emotion_ws(ws: WebSocket, session_id: str):
    await ws_manager.connect(ws, session_id)
    try:
        while True:
            data = await ws.receive_text()
            frame_data = json.loads(data)
            frame_bytes = base64.b64decode(frame_data["frame"])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            result = emotion_detector.detect(frame)
            adaptation = adaptive_engine.get_adaptation(result["emotion"], frame_data.get("topic", ""))
            await ws_manager.send(session_id, {
                "emotion": result["emotion"],
                "confidence": result["confidence"],
                "probs": result["probs"],
                "adaptation": adaptation,
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)

# ─── Static Files ─────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")

# ─── Curriculum Data ──────────────────────────────────────────────────────────
CURRICULUM = [
    {"id": "math", "name": "Mathematics", "icon": "➕", "color": "#6C63FF",
     "topics": [
         {"id": "fractions", "name": "Fractions & Decimals", "status": "done"},
         {"id": "algebra", "name": "Introduction to Algebra", "status": "inprog"},
         {"id": "geometry", "name": "Geometry Basics", "status": "new"},
         {"id": "ratios", "name": "Ratios & Proportions", "status": "new"},
         {"id": "statistics", "name": "Basic Statistics", "status": "new"},
     ]},
    {"id": "science", "name": "Science", "icon": "🔬", "color": "#10B981",
     "topics": [
         {"id": "cells", "name": "Cell Structure", "status": "done"},
         {"id": "forces", "name": "Forces & Motion", "status": "inprog"},
         {"id": "photosynthesis", "name": "Photosynthesis", "status": "new"},
         {"id": "atoms", "name": "Atoms & Molecules", "status": "new"},
     ]},
    {"id": "english", "name": "English", "icon": "📖", "color": "#F59E0B",
     "topics": [
         {"id": "grammar", "name": "Parts of Speech", "status": "done"},
         {"id": "essay", "name": "Essay Writing", "status": "inprog"},
         {"id": "comprehension", "name": "Reading Comprehension", "status": "new"},
         {"id": "vocab", "name": "Vocabulary Building", "status": "new"},
     ]}
]
