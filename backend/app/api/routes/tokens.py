from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import verify_token
from app.schemas.token import TokenCreate, TokenCreated, TokenRead, TokenUpdate
from app.services.token_service import TokenService

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("")
def list_tokens(current_token: str | None = None, db: Session = Depends(get_db)) -> dict:
    all_tokens = TokenService(db).list()
    result = []
    for t in all_tokens:
        data = TokenRead.model_validate(t).model_dump()
        data["is_current"] = bool(current_token and verify_token(current_token, t.token_hash))
        result.append(data)
    return ok({"tokens": result})


@router.post("")
def create_token(payload: TokenCreate, db: Session = Depends(get_db)) -> dict:
    api_token, plaintext = TokenService(db).create(payload)
    data = TokenCreated(
        **TokenRead.model_validate(api_token).model_dump(),
        token=plaintext,
    ).model_dump()
    return ok(data)


@router.patch("/{token_id}")
def update_token(token_id: int, payload: TokenUpdate, db: Session = Depends(get_db)) -> dict:
    api_token = TokenService(db).update(token_id, payload)
    return ok(TokenRead.model_validate(api_token).model_dump())


@router.delete("/{token_id}")
def delete_token(token_id: int, db: Session = Depends(get_db)) -> dict:
    TokenService(db).delete(token_id)
    return ok({"deleted": True})
