"""
EmotiLearn AI — Database Schema & Seeder
Run: python seed.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import bcrypt

MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.emotilearn

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

"""
==========================================================
MONGODB SCHEMA
==========================================================

COLLECTION: users
─────────────────
{
  _id: "u_alex_1742000000",      # string ID
  username: "alex123",
  password: "<bcrypt hash>",
  name: "Alex Johnson",
  role: "student" | "teacher" | "parent",
  grade: "6" | "7",              # students only
  age: 12,                        # students only
  avatar: "AJ",                   # initials
  color: "#6C63FF",               # avatar color
  parentId: "u_parent_...",       # students only
  childId: "u_student_...",       # parents only
  teacherId: "u_teacher_...",     # students only
  createdAt: "2026-03-17T00:00:00"
}

COLLECTION: progress
─────────────────────
{
  _id: "u_alex_...",   # same as user._id
  userId: "u_alex_...",
  math: 72,             # 0-100 percent complete
  science: 45,
  english: 60,
  sessions: 12,
  totalMinutes: 260,
  quizzesDone: 24,
  avgScore: 85,          # average quiz % score
  badges: ["first_session", "quiz_master"],
  emotionLog: ["focused", "confused", "focused", ...]
}

COLLECTION: sessions
─────────────────────
{
  _id: "sess_u_alex_1742000000",
  userId: "u_alex_...",
  subject: "math",
  topic: "algebra",
  startTime: "2026-03-17T10:00:00",
  endTime: "2026-03-17T10:32:00",
  durationMinutes: 32,
  status: "active" | "completed",
  emotions: [
    { emotion: "focused", confidence: 0.92, timestamp: "..." },
    { emotion: "confused", confidence: 0.78, timestamp: "..." }
  ],
  adaptations: [
    { type: "simplify", title: "...", emotion: "confused", topic: "algebra", timestamp: "..." }
  ]
}

COLLECTION: quiz_results
─────────────────────────
{
  _id: "qr_u_alex_1742000001",
  userId: "u_alex_...",
  subject: "math",
  topic: "algebra",
  score: 8,
  total: 10,
  pct: 80.0,
  emotions: ["focused", "confused", "focused", "happy"],
  date: "2026-03-17",
  timestamp: "2026-03-17T10:32:00"
}

COLLECTION: lessons
────────────────────
{
  _id: "lesson_algebra",
  topicId: "algebra",
  subject: "math",
  title: "Introduction to Algebra",
  content: "...",
  formula: "ax + b = c",
  formulaNote: "...",
  explanation: "...",
  simpleExplanation: "...",
  hint: "...",
  keyPoints: [...],
  examples: [...],
  quiz: [...],
  createdAt: "..."
}

INDEXES:
  users:        { username: 1 } unique
  sessions:     { userId: 1, startTime: -1 }
  quiz_results: { userId: 1, timestamp: -1 }
  progress:     { userId: 1 } unique
