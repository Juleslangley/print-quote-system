"""Shared pytest fixtures. Test DB setup via Alembic (no create_all)."""
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.core import db as db_module
from app.models.base import new_id
from app.models.user import User
from app.models.supplier import Supplier


def _get_test_database_url() -> str:
    """
    Test DB URL. Use TEST_DATABASE_URL if set. Otherwise use main DATABASE_URL.
    For a separate test DB (quote_test): set TEST_DATABASE_URL and ensure the DB
    has the base schema (alembic migrations assume users/suppliers/etc. exist).
    """
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    url = settings.DATABASE_URL
    url_lower = url.lower()
    if "sqlite" in url_lower and "memory" in url_lower:
        # :memory: can't be shared; use a temp file for tests
        test_path = Path(os.environ.get("TEST_DB_PATH", "/tmp/pqs_test.sqlite"))
        return f"sqlite+pysqlite:///{test_path}"
    return url


def _ensure_test_db_exists(url: str) -> None:
    """Create test database if it doesn't exist (Postgres only)."""
    from sqlalchemy.engine import make_url
    u = make_url(url)
    dbname = u.database
    if not dbname or "sqlite" in url.lower():
        return
    admin_url = u.set(database="postgres")
    admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        row = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}).fetchone()
        if not row:
            conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    admin_engine.dispose()


def _run_alembic_upgrade(url: str) -> None:
    """Run alembic upgrade head against the given URL."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def test_database_url():
    """Test database URL (quote_test for Postgres)."""
    return _get_test_database_url()


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """
    Engine for test database. Runs alembic upgrade head (no create_all).
    Uses main DATABASE_URL by default; use TEST_DATABASE_URL for a separate test DB.
    """
    url = test_database_url
    if "postgres" in url.lower() and url != settings.DATABASE_URL:
        _ensure_test_db_exists(url)
    _run_alembic_upgrade(url)
    engine = create_engine(
        url,
        pool_pre_ping=True,
        echo=os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true"),
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """SessionMaker bound to test engine."""
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(scope="session")
def use_test_db(test_database_url, test_engine, test_session_factory):
    """
    Patch app.core.db so API and fixtures share the same engine/session.
    Ensures fixture-created supplier/user rows are visible to API requests.
    """
    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = test_session_factory
    try:
        yield
    finally:
        db_module.engine = original_engine
        db_module.SessionLocal = original_session


@pytest.fixture
def db_session(test_session_factory, use_test_db):
    """Per-test session from the test DB (or main DB when TEST_DATABASE_URL not set)."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db(db_session):
    """Alias for db_session for tests that expect a 'db' fixture."""
    return db_session


@pytest.fixture
def supplier_id(db_session):
    """Create a supplier and return its id. Satisfies purchase_orders.supplier_id FK."""
    s = Supplier(
        id=new_id(),
        name=f"Test Supplier {new_id()}",
        active=True,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    yield s.id
    try:
        db_session.query(Supplier).filter(Supplier.id == s.id).delete(synchronize_session=False)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def test_user(db_session):
    """Create a user and return it. Satisfies files.uploaded_by and purchase_orders.created_by_user_id FKs."""
    u = User(
        id=new_id(),
        email=f"test-{new_id()}@local",
        password_hash="x",
        role="admin",
        active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    yield u
    try:
        db_session.query(User).filter(User.id == u.id).delete(synchronize_session=False)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def app_with_auth_bypass(test_user):
    """Override auth so API calls succeed; return test_user so File.uploaded_by FK is satisfied."""
    from app.main import app
    from app.api.permissions import require_admin, require_sales

    def _fake_admin():
        return test_user

    def _fake_sales():
        return test_user

    app.dependency_overrides[require_admin] = _fake_admin
    app.dependency_overrides[require_sales] = _fake_sales
    try:
        yield app
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(require_sales, None)
