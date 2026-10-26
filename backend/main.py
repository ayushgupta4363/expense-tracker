from datetime import date

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from auth import hash_password, verify_password, create_token, get_current_user
from config import FRONTEND_URL, GOOGLE_CLIENT_ID
from database import Base, engine, get_db
from llm import parse_expense_text

# creates the tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Expense Tracker")

# lets the React app (different port) call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Expense Tracker API is running"}


@app.get("/categories")
def get_categories():
    return schemas.CATEGORIES


# ---------------- AUTH ----------------
@app.post("/auth/register", response_model=schemas.TokenResponse)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"access_token": create_token(user.id)}


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email.lower()).first()

    if user is None or user.password_hash is None:
        # same message for both cases so nobody can guess which emails exist
        raise HTTPException(status_code=401, detail="Wrong email or password")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    return {"access_token": create_token(user.id)}


# Google login: the React app gets a Google token (credential) and sends it here.
# We check it with Google, then give back our own JWT.
@app.post("/auth/google", response_model=schemas.TokenResponse)
def google_login(body: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google login is not set up")

    try:
        info = id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified")

    email = info["email"].lower()
    user = db.query(models.User).filter(models.User.email == email).first()

    # first time with Google -> create the account
    if user is None:
        user = models.User(email=email, name=info.get("name", ""))
        db.add(user)
        db.commit()
        db.refresh(user)

    return {"access_token": create_token(user.id)}


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


# ---------------- EXPENSES ----------------
# Every query below filters by user.id, so users only ever see their own data.
@app.get("/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return (
        db.query(models.Expense)
        .filter(models.Expense.user_id == user.id)
        .order_by(models.Expense.date.desc(), models.Expense.id.desc())
        .all()
    )


@app.post("/expenses", response_model=schemas.ExpenseOut)
def add_expense(
    body: schemas.ExpenseCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.category not in schemas.CATEGORIES:
        raise HTTPException(status_code=400, detail="Unknown category")

    expense = models.Expense(
        user_id=user.id,
        amount=body.amount,
        category=body.category,
        description=body.description,
        date=body.date,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = (
        db.query(models.Expense)
        .filter(models.Expense.id == expense_id, models.Expense.user_id == user.id)
        .first()
    )
    # if it belongs to someone else we also say "not found"
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return {"message": "Deleted"}


# Uses the LLM to read text. It does NOT save anything:
# the React app shows the result so the user can fix it, then calls POST /expenses.
@app.post("/expenses/parse", response_model=schemas.ExpenseCreate)
def parse_expense(
    body: schemas.ParseRequest, user: models.User = Depends(get_current_user)
):
    try:
        data = parse_expense_text(body.text)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(status_code=502, detail="AI service failed. Try again.")

    # clean up the AI answer before trusting it
    if data.get("category") not in schemas.CATEGORIES:
        data["category"] = "Other"
    if not data.get("date"):
        data["date"] = str(date.today())

    try:
        return schemas.ExpenseCreate(**data)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail="Could not understand that. Try: 'spent 250 on lunch'",
        )


# ---------------- SUMMARY ----------------
# total spent per category for one month, e.g. /summary?month=2026-10
@app.get("/summary")
def summary(
    month: str = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    try:
        if month:
            year, mon = [int(x) for x in month.split("-")]
        else:
            year, mon = today.year, today.month
        start = date(year, mon, 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Month must look like 2026-10")

    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)

    rows = (
        db.query(models.Expense.category, func.sum(models.Expense.amount))
        .filter(
            models.Expense.user_id == user.id,
            models.Expense.date >= start,
            models.Expense.date < end,
        )
        .group_by(models.Expense.category)
        .all()
    )

    by_category = [{"category": c, "total": round(t, 2)} for c, t in rows]
    by_category.sort(key=lambda r: r["total"], reverse=True)

    return {
        "month": f"{year}-{mon:02d}",
        "total": round(sum(r["total"] for r in by_category), 2),
        "by_category": by_category,
    }
