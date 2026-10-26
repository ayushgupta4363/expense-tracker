import os
import sys
import tempfile

# use a throwaway database for tests (must be set before importing the app)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

client = TestClient(main.app)


def register(email):
    res = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert res.status_code == 200
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def test_register_login_and_me():
    register("a@example.com")
    res = client.post("/auth/login", json={"email": "a@example.com", "password": "secret123"})
    assert res.status_code == 200
    headers = {"Authorization": "Bearer " + res.json()["access_token"]}
    assert client.get("/auth/me", headers=headers).json()["email"] == "a@example.com"


def test_wrong_password_and_duplicate_email():
    register("b@example.com")
    bad = client.post("/auth/login", json={"email": "b@example.com", "password": "nope-nope"})
    assert bad.status_code == 401
    dup = client.post("/auth/register", json={"email": "b@example.com", "password": "secret123"})
    assert dup.status_code == 400


def test_needs_login():
    assert client.get("/expenses").status_code == 401
    bad = client.get("/expenses", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_users_cannot_see_each_others_data():
    alice = register("alice@example.com")
    bob = register("bob@example.com")

    res = client.post(
        "/expenses",
        headers=alice,
        json={"amount": 120.5, "category": "Food", "description": "lunch", "date": "2026-10-20"},
    )
    assert res.status_code == 200
    alice_expense_id = res.json()["id"]

    # alice sees it, bob does not
    assert len(client.get("/expenses", headers=alice).json()) == 1
    assert client.get("/expenses", headers=bob).json() == []
    assert client.get("/summary?month=2026-10", headers=bob).json()["total"] == 0

    # bob cannot delete alice's expense
    assert client.delete(f"/expenses/{alice_expense_id}", headers=bob).status_code == 404
    assert len(client.get("/expenses", headers=alice).json()) == 1

    # alice can
    assert client.delete(f"/expenses/{alice_expense_id}", headers=alice).status_code == 200
    assert client.get("/expenses", headers=alice).json() == []


def test_summary_totals():
    user = register("sum@example.com")
    for amount, category in [(100, "Food"), (50, "Food"), (200, "Transport")]:
        client.post(
            "/expenses",
            headers=user,
            json={"amount": amount, "category": category, "date": "2026-09-10"},
        )
    data = client.get("/summary?month=2026-09", headers=user).json()
    assert data["total"] == 350
    assert data["by_category"][0] == {"category": "Transport", "total": 200}


def test_invalid_expense_is_rejected():
    user = register("bad@example.com")
    res = client.post(
        "/expenses", headers=user, json={"amount": -5, "category": "Food", "date": "2026-10-01"}
    )
    assert res.status_code == 422
    res = client.post(
        "/expenses", headers=user, json={"amount": 5, "category": "Made up", "date": "2026-10-01"}
    )
    assert res.status_code == 400


def test_parse_with_fake_llm(monkeypatch):
    user = register("llm@example.com")

    # fake AI answer: unknown category and no date -> should become "Other" and today
    monkeypatch.setattr(main, "parse_expense_text", lambda text: {"amount": "250", "category": "Snacks"})
    res = client.post("/expenses/parse", headers=user, json={"text": "spent 250 on chips"})
    assert res.status_code == 200
    assert res.json()["amount"] == 250
    assert res.json()["category"] == "Other"

    # fake AI answer that is garbage -> friendly error
    monkeypatch.setattr(main, "parse_expense_text", lambda text: {"foo": "bar"})
    res = client.post("/expenses/parse", headers=user, json={"text": "hello there"})
    assert res.status_code == 422


def test_parse_needs_login():
    assert client.post("/expenses/parse", json={"text": "spent 10"}).status_code == 401
