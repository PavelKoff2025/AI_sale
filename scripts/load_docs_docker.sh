#!/bin/bash
# Загрузка документов из docs/ в RAG базу через Docker
# Запуск: cd AI_sale && ./scripts/load_docs_docker.sh

set -e

echo "Загружаю документы в RAG базу знаний..."

docker compose exec backend python -c "
import hashlib, re, os, sys
from pathlib import Path

# Инициализация
import chromadb
from openai import OpenAI

api_key = os.getenv('OPENAI_API_KEY', '')
if not api_key:
    print('ERROR: OPENAI_API_KEY not set')
    sys.exit(1)

openai_client = OpenAI(api_key=api_key)
chroma = chromadb.HttpClient(host=os.getenv('CHROMA_HOST','chromadb'), port=int(os.getenv('CHROMA_PORT','8000')))
collection = chroma.get_or_create_collection(
    name=os.getenv('CHROMA_COLLECTION','ai_sale_knowledge'),
    metadata={'hnsw:space': 'cosine'},
)
print(f'Collection has {collection.count()} docs before loading')

# Чтение файлов
docs_dir = Path('/app/docs')
all_chunks = []

for filepath in sorted(docs_dir.glob('*')):
    if filepath.name.startswith('.') or filepath.is_dir():
        continue
    text = filepath.read_text(encoding='utf-8')
    print(f'Processing: {filepath.name} ({len(text)} chars)')

    sections = re.split(r'\n(?=#{1,3}\s)', text)
    current_h2 = ''
    for section in sections:
        section = section.strip()
        if not section:
            continue
        h2 = re.match(r'^##\s+(.+)', section)
        if h2:
            current_h2 = h2.group(1).strip().strip('*')

        # Split long sections
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
                    'source': f'docs/{filepath.name}',
                    'url': 'https://gkproject.ru',
                    'title': current_h2 or filepath.name,
                    'category': current_h2 or 'company_info',
                },
            })

# Dedup
seen = set()
unique = []
for c in all_chunks:
    if c['id'] not in seen:
        seen.add(c['id'])
        unique.append(c)

print(f'Total: {len(unique)} unique chunks')

# Load
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
