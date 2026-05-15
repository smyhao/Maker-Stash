from typing import Generic, TypeVar

from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self.db = db
        self.model = model

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        return obj
