#!/bin/bash
# Загрузка Markdown в RAG: docs/ и parsing_agent/data/raw/ (через /app/parsing_raw)
# Запуск из корня репозитория: ./scripts/load_docs_docker.sh

set -e

echo "Загружаю документы в RAG базу знаний..."

docker compose exec backend python -c "
import hashlib, re, os, sys
from pathlib import Path

import chromadb
from openai import OpenAI

api_key = os.getenv('OPENAI_API_KEY', '')
if not api_key:
    print('ERROR: OPENAI_API_KEY not set')
    sys.exit(1)

openai_client = OpenAI(api_key=api_key)

chroma_host = (os.getenv('CHROMA_HOST') or '').strip()
chroma_port = int(os.getenv('CHROMA_PORT', '8000'))
chroma_data = os.getenv('CHROMA_DATA_DIR', '/app/chroma_data')
collection_name = os.getenv('CHROMA_COLLECTION', 'ai_sale_knowledge')

if chroma_host:
    try:
        chroma = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        chroma.heartbeat()
    except Exception as e:
        print(f'Chroma HttpClient failed ({e}), using PersistentClient at {chroma_data}')
        chroma = chromadb.PersistentClient(path=chroma_data)
else:
    chroma = chromadb.PersistentClient(path=chroma_data)

collection = chroma.get_or_create_collection(
    name=collection_name,
    metadata={'hnsw:space': 'cosine'},
)
print(f'Collection has {collection.count()} docs before loading')

scan_dirs = [
    (Path('/app/docs'), '*', 'docs'),
    (Path('/app/parsing_raw'), '*.md', 'parsing_raw'),
]
all_chunks = []

for base_dir, pattern, label in scan_dirs:
    if not base_dir.is_dir():
        print(f'Skip (no dir): {base_dir}')
        continue
    for filepath in sorted(base_dir.glob(pattern)):
        if filepath.name.startswith('.') or filepath.is_dir() or not filepath.is_file():
            continue
        text = filepath.read_text(encoding='utf-8')
        print(f'Processing [{label}]: {filepath.name} ({len(text)} chars)')

        sections = re.split(r'\n(?=#{1,3}\s)', text)
        current_h2 = ''
        default_cat = 'knowledge' if label == 'parsing_raw' else 'company_info'
        for section in sections:
            section = section.strip()
            if not section:
                continue
            h2 = re.match(r'^##\s+(.+)', section)
            if h2:
                current_h2 = h2.group(1).strip().strip('*')

            parts = [section] if len(section) <= 1200 else []
            if not parts:
                buf, cur = [], ''
                for p in section.split('\n\n'):
                    if len(cur) + len(p) > 1200 and cur:
                        buf.append(cur.strip())
                        cur = p
                    else:
                        cur = cur + '\n\n' + p if cur else p
                if cur.strip():
                    buf.append(cur.strip())
                parts = buf

            for part in parts:
                cid = hashlib.md5(part.encode()).hexdigest()[:12]
                all_chunks.append({
                    'id': cid,
                    'text': part,
                    'metadata': {
                        'source': f'{label}/{filepath.name}',
                        'url': 'https://gkproject.ru',
                        'title': current_h2 or filepath.stem,
                        'category': current_h2 or default_cat,
                    },
                })

seen = set()
unique = []
for c in all_chunks:
    if c['id'] not in seen:
        seen.add(c['id'])
        unique.append(c)

print(f'Total: {len(unique)} unique chunks')

model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
for i in range(0, len(unique), 50):
    batch = unique[i:i+50]
    resp = openai_client.embeddings.create(model=model, input=[c['text'] for c in batch])
    embeddings = [item.embedding for item in resp.data]
    collection.upsert(
        ids=[c['id'] for c in batch],
        documents=[c['text'] for c in batch],
        embeddings=embeddings,
        metadatas=[c['metadata'] for c in batch],
    )
    print(f'  Batch {i+1}-{i+len(batch)} loaded')

print(f'Done! Collection now has {collection.count()} docs')
"
