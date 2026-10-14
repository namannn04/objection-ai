from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Case
from app.services import case_service as cs


async def get_case_or_404(s: AsyncSession, ref: str) -> Case:
    case = await cs.load_case(s, ref)
    if not case:
        raise HTTPException(404, "case not found")
    return case
