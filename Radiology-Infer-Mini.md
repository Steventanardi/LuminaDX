# How to Run Radiology-Infer-Mini 100% Locally

Radiology-Infer-Mini (a 2B parameter model based on Qwen2-VL) is highly optimized for medical imaging. Because community members have converted it into the `.gguf` format, you can run it entirely offline using Ollama or LM Studio.

Here are the step-by-step instructions.

---

## Option 1: Running via Ollama (Best for your current pipeline)

Since your `llm_client.py` already talks to the Ollama API, this is the most seamless way to integrate the model.

### Step 1: Download the GGUF File
1. Go to Hugging Face and search for the quantized version of the model. 
   *(Example repository: `cgus/Radiology-Infer-Mini-iMat-GGUF` or search "Radiology-Infer-Mini GGUF")*
2. Download the specific `.gguf` file that fits your hardware. For an RTX 4070 (8GB VRAM), download a **Q4_K_M** or **Q6_K** version. It should be roughly 1.5 GB to 2 GB in size.
3. Save the downloaded `.gguf` file to a folder on your computer (e.g., `C:\models\radiology-infer-mini-q4.gguf`).

### Step 2: Create a Modelfile
1. Open Notepad or any text editor.
2. Type the following two lines (make sure the path matches where you saved the file):
   ```text
   FROM "C:\models\radiology-infer-mini-q4.gguf"
   TEMPLATE """{{ if .System }}<|im_start|>system
   {{ .System }}<|im_end|>
   {{ end }}{{ if .Prompt }}<|im_start|>user
   {{ .Prompt }}<|im_end|>
   {{ end }}<|im_start|>assistant
   """
   ```
   *(Note: The template above matches the standard ChatML format used by Qwen2).*
3. Save this text file in the same directory as your model and name it `Modelfile` (no file extension like `.txt`).

### Step 3: Import into Ollama
Open PowerShell or Command Prompt, navigate to the folder where you saved the files, and run:
```powershell
cd C:\models
ollama create rad-mini -f Modelfile
```
Ollama will process the weights and create a local model named `rad-mini`.

### Step 4: Use it in your Project
Update your `backend/.env` file to point to the new model:
```env
LLM_MODEL=rad-mini
```
Restart your backend. Your pipeline will now use Radiology-Infer-Mini.

---

## Option 2: Running via LM Studio (Best for manual testing)

If you prefer a graphical interface to test prompts and images manually before writing code, LM Studio is the best choice.

### Step 1: Search and Download inside LM Studio
1. Open LM Studio.
2. In the top search bar, type: `Radiology Infer Mini GGUF`.
3. Look for a repository (like `cgus/Radiology-Infer-Mini-iMat-GGUF`).
4. In the right-hand panel, find a **Q4_K_M** or **Q6_K** file and click **Download**.

### Step 2: Load the Model
1. Go to the **Chat** tab (the speech bubble icon on the left).
2. Use the top dropdown menu to select the model you just downloaded.
3. LM Studio will load the model into your RTX 4070 VRAM (you will see the RAM usage spike at the bottom).

### Step 3: Test with an Image
1. Click the **attachment (paperclip) icon** next to the chat box and upload one of your CT liver slice montages.
2. Type your prompt (e.g., "Analyze this abdominal CT scan and identify any lesions.") and press Enter.

*(Note: LM Studio also provides a local OpenAI-compatible server. You can route your `llm_client.py` to LM Studio instead of Ollama by changing the `base_url` in your code to `http://localhost:1234/v1` instead of Ollama's port).*
