"""
EmotiLearn AI — Emotion Detection Engine
Uses OpenCV face detection + CNN model trained on FER2013 dataset.
Detects: focused, confused, bored, happy, frustrated
"""
import cv2
import numpy as np
from pathlib import Path
import os

# Try TensorFlow/Keras, fall back to rule-based
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("[EmotionEngine] TensorFlow not found — using rule-based detection")

EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

# Map FER2013 7-class → our 5-class
FER_TO_EMOTILEARN = {
    'angry':    'frustrated',
    'disgust':  'frustrated',
    'fear':     'confused',
    'happy':    'happy',
    'sad':      'bored',
    'surprise': 'confused',
    'neutral':  'focused'
}

class EmotionDetector:
    def __init__(self):
        self.model = None
        self.face_cascade = None
        self._load_face_detector()
        self._load_model()

    def _load_face_detector(self):
        """Load OpenCV Haar Cascade for face detection."""
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if Path(cascade_path).exists():
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            print("[EmotionEngine] Face detector loaded")
        else:
            print("[EmotionEngine] WARNING: Haar cascade not found")

    def _load_model(self):
        """Load pre-trained CNN model or build architecture."""
        model_path = Path(__file__).parent / 'models' / 'emotion_cnn.h5'
        if TF_AVAILABLE and model_path.exists():
            try:
                self.model = keras.models.load_model(str(model_path))
                print(f"[EmotionEngine] Model loaded from {model_path}")
                return
            except Exception as e:
                print(f"[EmotionEngine] Could not load model: {e}")
        if TF_AVAILABLE:
            print("[EmotionEngine] Building CNN architecture (not trained — run train.py)")
            self.model = self._build_cnn()

    def _build_cnn(self):
        """
        CNN architecture for FER2013 emotion recognition.
        Input: 48x48 grayscale images
        Output: 7-class softmax (FER2013 classes)
        Train with: python train.py
        """
        model = keras.Sequential([
            # Block 1
            keras.layers.Conv2D(64, (3,3), padding='same', activation='relu', input_shape=(48,48,1)),
            keras.layers.BatchNormalization(),
            keras.layers.Conv2D(64, (3,3), padding='same', activation='relu'),
            keras.layers.MaxPooling2D(2,2),
            keras.layers.Dropout(0.25),
            # Block 2
            keras.layers.Conv2D(128, (3,3), padding='same', activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Conv2D(128, (3,3), padding='same', activation='relu'),
            keras.layers.MaxPooling2D(2,2),
            keras.layers.Dropout(0.25),
            # Block 3
            keras.layers.Conv2D(256, (3,3), padding='same', activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.MaxPooling2D(2,2),
            keras.layers.Dropout(0.25),
            # Dense
            keras.layers.Flatten(),
            keras.layers.Dense(512, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(256, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(7, activation='softmax')
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        return model

    def detect(self, frame: np.ndarray) -> dict:
        """
        Detect emotion from a webcam frame.

        Args:
            frame: BGR image from OpenCV

        Returns:
            {
                "emotion": str,          # EmotiLearn 5-class emotion
                "confidence": float,     # 0.0 - 1.0
                "probs": dict,           # all 5 emotion probabilities
                "face_detected": bool,
                "face_bbox": tuple | None
            }
        """
        if frame is None or frame.size == 0:
            return self._default_result()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_bbox = None

        # Detect face
        if self.face_cascade is not None:
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5,
                minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE
            )
            if len(faces) > 0:
                # Use largest face
                face_bbox = max(faces, key=lambda f: f[2]*f[3])

        if face_bbox is None:
            return self._default_result(face_detected=False)

        x, y, w, h = face_bbox
        face_roi = gray[y:y+h, x:x+w]

        # Run CNN inference if model available
        if self.model is not None and TF_AVAILABLE:
            return self._cnn_predict(face_roi, face_bbox)
        else:
            # Heuristic / rule-based fallback using brightness & contrast
            return self._heuristic_detect(face_roi, face_bbox)

    def _cnn_predict(self, face_roi: np.ndarray, bbox: tuple) -> dict:
        """Run CNN model on face ROI."""
        resized = cv2.resize(face_roi, (48, 48))
        normalized = resized.astype('float32') / 255.0
        input_tensor = normalized.reshape(1, 48, 48, 1)
        raw_probs = self.model.predict(input_tensor, verbose=0)[0]
        fer_idx = int(np.argmax(raw_probs))
        fer_emotion = EMOTIONS[fer_idx]
        el_emotion = FER_TO_EMOTILEARN[fer_emotion]
        confidence = float(raw_probs[fer_idx])
        # Aggregate to 5-class
        probs_5 = self._aggregate_probs(raw_probs)
        return {
            "emotion": el_emotion, "confidence": confidence,
            "probs": probs_5, "face_detected": True,
            "face_bbox": tuple(int(v) for v in bbox)
        }

    def _aggregate_probs(self, raw_probs: np.ndarray) -> dict:
        """Aggregate 7-class FER probs to 5 EmotiLearn classes."""
        mapping = {'frustrated': ['angry', 'disgust'],
                   'confused':   ['fear', 'surprise'],
                   'happy':      ['happy'],
                   'bored':      ['sad'],
                   'focused':    ['neutral']}
        result = {}
        for el_class, fer_classes in mapping.items():
            result[el_class] = float(sum(raw_probs[EMOTIONS.index(f)] for f in fer_classes))
        # Normalize
        total = max(sum(result.values()), 1e-9)
        return {k: round(v/total, 3) for k, v in result.items()}

    def _heuristic_detect(self, face_roi: np.ndarray, bbox: tuple) -> dict:
        """Rule-based emotion estimation using pixel statistics."""
        brightness = float(np.mean(face_roi))
        contrast   = float(np.std(face_roi))
        # Very simple heuristic — replace with CNN in production
        if brightness > 140 and contrast > 50:
            emotion, conf = 'happy', 0.65
        elif contrast < 25:
            emotion, conf = 'bored', 0.58
        elif brightness < 80:
            emotion, conf = 'frustrated', 0.60
        elif contrast > 70:
            emotion, conf = 'confused', 0.55
        else:
            emotion, conf = 'focused', 0.70
        probs = {e: 0.05 for e in ['focused','confused','bored','happy','frustrated']}
        probs[emotion] = conf
        return {
            "emotion": emotion, "confidence": conf, "probs": probs,
            "face_detected": True, "face_bbox": tuple(int(v) for v in bbox)
        }

    def _default_result(self, face_detected=True) -> dict:
        return {
            "emotion": "focused", "confidence": 0.0,
            "probs": {"focused":1.0,"confused":0.0,"bored":0.0,"happy":0.0,"frustrated":0.0},
            "face_detected": face_detected, "face_bbox": None
        }


# ─── Training Script (run separately) ────────────────────────────────────────
TRAIN_SCRIPT = '''
"""
Train the emotion CNN on FER2013 dataset.
Download FER2013: https://www.kaggle.com/datasets/msambare/fer2013
Place fer2013.csv in the data/ folder, then run: python train.py
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow import keras
import tensorflow as tf

# Load FER2013
df = pd.read_csv('data/fer2013.csv')
X = np.array([np.fromstring(row, dtype=int, sep=' ').reshape(48,48,1)/255.0
               for row in df['pixels']])
y = keras.utils.to_categorical(df['emotion'], 7)
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.1, random_state=42)

# Build model (same architecture as emotion_engine.py)
from emotion_engine import EmotionDetector
detector = EmotionDetector()
model = detector._build_cnn()

# Train with callbacks
callbacks = [
    keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
    keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5),
    keras.callbacks.ModelCheckpoint('models/emotion_cnn.h5', save_best_only=True)
]
model.fit(X_train, y_train, batch_size=64, epochs=100,
          validation_data=(X_val, y_val), callbacks=callbacks)
print("Training complete! Model saved to models/emotion_cnn.h5")
'''

if __name__ == "__main__":
    # Quick test
    detector = EmotionDetector()
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    result = detector.detect(test_frame)
    print("Test result:", result)
