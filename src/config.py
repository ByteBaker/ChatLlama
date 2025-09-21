"""Configuration for ChatLlama server."""

import os
from pathlib import Path

# Get the directory containing this config file
_config_dir = Path(__file__).parent
_model_path = _config_dir / "../model/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"

# Llama 3 8B GGUF Model configuration
LLAMA3_MODEL = {
    "path": str(_model_path.resolve()),
    "name": "Llama 3 8B Q4_K_M",
    "description": "Llama 3 8B Instruct, 4-bit quantized",
    "n_ctx": 8192,
    "n_gpu_layers": -1
}