#!/usr/bin/env python3
"""Quick verdict on whether OCR will run on the GPU. Prints the onnxruntime providers and a clear
GPU READY / CPU ONLY result with the likely reason. Run: python engine/gpu_check.py"""
import shutil, subprocess, sys

def main():
    print("=== THE VIEWER — GPU readiness check ===")
    # 1) driver
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            out = subprocess.run([smi, "--query-gpu=name,driver_version", "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=15).stdout.strip()
            print("NVIDIA driver: OK ->", out or "(card detected)")
        except Exception as e:
            print("NVIDIA driver: nvidia-smi present but errored:", e)
    else:
        print("NVIDIA driver: nvidia-smi NOT found — no NVIDIA GPU/driver visible (will use CPU).")

    # 2) onnxruntime providers
    try:
        import onnxruntime as ort
        provs = ort.get_available_providers()
        print("onnxruntime:", ort.__version__, "| providers:", provs)
        gpu = "CUDAExecutionProvider" in provs
    except Exception as e:
        print("onnxruntime: NOT importable ->", e)
        provs, gpu = [], False

    # 3) rapidocr present?
    try:
        import rapidocr_onnxruntime  # noqa
        print("RapidOCR: installed")
    except Exception:
        print("RapidOCR: NOT installed (run_ocr_gpu.bat installs it)")

    print("-" * 44)
    if gpu and smi:
        print("VERDICT: GPU READY [OK]  -- run engine\\run_ocr_gpu.bat for fast OCR.")
        return 0
    print("VERDICT: CPU ONLY  — OCR will still run, just slower. Likely fix:")
    if not smi:
        print("  • Install/update the NVIDIA driver (nvidia-smi must work).")
    elif "onnxruntime" not in str(provs) and not provs:
        print("  • pip uninstall -y onnxruntime onnxruntime-gpu  &&  pip install --user onnxruntime-gpu")
    elif not gpu:
        print("  • Replace CPU onnxruntime with the GPU build:")
        print("      pip uninstall -y onnxruntime onnxruntime-gpu")
        print("      pip install --user onnxruntime-gpu")
        print("  • If still CPU: CUDA/driver mismatch — update the driver and match onnxruntime-gpu to")
        print("    a supported CUDA (e.g. pip install --user \"onnxruntime-gpu==1.17.1\"). See docs/SETUP-GPU.md.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
