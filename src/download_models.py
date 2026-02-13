#!/usr/bin/env python3
"""
Download required ONNX models for face recognition
"""

import os
import urllib.request
import sys

def download_file(url, destination):
    """Download a file with progress indicator"""
    print(f"Downloading from: {url}")
    print(f"Saving to: {destination}")
    
    try:
        def reporthook(blocknum, blocksize, totalsize):
            readsofar = blocknum * blocksize
            if totalsize > 0:
                percent = readsofar * 1e2 / totalsize
                s = f"\r{percent:.1f}% complete ({readsofar}/{totalsize} bytes)"
                sys.stderr.write(s)
                if readsofar >= totalsize:
                    sys.stderr.write("\n")
        
        urllib.request.urlretrieve(url, destination, reporthook)
        print(f"✓ Downloaded successfully: {destination}")
        return True
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False

def main():
    # Base path for models
    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # ArcFace ONNX model (w600k_r50, from InsightFace)
    # This is a popular pre-trained model
    arcface_model = os.path.join(models_dir, "embedder_arcface.onnx")
    
    if os.path.exists(arcface_model):
        print(f"✓ Model already exists: {arcface_model}")
    else:
        print(f"Downloading ArcFace ONNX model...")
        # Try multiple sources for the ArcFace model
        urls = [
            # HuggingFace mirror
            "https://huggingface.co/spaces/radames/arcface-onnx/resolve/main/model.onnx",
            # Alternative: ONNX Model Zoo (ResNet50 based)
            "https://github.com/onnx/models/raw/master/vision/body_analysis/arcface/model/arcface.onnx",
        ]
        
        success = False
        for url in urls:
            if download_file(url, arcface_model):
                success = True
                break
            print(f"  Trying alternative source...")
        
        if success:
            print(f"✓ Successfully downloaded ArcFace model")
        else:
            print(f"✗ Failed to download ArcFace model from all sources")
            print(f"\nManual download options:")
            print(f"1. HuggingFace: https://huggingface.co/spaces/radames/arcface-onnx/")
            print(f"2. ONNX Model Zoo: https://github.com/onnx/models/tree/master/vision/body_analysis/arcface")
            print(f"\nPlace the downloaded model at: {arcface_model}")
            return False
    
    print("\n✓ All models ready!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
