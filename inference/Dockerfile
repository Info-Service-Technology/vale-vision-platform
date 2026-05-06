FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instala PyTorch compatível com CUDA 12.4 da Tesla T4/driver atual
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip install --no-cache-dir \
    "typing-extensions>=4.10,<5" \
    --index-url https://pypi.org/simple

RUN pip install --no-cache-dir \
    torch==2.6.0+cu124 \
    torchvision==0.21.0+cu124 \
    torchaudio==2.6.0+cu124 \
    --extra-index-url https://download.pytorch.org/whl/cu124

# Instala o restante sem deixar requirements sobrescrever o torch
RUN grep -viE '^(torch|torchvision|torchaudio)([=<>~ ].*)?$' requirements.txt > /tmp/requirements-no-torch.txt \
    && pip install --no-cache-dir -r /tmp/requirements-no-torch.txt

COPY . .

CMD ["python", "worker.py"]