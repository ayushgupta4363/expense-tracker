import datetime

from pydantic import BaseModel, EmailStr, Field

CATEGORIES = [
    "Food",
    "Transport",
    "Rent",
    "Shopping",
    "Bills",
    "Health",
    "Entertainment",
    "Other",
]


# ---------- auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str

    model_config = {"from_attributes": True}


# ---------- expenses ----------
class ExpenseCreate(BaseModel):
    amount: float = Field(gt=0)
    category: str
    description: str = ""
    date: datetime.date


class ExpenseOut(BaseModel):
    id: int
    amount: float
    category: str
    description: str
    date: datetime.date

    model_config = {"from_attributes": True}


class ParseRequest(BaseModel):
    text: str = Field(min_length=3, max_length=300)
