from sqlalchemy.orm import Session

from app.models import Book
from app.schemas import BookCreate


class BookService:
    def __init__(self, book_dao) -> None:
        self.book_dao = book_dao

    def create_book_for_user(self, user_id: int, data: BookCreate) -> Book:
        return self.book_dao.create_book_for_user(user_id, data)

    def list_books(self, user_id: int | None = None) -> list[Book]:
        return self.book_dao.list_books(user_id)
