"""Dashboard API tests against a real Postgres test database (js_receptionist_test)."""

from contextlib import asynccontextmanager

import httpx
import pytest
from sqlalchemy import text

from app.db.models import Base, Call, CallbackRequest, UnansweredQuestion
from app.db.session import SessionLocal, engine
from app.facts.repo import seed_if_empty
from app.main import app


@pytest.fixture(autouse=True)
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        await seed_if_empty(s)
        call = Call(outcome="callback_requested")
        s.add(call)
        await s.flush()
        s.add(CallbackRequest(call_id=call.id, first_name="Test", phone_e164="+12125550100", reason="Order status"))
        s.add(UnansweredQuestion(call_id=call.id, question="Do you clean leather?"))
        await s.commit()
    yield


@asynccontextmanager
async def client(login: bool = True):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        if login:
            r = await c.post("/api/auth/login", json={"email": "owner@test.local", "password": "test-password"})
            assert r.status_code == 200
        yield c


@pytest.mark.parametrize("path", ["/api/calls", "/api/callbacks", "/api/unanswered", "/api/facts", "/api/stats"])
async def test_requires_login(path):
    async with client(login=False) as c:
        assert (await c.get(path)).status_code == 401


async def test_wrong_password_rejected():
    async with client(login=False) as c:
        r = await c.post("/api/auth/login", json={"email": "owner@test.local", "password": "nope"})
        assert r.status_code == 401


async def test_logout_ends_session():
    async with client() as c:
        await c.post("/api/auth/logout")
        assert (await c.get("/api/auth/me")).status_code == 401


async def test_edit_facts_creates_new_version_used_by_calls():
    async with client() as c:
        cur = (await c.get("/api/facts")).json()
        data = cur["data"]
        next(p for p in data["prices"] if p["id"] == "pants")["price"] = "14.00"
        r = await c.put("/api/facts", json={"data": data, "note": "Raise pants", "base_version_id": cur["version_id"]})
        assert r.status_code == 200
        assert r.json()["version_id"] == cur["version_id"] + 1

    from app.facts.repo import latest_facts
    async with SessionLocal() as s:
        _, facts = await latest_facts(s)
    assert str(facts.item("pants").price) == "14.00"


async def test_stale_edit_is_rejected():
    async with client() as c:
        cur = (await c.get("/api/facts")).json()
        ok = await c.put("/api/facts", json={"data": cur["data"], "base_version_id": cur["version_id"]})
        assert ok.status_code == 200
        stale = await c.put("/api/facts", json={"data": cur["data"], "base_version_id": cur["version_id"]})
        assert stale.status_code == 409


async def test_invalid_facts_rejected():
    async with client() as c:
        cur = (await c.get("/api/facts")).json()
        cur["data"]["prices"][0]["price"] = "-5"
        r = await c.put("/api/facts", json={"data": cur["data"], "base_version_id": cur["version_id"]})
        assert r.status_code == 422


async def test_answer_question_becomes_faq():
    async with client() as c:
        q = (await c.get("/api/unanswered")).json()[0]
        r = await c.post(f"/api/unanswered/{q['id']}/answer",
                         json={"answer": "Yes, leather starts at $60.", "question": "Do you clean leather jackets?"})
        assert r.status_code == 200 and r.json()["status"] == "answered"
        faqs = (await c.get("/api/facts")).json()["data"]["faqs"]
        assert faqs == [{"question": "Do you clean leather jackets?", "answer": "Yes, leather starts at $60.",
                         "unanswered_id": q["id"]}]
        assert (await c.get("/api/unanswered")).json() == []


async def test_restore_version():
    async with client() as c:
        v1 = (await c.get("/api/facts")).json()
        original = v1["data"]["turnaround"]
        data = {**v1["data"], "turnaround": "Changed"}
        await c.put("/api/facts", json={"data": data, "base_version_id": v1["version_id"]})
        r = await c.post(f"/api/facts/versions/{v1['version_id']}/restore")
        assert r.json()["data"]["turnaround"] == original
        assert len((await c.get("/api/facts/versions")).json()) == 3


async def test_mark_callback_done():
    async with client() as c:
        cb = (await c.get("/api/callbacks")).json()[0]
        r = await c.patch(f"/api/callbacks/{cb['id']}", json={"status": "done", "owner_note": "Called back"})
        assert r.json()["status"] == "done" and r.json()["handled_at"]
        assert (await c.get("/api/callbacks")).json() == []
        assert len((await c.get("/api/callbacks?status=done")).json()) == 1


async def test_call_detail_and_stats():
    async with client() as c:
        calls = (await c.get("/api/calls")).json()
        assert calls["total"] == 1
        detail = (await c.get(f"/api/calls/{calls['items'][0]['id']}")).json()
        assert detail["callbacks"][0]["first_name"] == "Test"
        stats = (await c.get("/api/stats")).json()
        assert stats["pending_callbacks"] == 1 and stats["open_questions"] == 1


async def test_dev_database_untouched():
    async with engine.connect() as conn:
        assert (await conn.execute(text("select current_database()"))).scalar() == "js_receptionist_test"


async def test_bare_owner_answer_rejected():
    async with client() as c:
        q = (await c.get("/api/unanswered")).json()[0]
        r = await c.post(f"/api/unanswered/{q['id']}/answer", json={"answer": "9"})
        assert r.status_code == 422 and "full sentence" in r.text
        cur = (await c.get("/api/facts")).json()
        cur["data"]["faqs"] = [{"question": "Leather?", "answer": "$9", "unanswered_id": None}]
        r = await c.put("/api/facts", json={"data": cur["data"], "base_version_id": cur["version_id"]})
        assert r.status_code == 422
