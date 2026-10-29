import pytest

from app.config import _async_db_url


@pytest.mark.parametrize("raw", [
    "postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db",
])
def test_db_url_normalized(raw):
    assert _async_db_url(raw) == "postgresql+asyncpg://u:p@h:5432/db"
