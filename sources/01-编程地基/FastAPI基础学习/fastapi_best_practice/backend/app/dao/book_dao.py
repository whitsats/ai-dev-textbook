from sqlalchemy.orm import Session

from app.models import Book
from app.schemas import BookCreate


class BookDAO:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_book_for_user(self, user_id: int, data: BookCreate) -> Book:
        book = Book(title=data.title, owner_id=user_id)
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book

    def list_books(self, user_id: int | None = None) -> list[Book]:
        q = self.db.query(Book).order_by(Book.id.desc())
        if user_id is not None:
            q = q.filter(Book.owner_id == user_id)
        return q.all()
