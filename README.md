# QA Automation Site

An English Django training site for writing UI and API automation scenarios. The site project is intentionally separate from `qa_automation_tests`.

## Run locally (PowerShell)

```powershell
cd qa_automation_site
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Demo account: **demo / DemoPass123!**. Use `seed_demo --reset` to restore its 12 sample tasks.

The site includes registration/login, task CRUD, statuses, priorities, due dates, search, filters, sorting, pagination, ownership checks, CSRF protection, and delete confirmation. Projects and labels add relational test data: each user owns projects and labels, tasks optionally belong to one project, and tasks can have many labels.

The interface uses JSON API calls for authentication, task operations, projects, labels, filters and pagination. See [API documentation](docs/API.md) and [JOIN examples](docs/JOIN_EXAMPLES.md). Stable `data-testid` attributes are available throughout the UI.

The local settings use SQLite, English locale, DEBUG mode, and a development secret key. This is a test playground, not a production deployment.
