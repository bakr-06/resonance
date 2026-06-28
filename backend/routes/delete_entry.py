import uuid
from http import HTTPStatus

from fastapi import HTTPException, Response

from db.database import DbSession
from db.models import Entry

from . import router


@router.delete("/entries/{entry_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_entry(
        entry_id: uuid.UUID,
        db_session: DbSession,
) -> Response:
    entry = await db_session.get(Entry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )

    await db_session.delete(entry)
    await db_session.commit()

    return Response(status_code=HTTPStatus.NO_CONTENT)
