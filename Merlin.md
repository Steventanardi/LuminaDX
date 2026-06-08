# How to Run Merlin 100% Locally (3D Volumetric Model)

Merlin is a specialized vision-language foundation model for **abdominal CT interpretation**. Unlike 2D models, it natively ingests 3D NIfTI (`.nii.gz`) volumes. 

Because LM Studio and Ollama are built on `llama.cpp` (which only supports text and 2D images), **you cannot use Ollama to run Merlin**. 

Instead, you must run it natively using Python, PyTorch, and the Hugging Face Transformers library. Here is how you build a 100% local, offline pipeline for it.

---

## Step 1: Prepare the Python Environment

You need a Python environment with PyTorch configured for your RTX 4070 (CUDA 12.1+).

1. Open PowerShell and create a new virtual environment:
   ```powershell
   python -m venv merlin_env
   .\merlin_env\Scripts\activate
   ```

2. Install PyTorch with CUDA support, plus the required Hugging Face libraries and medical imaging tools (MONAI/nibabel):
   ```powershell
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   pip install transformers accelerate huggingface_hub nibabel monai
   ```

## Step 2: Download the Model Weights Locally

To ensure you are 100% offline during inference, download the weights to your local machine first. 
*(Note: Replace `merlin-org/merlin-abdominal-ct` with the actual repository name on Hugging Face when it becomes public).*

```powershell
huggingface-cli download merlin-org/merlin-abdominal-ct --local-dir C:\models\merlin
```
This will download the PyTorch `.bin` or `.safetensors` files to `C:\models\merlin`.

## Step 3: Write the Inference Script

Since you cannot use the Ollama API, you must write a Python script that loads the model into your GPU VRAM, processes the 3D NIfTI file, and runs generation.

Create a file called `run_merlin.py`:

```python
import torch
import nibabel as nib
from transformers import AutoModelForCausalLM, AutoProcessor

# 1. Load the model and processor locally (offline)
model_path = r"C:\models\merlin"

print("Loading processor...")
processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)

print("Loading model into VRAM...")
model = AutoModelForCausalLM.from_pretrained(
    model_path, 
    device_map="cuda",          # Load directly to RTX 4070
    torch_dtype=torch.float16,  # Use half-precision to fit in 8GB VRAM
    local_files_only=True
)

# 2. Load the 3D CT Volume
# Merlin expects raw NIfTI data, not 2D PNG slices.
nifti_path = r"D:\Steven Project\Liver Cancer\data\patient_01_phase_arterial.nii.gz"
print(f"Loading 3D volume from {nifti_path}...")

img = nib.load(nifti_path)
volume_data = img.get_fdata()

# 3. Prepare the Prompt
prompt = "Analyze this abdominal CT volume. Are there any focal liver lesions indicative of HCC?"

# 4. Process Inputs
inputs = processor(
    text=prompt, 
    images=volume_data, # Passing the 3D NumPy array directly
    return_tensors="pt"
).to("cuda")

# 5. Generate Response
print("Generating report...")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.1
    )

# 6. Decode and Print
response = processor.decode(outputs[0], skip_special_tokens=True)
print("\n=== MERLIN REPORT ===")
print(response)
```

## Step 4: How This Changes Your Project Architecture

If you switch your thesis to use Merlin, your `backend/core/llm_client.py` will have to change dramatically. 

### Current Pipeline (Ollama)
1. Backend creates 2D slice montage `.png`.
2. Backend converts `.png` to Base64 string.
3. Backend sends Base64 + Text to `http://localhost:11434/api/chat`.
4. Ollama returns text.

### New Pipeline (Merlin)
1. Backend identifies the path to the original `.nii.gz` file.
2. Backend executes the PyTorch script directly (or the PyTorch model stays resident in your FastAPI memory).
3. The model directly ingests the 3D array (no Base64 serialization).
4. The model returns text.

### Pros & Cons for your Thesis
* **Pro:** You are doing *true* 3D medical AI. You no longer have to worry about "did the montage capture the lesion correctly?" because the model looks at the whole scan.
* **Con:** It is computationally heavier. It requires writing a custom inference engine rather than relying on Ollama's highly optimized server. It may exceed your 8GB VRAM if the 3D context window is too large, requiring aggressive downsampling of the NIfTI files before feeding them to the model.
