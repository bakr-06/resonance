from fastapi import APIRouter

router = APIRouter()

from . import create_entry  # noqa: E402
from . import delete_entry  # noqa: E402
