#!/usr/bin/env python3
"""
Check ArcFace model input requirements
"""
import onnxruntime as ort
import os

# Get absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
embedder_path = os.path.join(project_root, "models", "embedder_arcface.onnx")

# Load model and check input/output
session = ort.InferenceSession(embedder_path)

print("=== ArcFace Model Information ===")
print(f"Model path: {embedder_path}")

# Check inputs
print("\nInputs:")
for input_meta in session.get_inputs():
    print(f"  Name: {input_meta.name}")
    print(f"  Type: {input_meta.type}")
    print(f"  Shape: {input_meta.shape}")

# Check outputs
print("\nOutputs:")
for output_meta in session.get_outputs():
    print(f"  Name: {output_meta.name}")
    print(f"  Type: {output_meta.type}")
    print(f"  Shape: {output_meta.shape}")
