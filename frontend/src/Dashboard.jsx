import { useEffect, useState } from "react";
import { api } from "./api.js";

function today() {
  return new Date().toISOString().slice(0, 10);
}

const emptyForm = { amount: "", category: "Food", description: "", date: today() };

function Dashboard({ onLogout }) {
  const [user, setUser] = useState(null);
  const [categories, setCategories] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState(null);

  const [aiText, setAiText] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  // runs once when the page opens
  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    try {
      setUser(await api("/auth/me"));
      setCategories(await api("/categories"));
      loadExpenses();
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadExpenses() {
    setExpenses(await api("/expenses"));
    setSummary(await api("/summary"));
  }

  // ask the AI to read the text and fill the form
  async function handleParse() {
    setError("");
    setAiLoading(true);
    try {
      const data = await api("/expenses/parse", {
        method: "POST",
        body: JSON.stringify({ text: aiText }),
      });
      setForm({
        amount: data.amount,
        category: data.category,
        description: data.description,
        date: data.date,
      });
    } catch (err) {
      setError(err.message);
    }
    setAiLoading(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/expenses", {
        method: "POST",
        body: JSON.stringify({ ...form, amount: Number(form.amount) }),
      });
      setForm(emptyForm);
      setAiText("");
      loadExpenses();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    try {
      await api("/expenses/" + id, { method: "DELETE" });
      loadExpenses();
    } catch (err) {
      setError(err.message);
    }
  }

  function changeForm(field, value) {
    setForm({ ...form, [field]: value });
  }

  const biggest = summary && summary.by_category.length > 0 ? summary.by_category[0].total : 1;

  return (
    <div className="page">
      <header className="top">
        <h1>Expense Tracker</h1>
        <div>
          <span className="muted">{user ? user.name || user.email : ""}</span>
          <button className="small" onClick={onLogout}>Logout</button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="grid">
        <div className="card">
          <h2>Add expense</h2>

          <div className="row">
            <input
              placeholder='Type like "spent 250 on lunch yesterday"'
              value={aiText}
              onChange={(e) => setAiText(e.target.value)}
            />
            <button type="button" onClick={handleParse} disabled={aiLoading || aiText.length < 3}>
              {aiLoading ? "Reading..." : "Parse with AI"}
            </button>
          </div>
          <p className="muted">Check the details below, then press Save.</p>

          <form onSubmit={handleSave}>
            <input
              type="number"
              step="0.01"
              placeholder="Amount"
              value={form.amount}
              onChange={(e) => changeForm("amount", e.target.value)}
              required
            />
            <select value={form.category} onChange={(e) => changeForm("category", e.target.value)}>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <input
              placeholder="Description"
              value={form.description}
              onChange={(e) => changeForm("description", e.target.value)}
            />
            <input
              type="date"
              value={form.date}
              onChange={(e) => changeForm("date", e.target.value)}
              required
            />
            <button type="submit">Save</button>
          </form>
        </div>

        <div className="card">
          <h2>This month</h2>
          {summary && (
            <>
              <p className="total">Rs. {summary.total}</p>
              {summary.by_category.length === 0 && <p className="muted">No expenses yet.</p>}
              {summary.by_category.map((row) => (
                <div key={row.category} className="bar-row">
                  <div className="bar-label">
                    <span>{row.category}</span>
                    <span>Rs. {row.total}</span>
                  </div>
                  <div className="bar-bg">
                    <div className="bar" style={{ width: (row.total / biggest) * 100 + "%" }} />
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h2>All expenses</h2>
        {expenses.length === 0 && <p className="muted">Nothing here yet. Add your first expense above.</p>}
        {expenses.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Category</th>
                <th>Description</th>
                <th className="right">Amount</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((e) => (
                <tr key={e.id}>
                  <td>{e.date}</td>
                  <td>{e.category}</td>
                  <td>{e.description}</td>
                  <td className="right">Rs. {e.amount}</td>
                  <td className="right">
                    <button className="small danger" onClick={() => handleDelete(e.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
