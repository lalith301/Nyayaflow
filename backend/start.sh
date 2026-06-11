#!/usr/bin/env bash
set -e

# Pre-download model to cache before starting server
# This runs once and caches to /opt/render/.cache/huggingface
echo "[startup] Downloading embedding model..."
python3 -c "
from sentence_transformers import SentenceTransformer
import os
os.environ['TRANSFORMERS_CACHE'] = '/opt/render/.cache/huggingface'
os.environ['HF_HOME'] = '/opt/render/.cache/huggingface'
m = SentenceTransformer('BAAI/bge-small-en-v1.5')
print('[startup] Model ready.')
"

echo "[startup] Starting gunicorn..."
exec gunicorn app:app \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers 1 \
  --timeout 300 \
  --keep-alive 5 \
  --preload