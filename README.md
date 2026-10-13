# Expense Tracker

A simple web app for recording and reviewing personal spending, built with Flask and Postgres.

**Live demo:** _add your Vercel URL here after deploying_

## Features

- Add, edit, and delete expenses (amount, category, date)
- Running total and spending breakdown by category
- Filter by month and category
- Doughnut chart of spending by category
- Bar chart of spending per month
- Export the current view to CSV
- Server-side validation with flash messages

## Tech stack

- **Backend:** Python, Flask
- **Database:** PostgreSQL (Neon) via psycopg
- **Frontend:** Jinja2 templates, CSS, Chart.js
- **Hosting:** Vercel

## Project structure

```
expense-tracker/
├── app.py              # Flask app: routes, validation, database code
├── requirements.txt    # Python dependencies
├── .env.example        # Names of the environment variables needed
├── public/
│   └── style.css       # Static assets (served from here on Vercel)
└── templates/
    ├── index.html      # Main page: form, filters, summary, charts, table
    └── edit.html       # Edit expense page
```

## Run it locally

You need Python 3.10+ and a PostgreSQL database (a free Neon project works well).

1. Clone the repository and open the folder:

```powershell
   git clone https://github.com/YOUR-USERNAME/expense-tracker.git
   cd expense-tracker
```

2. Create and activate a virtual environment:

```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
```

   On macOS or Linux: `source venv/bin/activate`

3. Install the dependencies:

```powershell
   pip install -r requirements.txt
```

4. Create a `.env` file in the project root (see `.env.example`):

```
   SECRET_KEY=your-random-secret-key
   DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   FLASK_DEBUG=1
```

   Generate a secret key with:

```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
```

5. Start the app:

```powershell
   python app.py
```

   Then open http://127.0.0.1:5000

The `expenses` table is created automatically the first time the app starts.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Signs session cookies (used for flash messages) |
| `DATABASE_URL` | Yes | Postgres connection string |
| `FLASK_DEBUG` | No | Set to `1` for debug mode locally. Leave unset in production |

## Deployment

The app deploys to Vercel straight from this repository:

1. Push the code to GitHub.
2. Import the repository in Vercel.
3. Add `SECRET_KEY` and `DATABASE_URL` as environment variables.
4. Deploy.

Static files live in `public/` because Vercel ignores Flask's `static` folder.

## Possible next steps

- User accounts so each person has their own expenses
- Budgets and spending alerts
- Automated tests