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

The first version includes registration/login and a task manager with CRUD, statuses, priorities, due dates, search, filters, sorting, pagination, ownership checks, CSRF protection, and a delete confirmation dialog. Stable `data-testid` attributes are present on forms, fields, actions, notifications, task rows, filters, pagination, and empty states.

The local settings use SQLite, English locale, DEBUG mode, and a development secret key. This is a test playground, not a production deployment.