"""

async def create_indexes():
    await db.users.create_index("username", unique=True)
    await db.sessions.create_index([("userId", 1), ("startTime", -1)])
    await db.quiz_results.create_index([("userId", 1), ("timestamp", -1)])
    await db.progress.create_index("userId", unique=True)
    print("Indexes created.")

async def seed():
    print("Seeding database...")
    await db.users.drop()
    await db.progress.drop()
    await db.quiz_results.drop()
    await db.sessions.drop()
    await db.lessons.drop()
    await create_indexes()

    # --- Users ---
    users = [
        {"_id":"u1","username":"alex123","password":hash_pw("pass123"),"name":"Alex Johnson","role":"student","grade":"7","age":12,"avatar":"AJ","color":"#6C63FF","parentId":"u6","teacherId":"u4","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u2","username":"priya456","password":hash_pw("pass123"),"name":"Priya Sharma","role":"student","grade":"7","age":12,"avatar":"PS","color":"#EC4899","parentId":"u7","teacherId":"u4","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u3","username":"raj789","password":hash_pw("pass123"),"name":"Raj Kumar","role":"student","grade":"6","age":11,"avatar":"RK","color":"#10B981","parentId":"u8","teacherId":"u5","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u4","username":"ms_johnson","password":hash_pw("pass123"),"name":"Ms. R. Johnson","role":"teacher","subject":"Mathematics","avatar":"RJ","color":"#6C63FF","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u5","username":"mr_patel","password":hash_pw("pass123"),"name":"Mr. S. Patel","role":"teacher","subject":"Science","avatar":"SP","color":"#10B981","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u6","username":"parent_alex","password":hash_pw("pass123"),"name":"Mr. K. Johnson","role":"parent","childId":"u1","avatar":"KJ","color":"#F59E0B","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u7","username":"parent_priya","password":hash_pw("pass123"),"name":"Mrs. Meera Sharma","role":"parent","childId":"u2","avatar":"MS","color":"#EC4899","createdAt":datetime.utcnow().isoformat()},
        {"_id":"u8","username":"parent_raj","password":hash_pw("pass123"),"name":"Mr. Arun Kumar","role":"parent","childId":"u3","avatar":"AK","color":"#10B981","createdAt":datetime.utcnow().isoformat()},
    ]
    await db.users.insert_many(users)

    # --- Progress ---
    progress = [
        {"_id":"u1","userId":"u1","math":72,"science":45,"english":60,"sessions":12,"totalMinutes":260,"quizzesDone":24,"avgScore":85,"badges":["first_session","quiz_master","week_streak"],"emotionLog":["focused","focused","confused","focused","happy","bored","focused","focused","frustrated","focused","focused","happy"]},
        {"_id":"u2","userId":"u2","math":55,"science":70,"english":40,"sessions":9,"totalMinutes":185,"quizzesDone":18,"avgScore":72,"badges":["first_session"],"emotionLog":["confused","focused","confused","focused","bored","focused","frustrated","confused","focused"]},
        {"_id":"u3","userId":"u3","math":68,"science":50,"english":75,"sessions":7,"totalMinutes":145,"quizzesDone":14,"avgScore":79,"badges":["first_session","week_streak"],"emotionLog":["bored","focused","happy","bored","focused","focused","happy"]},
    ]
    await db.progress.insert_many(progress)

    # --- Quiz Results ---
    quiz_results = [
        {"_id":"qr1","userId":"u1","subject":"math","topic":"algebra","score":8,"total":10,"pct":80,"date":"2026-03-15","timestamp":"2026-03-15T10:30:00","emotions":["focused","confused","focused","focused"]},
        {"_id":"qr2","userId":"u1","subject":"science","topic":"forces","score":7,"total":10,"pct":70,"date":"2026-03-14","timestamp":"2026-03-14T14:00:00","emotions":["focused","happy","focused","focused"]},
        {"_id":"qr3","userId":"u1","subject":"math","topic":"fractions","score":9,"total":10,"pct":90,"date":"2026-03-13","timestamp":"2026-03-13T09:00:00","emotions":["focused","focused","happy","focused"]},
        {"_id":"qr4","userId":"u2","subject":"science","topic":"cells","score":7,"total":10,"pct":70,"date":"2026-03-15","timestamp":"2026-03-15T11:00:00","emotions":["confused","focused","frustrated","focused"]},
        {"_id":"qr5","userId":"u3","subject":"english","topic":"grammar","score":8,"total":10,"pct":80,"date":"2026-03-15","timestamp":"2026-03-15T13:00:00","emotions":["bored","happy","focused","focused"]},
    ]
    await db.quiz_results.insert_many(quiz_results)

    print("Database seeded successfully!")
    print("\nDemo Credentials:")
    print("  Student : alex123   / pass123")
    print("  Student : priya456  / pass123")
    print("  Teacher : ms_johnson / pass123")
    print("  Parent  : parent_alex / pass123")

if __name__ == "__main__":
    asyncio.run(seed())
