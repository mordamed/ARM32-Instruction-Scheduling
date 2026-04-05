FROM ubuntu:22.04

# Avoid interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc-arm-none-eabi \
    gdb-multiarch \
    qemu-user \
    qemu-user-static \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ── Install project as editable package ───────────────────────────────────────
COPY . .
RUN pip3 install --no-cache-dir -e .

# ── Convenience aliases ───────────────────────────────────────────────────────
RUN echo "alias arm-gdb='gdb-multiarch -q'" >> ~/.bashrc

# ── Default: run the full benchmark ───────────────────────────────────────────
CMD ["python3", "experiments/run_all.py"]