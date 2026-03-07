from app.db.session import SessionLocal


def get_db():
    """Yield a scoped SQLAlchemy session for request handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth_placeholder() -> None:
    """Temporary auth dependency placeholder until real authentication is implemented."""
    return None
