import cv2



import numpy as np



import mediapipe as mp



from mediapipe.tasks import python



from mediapipe.tasks.python import vision



import onnxruntime as ort



import pickle



import os







# -----------------------------



# Models



# -----------------------------



# Get absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
model_path = os.path.join(project_root, "models", "face_landmarker.task")
embedder_path = os.path.join(project_root, "models", "embedder_arcface.onnx")
data_path = os.path.join(project_root, "data")

# Initialize MediaPipe Face Detector
base_options = python.BaseOptions(model_asset_path=model_path)
detector_options = vision.FaceDetectorOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    min_detection_confidence=0.5
)
face_detector = vision.FaceDetector.create_from_options(detector_options)

# Create FaceLandmarker detector using Tasks API
landmarker_options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_faces=1
)
face_mesh = vision.FaceLandmarker.create_from_options(landmarker_options)

session = ort.InferenceSession(embedder_path)



input_name = session.get_inputs()[0].name







# -----------------------------



# Alignment reference points



# -----------------------------



REF_POINTS = np.array([



    [38.2946, 51.6963],



    [73.5318, 51.5014],



    [56.0252, 71.7366],



    [41.5493, 92.3655],



    [70.7299, 92.2041]



], dtype=np.float32)







INDICES = [33, 263, 1, 61, 291]  # eye, eye, nose, mouth, mouth











# -----------------------------



# Preprocess for ArcFace



# -----------------------------



def preprocess(aligned):



    img = aligned.astype(np.float32)



    img = (img - 127.5) / 127.5



    img = np.transpose(img, (2, 0, 1))



    img = np.expand_dims(img, axis=0)



    return img











# -----------------------------



# Load DB



# -----------------------------



DB_PATH = os.path.join(data_path, "db", "face_db.pkl")







if os.path.exists(DB_PATH):



    with open(DB_PATH, 'rb') as f:



        db = pickle.load(f)



else:



    db = {}







# -----------------------------



# Enrollment Setup



# -----------------------------



name = input("Enter identity name: ").strip()



os.makedirs(os.path.join(data_path, "enroll", name), exist_ok=True)







embeddings = []



count = 0



# Create resizable windows
cv2.namedWindow("Enroll", cv2.WINDOW_NORMAL)
cv2.namedWindow("Saved Aligned", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Enroll", 1280, 720)
cv2.resizeWindow("Saved Aligned", 224, 224)

cap = cv2.VideoCapture(0)







print("Look at camera. Auto-capture on good face. Aim for 15+ samples. Press Q to finish.")







# -----------------------------



# Capture Loop



# -----------------------------



while True:



    ret, frame = cap.read()



    if not ret:



        print("Camera read failed")



        break







    frame = cv2.flip(frame, 1)



    # Convert frame to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    # Detect faces using MediaPipe
    detection_result = face_detector.detect(mp_image)
    
    if detection_result.detections:
        detection = detection_result.detections[0]
        bbox = detection.bounding_box
        x, y = int(bbox.origin_x), int(bbox.origin_y)
        w, h = int(bbox.width), int(bbox.height)
        
        # safety crop bounds
        x, y = max(0, x), max(0, y)
        w, h = min(w, frame.shape[1] - x), min(h, frame.shape[0] - y)
        crop = frame[y:y+h, x:x+w]

        if crop.size == 0:
            continue
            
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = face_mesh.detect(mp_image)

        if results.face_landmarks:
            lm = results.face_landmarks[0]
            ch, cw = crop.shape[:2]
            pts = np.array(
                [[lm.landmark[i].x * cw, lm.landmark[i].y * ch] for i in INDICES],
                dtype=np.float32
            )

            M, _ = cv2.estimateAffinePartial2D(pts, REF_POINTS)

            if M is None:
                continue

            aligned = cv2.warpAffine(
                crop, M, (112, 112),
                flags=cv2.INTER_LINEAR,
                borderValue=0
            )

            blob = preprocess(aligned)

            # ✅ correct ONNX call
            emb = session.run(None, {input_name: blob})[0][0]

            # normalize embedding safely
            norm = np.linalg.norm(emb)
            if norm == 0:
                continue

            emb = emb / norm

            embeddings.append(emb)

            count += 1

            cv2.imwrite(os.path.join(data_path, "enroll", name, f"{count:04d}.jpg"), aligned)

            cv2.putText(
                frame,
                f"Captured {count}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )

            # Show aligned face
            cv2.imshow("Saved Aligned", aligned)




    # Get current window size and resize frame to match (maintain aspect ratio)
    window_width = cv2.getWindowImageRect('Enroll')[2]
    window_height = cv2.getWindowImageRect('Enroll')[3]

    if window_width > 0 and window_height > 0:
        h, w = frame.shape[:2]
        aspect_ratio = w / h

        new_width = window_width
        new_height = int(window_width / aspect_ratio)

        if new_height > window_height:
            new_height = window_height
            new_width = int(window_height * aspect_ratio)

        frame_resized = cv2.resize(frame, (new_width, new_height))
        cv2.imshow("Enroll", frame_resized)
    else:
        cv2.imshow("Enroll", frame)







    key = cv2.waitKey(1) & 0xFF

    if key == ord('q') or key == 27:  # q OR ESC
        print("Exiting...")
        break

    if cv2.getWindowProperty('Enroll', cv2.WND_PROP_VISIBLE) < 1:
        print("Window closed")
        break

    if key == ord('s'):  # s
        print("Saving...")
        break

    if cv2.getWindowProperty('Enroll', cv2.WND_PROP_VISIBLE) < 1:
        print("Window closed")
        break




# -----------------------------



# Save DB



# -----------------------------



if embeddings:
    # Compute mean embedding for this person
    mean_embedding = np.mean(embeddings, axis=0)
    mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)
    
    # Save to database
    db[name] = {
        'embedding': mean_embedding,
        'samples': len(embeddings),
        'created_at': str(np.datetime64('now'))
    }

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with open(DB_PATH, 'wb') as f:
        pickle.dump(db, f)

    print(f" Successfully enrolled {name} with {len(embeddings)} samples!")
    print(f"Database saved to {DB_PATH}")
else:
    print(" No samples captured.") 




cap.release()



cv2.destroyAllWindows()
