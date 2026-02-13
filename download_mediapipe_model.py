#!/usr/bin/env python3
"""
Download MediaPipe Face Landmarker model
"""
import urllib.request
import os

def download_mediapipe_model():
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)
    destination = os.path.join(models_dir, "face_landmarker.task")
    
    print(f"Downloading MediaPipe Face Landmarker model...")
    print(f"From: {url}")
    print(f"To: {destination}")
    
    try:
        def reporthook(blocknum, blocksize, totalsize):
            if totalsize > 0:
                percent = min(100, (blocknum * blocksize * 100) // totalsize)
                print(f"\rProgress: {percent}% ({blocknum * blocksize}/{totalsize} bytes)", end="")
            else:
                print(f"\rDownloaded: {blocknum * blocksize} bytes", end="")
        
        urllib.request.urlretrieve(url, destination, reporthook)
        print(f"\n✓ Successfully downloaded MediaPipe model!")
        return True
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        return False

if __name__ == "__main__":
    success = download_mediapipe_model()
    if success:
        print("MediaPipe model ready for face detection!")
    else:
        print("Please download the model manually from MediaPipe website")
