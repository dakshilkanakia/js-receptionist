import os

# Point the app at a throwaway test database before anything imports app.config.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://js:js@localhost:5432/js_receptionist_test")
os.environ["DB_NULLPOOL"] = "1"
os.environ["OWNER_EMAIL"] = "owner@test.local"
os.environ["OWNER_PASSWORD"] = "test-password"
