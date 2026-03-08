from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services import auth_service


def get_db():
    """Yield a scoped SQLAlchemy session for request handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """Enforce auth for protected routes."""
    context = auth_service.require_authenticated_context(db=db, request=request)
    request.state.current_user = context.user
    request.state.auth_method = context.method
