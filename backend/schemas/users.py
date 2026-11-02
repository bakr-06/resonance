import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator

from db.models import SocialStatus


class UserBase(BaseModel):
    name: str
    social_status: SocialStatus
    date_of_birth: date

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("date_of_birth must be a past date")
        return value


class CreateUserRequest(UserBase):
    pass


class UpdateUserRequest(BaseModel):
    name: str | None = None
    social_status: SocialStatus | None = None
    date_of_birth: date | None = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        if value is None:
            return value
        if value >= date.today():
            raise ValueError("date_of_birth must be a past date")
        return value


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    social_status: SocialStatus
    date_of_birth: date
    created_at: datetime
    updated_at: datetime
