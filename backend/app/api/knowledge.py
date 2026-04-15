from fastapi import APIRouter, Depends

from app.core.dependencies import verify_admin_key
from app.rag.engine import rag_engine

router = APIRouter()


@router.get("/")
async def list_knowledge():
    stats = await rag_engine.get_collection_stats()
    return stats


@router.delete("/{chunk_id}", dependencies=[Depends(verify_admin_key)])
async def delete_chunk(chunk_id: str):
    await rag_engine.delete_chunk(chunk_id)
    return {"status": "deleted", "chunk_id": chunk_id}
