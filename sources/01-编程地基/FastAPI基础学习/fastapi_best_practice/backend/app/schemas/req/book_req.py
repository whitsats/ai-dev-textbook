from pydantic import BaseModel


class BookCreate(BaseModel):
    title: str
