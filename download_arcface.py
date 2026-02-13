#!/usr/bin/env python3
"""
Download ArcFace model from HuggingFace
"""
import urllib.request
import os

def download_arcface():
    url = "https://huggingface.co/garavv/arcface-onnx/resolve/main/arc.onnx?download=true"
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)
    destination = os.path.join(models_dir, "embedder_arcface.onnx")
    
    print(f"Downloading ArcFace model from {url}")
    print(f"Saving to {destination}")
    
    try:
        urllib.request.urlretrieve(url, destination)
        print(f"✓ Successfully downloaded ArcFace model!")
        return True
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False

if __name__ == "__main__":
    success = download_arcface()
    if success:
        print("Model ready for face recognition!")
    else:
        print("Please download the model manually from:")
        print("https://huggingface.co/garavv/arcface-onnx")
