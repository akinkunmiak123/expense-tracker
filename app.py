import csv
import io
import math
import os
from datetime import date, datetime

import psycopg
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, Response
)
from psycopg.rows import dict_row

load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")

app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY is not set.")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Other"]


def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            amount NUMERIC(12, 2) NOT NULL,
            category TEXT NOT NULL,
            date DATE NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# Runs on every cold start. Safe because of IF NOT EXISTS.
init_db()


def build_filters(args):
    """Turn ?month=YYYY-MM&category=Food into a SQL WHERE clause and its parameters."""
    month = args.get("month", "").strip()
    category = args.get("category", "").strip()

    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        month = ""
    if category not in CATEGORIES:
        category = ""

    clauses, params = [], []
    if month:
        clauses.append("to_char(date, 'YYYY-MM') = %s")
        params.append(month)
    if category:
        clauses.append("category = %s")
        params.append(category)

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params, month, category


def parse_expense_form(form):
    """Validate form data. Returns ((amount, category, date), None) or (None, error_message)."""
    amount_raw = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    expense_date = form.get("date", "").strip()

    try:
        amount = float(amount_raw)
    except ValueError:
        return None, "Amount must be a number."

    if not math.isfinite(amount) or amount <= 0:
        return None, "Amount must be greater than zero."

    if category not in CATEGORIES:
        return None, "Please choose a valid category."

    try:
        parsed_date = datetime.strptime(expense_date, "%Y-%m-%d").date()
    except ValueError:
        return None, "Please enter a valid date."

    return (round(amount, 2), category, parsed_date), None


@app.route("/")
def index():
    today = date.today().isoformat()
    where, params, month, category = build_filters(request.args)

    conn = get_db()

    expenses = conn.execute(
        f"SELECT id, amount, category, date FROM expenses {where} ORDER BY date DESC, id DESC",
        params,
    ).fetchall()

    total = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS total FROM expenses {where}",
        params,
    ).fetchone()["total"]

    by_category = conn.execute(
        f"""
        SELECT category, SUM(amount) AS total
        FROM expenses {where}
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        today=today,
        expenses=expenses,
        total=total,
        by_category=by_category,
        categories=CATEGORIES,
        month=month,
        category=category,
    )


@app.route("/api/summary")
def api_summary():
    where, params, _, _ = build_filters(request.args)

    conn = get_db()
    rows = conn.execute(
        f"""
        SELECT category, SUM(amount) AS total
        FROM expenses {where}
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    ).fetchall()
    conn.close()

    return jsonify(
        labels=[row["category"] for row in rows],
        values=[float(row["total"]) for row in rows],
    )


@app.route("/api/monthly")
def api_monthly():
    _, _, _, category = build_filters(request.args)

    where = "WHERE category = %s" if category else ""
    params = [category] if category else []

    conn = get_db()
    rows = conn.execute(
        f"""
        SELECT to_char(date, 'YYYY-MM') AS month, SUM(amount) AS total
        FROM expenses {where}
        GROUP BY month
        ORDER BY month ASC
        """,
        params,
    ).fetchall()
    conn.close()

    return jsonify(
        labels=[row["month"] for row in rows],
        values=[float(row["total"]) for row in rows],
    )


@app.route("/add", methods=["POST"])
def add_expense():
    data, error = parse_expense_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (amount, category, date) VALUES (%s, %s, %s)", data
    )
    conn.commit()
    conn.close()

    flash("Expense added.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    conn.close()

    flash("Expense deleted.", "danger")
    return redirect(url_for("index"))


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    conn = get_db()
    expense = conn.execute(
        "SELECT id, amount, category, date FROM expenses WHERE id = %s",
        (expense_id,),
    ).fetchone()

    if expense is None:
        conn.close()
        flash("Expense not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, error = parse_expense_form(request.form)
        if error:
            conn.close()
            flash(error, "error")
            return redirect(url_for("edit_expense", expense_id=expense_id))

        conn.execute(
            "UPDATE expenses SET amount = %s, category = %s, date = %s WHERE id = %s",
            (*data, expense_id),
        )
        conn.commit()
        conn.close()

        flash("Expense updated.", "success")
        return redirect(url_for("index"))

    conn.close()
    return render_template("edit.html", expense=expense, categories=CATEGORIES)


@app.route("/export")
def export_csv():
    where, params, month, category = build_filters(request.args)

    conn = get_db()
    rows = conn.execute(
        f"SELECT date, category, amount FROM expenses {where} ORDER BY date DESC, id DESC",
        params,
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Amount"])
    for row in rows:
        writer.writerow([row["date"].isoformat(), row["category"], f"{row['amount']:.2f}"])

    filename = "expenses"
    if month:
        filename += f"-{month}"
    if category:
        filename += f"-{category.lower()}"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
    )


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")