from fastapi import APIRouter, Depends

from app.common.result import Result
from app.dependencies.api_dp.book_api_dp import get_book_svc
from app.schemas import BookCreate, BookOut
from app.services.book_service import BookService

router = APIRouter(prefix="/api", tags=["book"])


@router.post("/users/{user_id}/books")
def create_book_for_user(
    user_id: int,
    data: BookCreate,
    svc: BookService = Depends(get_book_svc),
) -> Result:
    book = svc.create_book_for_user(user_id, data)
    return Result.success(BookOut.model_validate(book))


@router.get("/books")
def list_books(
    user_id: int | None = None,
    svc: BookService = Depends(get_book_svc),
) -> Result:
    books = svc.list_books(user_id=user_id)
    return Result.success([BookOut.model_validate(b) for b in books])
