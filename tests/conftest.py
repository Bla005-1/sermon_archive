from __future__ import annotations

import os
from collections.abc import Generator
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, SMALLINT, TINYINT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import DefaultClause

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["DEBUG"] = "true"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost"


@compiles(BIGINT, "sqlite")
@compiles(INTEGER, "sqlite")
@compiles(SMALLINT, "sqlite")
@compiles(TINYINT, "sqlite")
def _compile_mysql_integer_for_sqlite(_type, _compiler, **_kw) -> str:
    return "INTEGER"


@compiles(LONGTEXT, "sqlite")
def _compile_mysql_longtext_for_sqlite(_type, _compiler, **_kw) -> str:
    return "TEXT"


from app.config import settings  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.dependencies import get_db, require_auth  # noqa: E402
from main import create_app  # noqa: E402


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    stripped_defaults = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            default_text = str(column.server_default.arg) if column.server_default else ""
            if "ON UPDATE" in default_text:
                stripped_defaults.append((column, column.server_default))
                column.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        for column, server_default in stripped_defaults:
            column.server_default = server_default


@pytest.fixture()
def client(db_session: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("SERMON_STORAGE_ROOT", str(tmp_path))
    settings.allowed_hosts = ["testserver", "localhost"]
    settings.cors_allowed_origins = ["http://testserver"]

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_require_auth(request: Request) -> None:
        request.state.current_user = None
        request.state.auth_method = "test"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
