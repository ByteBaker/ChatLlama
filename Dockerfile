FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
RUN mkdir -p model
RUN mkdir -p data

# Download the Llama 3 8B model during build
RUN python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='bartowski/Meta-Llama-3-8B-Instruct-GGUF', filename='Meta-Llama-3-8B-Instruct-Q4_K_M.gguf', local_dir='/app/model')"

EXPOSE $PORT

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app/src

CMD ["python", "main.py"]