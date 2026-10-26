# Expense Tracker

A simple multi-user expense tracker.

- **Backend:** Python, FastAPI, SQLite (SQLAlchemy)
- **Frontend:** React (Vite)
- **Login:** email + password (JWT) and "Sign in with Google"
- **AI:** type "spent 250 on lunch yesterday" and the Claude API fills in the form

```
expense-tracker/
├── backend/
│   ├── main.py          # all API routes
│   ├── auth.py          # password hashing + JWT
│   ├── models.py        # database tables (User, Expense)
│   ├── schemas.py       # request/response shapes + category list
│   ├── llm.py           # the only file that calls the AI
│   ├── database.py      # SQLite connection
│   ├── config.py        # reads .env
│   └── tests/test_api.py
└── frontend/
    └── src/
        ├── App.jsx        # shows Login or Dashboard
        ├── Login.jsx      # login / register / Google button
        ├── Dashboard.jsx  # add expense, summary, list
        └── api.js         # fetch helper that adds the token
```

## 1. Run the backend

You need Python 3.10 or newer.

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux
pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Mac / Linux
```

Open `backend/.env` and fill in:

- `SECRET_KEY`: make one with `python -c "import secrets; print(secrets.token_hex(32))"`
- `ANTHROPIC_API_KEY`: from https://console.anthropic.com (only needed for "Parse with AI")
- `GOOGLE_CLIENT_ID`: see section 3 (optional)

Start the server:

```bash
uvicorn main:app --reload
```

Open http://localhost:8000/docs to see and try every endpoint. The database file `expenses.db` is created automatically.

## 2. Run the frontend

You need Node.js 18 or newer. Use a second terminal.

```bash
cd frontend
npm install
copy .env.example .env         # Windows  (cp on Mac / Linux)
npm run dev
```

Open http://localhost:5173, register an account, and add an expense.

## 3. Set up "Sign in with Google" (optional)

1. Go to https://console.cloud.google.com and create a project.
2. Open **APIs & Services > OAuth consent screen**. Choose "External", fill in the app name and your email, and add your own Gmail as a **test user**.
3. Open **APIs & Services > Credentials > Create credentials > OAuth client ID**.
4. Application type: **Web application**.
5. Under **Authorized JavaScript origins** add `http://localhost:5173`.
6. Copy the **Client ID** and paste the same value into:
   - `backend/.env` as `GOOGLE_CLIENT_ID`
   - `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`
7. Restart both servers. The Google button now appears on the login page.

If you leave the client ID empty, the Google button is simply hidden and email/password login still works.

## How login works

1. User registers or logs in. The backend checks the password and returns a **JWT token**.
2. React saves the token in `localStorage` and sends it with every request as `Authorization: Bearer <token>`.
3. `get_current_user` in `auth.py` reads the token and finds the user. Any route that uses it is login-only.
4. Google login: Google gives React a signed `credential`. React sends it to `POST /auth/google`. The backend verifies it with Google, creates the user if new, and returns the same kind of JWT.

## How multiple users work

Every expense row has a `user_id`, and every query in `main.py` filters by the logged-in user's id. The test `test_users_cannot_see_each_others_data` checks that one user cannot see or delete another user's expenses.

## How the AI part works

1. You type text and press **Parse with AI**.
2. `POST /expenses/parse` sends it to Claude (`llm.py`) and gets back amount, category, description and date.
3. The backend cleans the answer (unknown category becomes "Other", missing date becomes today).
4. The form is filled in so you can **check and fix it**, then press Save. Nothing is saved until you do.

## Run the tests

```bash
cd backend
pytest
```

## Before you put this online

- Use a long random `SECRET_KEY` and keep `.env` out of git (it is already in `.gitignore`).
- Set `FRONTEND_URL` to your real website address and use HTTPS.
- `localStorage` is simple but can be read by malicious scripts. A more secure setup uses httpOnly cookies.
- Add a rate limit on `/expenses/parse`, since every call costs money.
- Switch SQLite to PostgreSQL if many people will use it at once (change `DATABASE_URL`).

## Ideas for next steps

- Edit an expense
- Monthly budgets with alerts
- A chat box: "how much did I spend on food last month?" (LLM tool calling over your own query functions)
- Charts with Recharts
- Alembic for database migrations
