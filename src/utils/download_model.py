#!/usr/bin/env python3
"""Download Llama 3 8B GGUF model from Hugging Face"""

from pathlib import Path
from huggingface_hub import hf_hub_download

def main():
    script_dir = Path(__file__).parent
    model_dir = script_dir / "../../model"
    model_dir.mkdir(exist_ok=True)

    print("Downloading Llama 3 8B Q4_K_M model...")

    hf_hub_download(
        repo_id="bartowski/Meta-Llama-3-8B-Instruct-GGUF",
        filename="Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        local_dir=model_dir
    )

    print("Download complete!")

if __name__ == "__main__":
    main()