#!/usr/bin/env python3
"""
Simple face enrollment using Haar cascade (fallback method)
"""
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import onnxruntime as ort
import pickle
import os

# Get absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
embedder_path = os.path.join(project_root, "models", "embedder_arcface.onnx")
data_path = os.path.join(project_root, "data")

# Initialize Haar cascade face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize ArcFace embedder
session = ort.InferenceSession(embedder_path)
input_name = session.get_inputs()[0].name

# Face alignment reference points
REF_POINTS = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041]
], dtype=np.float32)

INDICES = [33, 263, 1, 61, 291]  # MediaPipe landmark indices

def preprocess_face(aligned_face):
    """Preprocess face for ArcFace - expects RGB format"""
    img = aligned_face.astype(np.float32)
    img = (img - 127.5) / 127.5
    # ArcFace expects (1, 3, 112, 112) format
    img = np.transpose(img, (2, 0, 1))  # HWC to CHW
    img = np.expand_dims(img, axis=0)   # Add batch dimension
    return img

def align_face_simple(image):
    """Simple resize fallback when landmarks aren't available"""
    # Convert BGR to RGB for ArcFace
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return cv2.resize(rgb_image, (112, 112))

def main():
    print("=== Simple Face Enrollment System ===")
    
    # Get person name
    name = input("Enter your name: ").strip().lower()
    if not name:
        print("Name cannot be empty!")
        return
    
    # Create person directory
    person_dir = os.path.join(data_path, "enroll", name)
    os.makedirs(person_dir, exist_ok=True)
    
    # Load existing database
    db_path = os.path.join(data_path, "db", "face_db.pkl")
    if os.path.exists(db_path):
        with open(db_path, 'rb') as f:
            database = pickle.load(f)
    else:
        database = {}
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera!")
        return
    
    print(f"\nEnrolling {name}...")
    print("Look at the camera. Faces will be captured automatically.")
    print("Or press SPACE to capture manually.")
    print("Press 'q' to quit, 's' to save and quit")
    
    embeddings = []
    count = 0
    auto_capture_timer = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break
        
        # Flip frame horizontally (mirror effect)
        frame = cv2.flip(frame, 1)
        
        # Convert to grayscale for Haar cascade
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces using Haar cascade
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
        
        # Process detected faces
        face_detected = False
        for (x, y, w, h) in faces:
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Crop face
            face_crop = frame[y:y+h, x:x+w]
            
            if face_crop.size > 0:
                face_detected = True
                
                # Auto-capture every 30 frames if face is stable
                auto_capture_timer += 1
                if auto_capture_timer >= 30:
                    auto_capture_timer = 0
                    
                    # Simple alignment (resize)
                    aligned_face = align_face_simple(face_crop)
                    
                    # Generate embedding
                    preprocessed = preprocess_face(aligned_face)
                    embedding = session.run(None, {input_name: preprocessed})[0][0]
                    
                    # Normalize embedding
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm
                        embeddings.append(embedding)
                        
                        # Save aligned face image
                        count += 1
                        cv2.imwrite(os.path.join(person_dir, f"{count:04d}.jpg"), aligned_face)
                        
                        print(f"Auto-captured sample {count}")
                        
                        # Show capture feedback
                        cv2.putText(frame, f"Captured {count}!", (x, y-30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Show aligned face
                        cv2.imshow('Captured Face', aligned_face)
                
                # Show instructions
                cv2.putText(frame, f"Auto-capturing...", (x, y-10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # If no face detected, reset timer
        if not face_detected:
            auto_capture_timer = 0
        
        # Show status
        cv2.putText(frame, f"Samples: {count}/15", (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        if face_detected:
            cv2.putText(frame, "Face detected - auto-capturing...", (10, 60), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "No face detected - position yourself in camera", (10, 60), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Show frame
        cv2.imshow('Simple Face Enrollment', frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' ') and len(faces) > 0:  # Space bar to capture manually
            # Capture the first detected face
            x, y, w, h = faces[0]
            face_crop = frame[y:y+h, x:x+w]
            
            if face_crop.size > 0:
                aligned_face = align_face_simple(face_crop)
                preprocessed = preprocess_face(aligned_face)
                embedding = session.run(None, {input_name: preprocessed})[0][0]
                
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                    embeddings.append(embedding)
                    
                    # Save aligned face image
                    count += 1
                    cv2.imwrite(os.path.join(person_dir, f"{count:04d}.jpg"), aligned_face)
                    
                    print(f"Manually captured sample {count}")
                    
                    # Show capture feedback
                    cv2.putText(frame, f"Captured {count}!", (x, y-30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Show aligned face
                    cv2.imshow('Captured Face', aligned_face)
        elif key == ord('s'):
            # Save and quit
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Save embeddings to database
    if len(embeddings) >= 5:  # Minimum 5 samples
        # Compute mean embedding
        mean_embedding = np.mean(embeddings, axis=0)
        mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)
        
        database[name] = {
            'embedding': mean_embedding,
            'samples': len(embeddings),
            'created_at': str(np.datetime64('now'))
        }
        
        # Save database
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with open(db_path, 'wb') as f:
            pickle.dump(database, f)
        
        print(f"\n✓ Successfully enrolled {name} with {len(embeddings)} samples!")
        print(f"Database saved to {db_path}")
    else:
        print(f"\n✗ Not enough samples captured ({len(embeddings)}). Minimum required: 5")
        print("Please try again and capture at least 5 good face images.")

if __name__ == "__main__":
    main()
