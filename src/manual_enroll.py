#!/usr/bin/env python3
"""
Manual face enrollment - captures center of frame
"""
import cv2
import numpy as np
import onnxruntime as ort
import pickle
import os

# Get absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
embedder_path = os.path.join(project_root, "models", "embedder_arcface.onnx")
data_path = os.path.join(project_root, "data")

# Initialize ArcFace embedder
session = ort.InferenceSession(embedder_path)
input_name = session.get_inputs()[0].name

def preprocess_face(aligned_face):
    """Preprocess face for ArcFace - expects RGB format"""
    img = aligned_face.astype(np.float32)
    img = (img - 127.5) / 127.5
    # ArcFace expects (1, 112, 112, 3) format (batch, height, width, channels)
    img = np.expand_dims(img, axis=0)   # Add batch dimension
    return img

def main():
    print("=== Manual Face Enrollment System ===")
    
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
    print("Position your face in the center of the camera frame")
    print("Press SPACE to capture face manually")
    print("Press 'q' to quit, 's' to save and quit")
    
    embeddings = []
    count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break
        
        # Flip frame horizontally (mirror effect)
        frame = cv2.flip(frame, 1)
        
        # Get frame dimensions
        h, w = frame.shape[:2]
        
        # Define center region for face capture (larger area)
        center_x, center_y = w // 2, h // 2
        crop_size = min(h, w) // 2  # Use half of the smaller dimension
        
        # Calculate crop coordinates
        x1 = max(0, center_x - crop_size // 2)
        y1 = max(0, center_y - crop_size // 2)
        x2 = min(w, center_x + crop_size // 2)
        y2 = min(h, center_y + crop_size // 2)
        
        # Draw center rectangle (face capture area)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, "Position face here", (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Draw center crosshair
        cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 0, 255), 1)
        cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 0, 255), 1)
        
        # Show status
        cv2.putText(frame, f"Samples: {count}/15", (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, "Press SPACE to capture", (10, 60), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show frame
        cv2.imshow('Manual Face Enrollment', frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):  # Space bar to capture
            # Capture center region
            face_crop = frame[y1:y2, x1:x2]
            
            if face_crop.size > 0:
                # Convert BGR to RGB for ArcFace
                rgb_image = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                
                # Resize to 112x112 for ArcFace
                aligned_face = cv2.resize(rgb_image, (112, 112))
                
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
                    
                    print(f"Captured sample {count}")
                    
                    # Show capture feedback
                    cv2.putText(frame, f"Captured {count}!", (center_x - 50, center_y - 50), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Show aligned face
                    cv2.imshow('Captured Face', aligned_face)
                    
                    # Brief pause to show feedback
                    cv2.waitKey(500)
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
