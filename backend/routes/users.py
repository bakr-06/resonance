import uuid
from http import HTTPStatus

from fastapi import HTTPException, Response
from sqlalchemy import delete, select

from db.database import DbSession
from db.models import User
from schemas.users import CreateUserRequest, UpdateUserRequest, UserResponse

from . import user_router


@user_router.post("/users", response_model=UserResponse, status_code=HTTPStatus.CREATED)
async def create_user(
    db_session: DbSession,
    body: CreateUserRequest,
) -> UserResponse:
    user = User(
        name=body.name,
        occupation=body.occupation,
        social_status=body.social_status,
        date_of_birth=body.date_of_birth,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@user_router.get("/users", response_model=list[UserResponse])
async def list_users(db_session: DbSession) -> list[UserResponse]:
    result = await db_session.execute(select(User))
    users = result.scalars().all()
    return users


@user_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db_session: DbSession) -> UserResponse:
    user = await db_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"User {user_id} not found")
    return user


@user_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: uuid.UUID, db_session: DbSession, body: UpdateUserRequest) -> UserResponse:
    user = await db_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"User {user_id} not found")
    if body.name is not None:
        user.name = body.name
    if body.occupation is not None:
        user.occupation = body.occupation
    if body.social_status is not None:
        user.social_status = body.social_status
    if body.date_of_birth is not None:
        user.date_of_birth = body.date_of_birth
    await db_session.commit()
    await db_session.refresh(user)
    return user


@user_router.delete("/users/{user_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db_session: DbSession) -> Response:
    user = await db_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"User {user_id} not found")
    await db_session.delete(user)
    await db_session.commit()
    return Response(status_code=HTTPStatus.NO_CONTENT)


@user_router.delete("/users", status_code=HTTPStatus.NO_CONTENT)
async def delete_all_users(db_session: DbSession) -> Response:
    await db_session.execute(delete(User))
    await db_session.commit()
    return Response(status_code=HTTPStatus.NO_CONTENT)
