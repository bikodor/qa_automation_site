# JSON API

Base URL: `http://127.0.0.1:8000/api/`. Paths require a trailing slash. The interface uses these endpoints through `fetch`; select **Fetch/XHR** in the browser Network panel to inspect them.

Authentication uses the Django session cookie. Obtain a CSRF token with `GET /api/auth/csrf/`, retain the response cookies, and send the token in `X-CSRFToken` on POST, PUT, PATCH and DELETE. Login and registration rotate the token and return the new `csrfToken`. JSON writes also require `Content-Type: application/json`. Logout accepts `{}`.

## Endpoints

| Method | Path | Result |
| --- | --- | --- |
| GET | `/api/auth/csrf/` | CSRF token and cookie, 200 |
| POST | `/api/auth/register/` | Create account and log in, 201 |
| POST | `/api/auth/login/` | Log in, 200 |
| POST | `/api/auth/logout/` | End the session, 200 |
| GET | `/api/auth/me/` | Current user ID, username and email, 200 |
| GET | `/api/tasks/options/` | Available statuses and priorities, 200 |
| GET | `/api/tasks/` | Filtered, paginated tasks and overall counters, 200 |
| POST | `/api/tasks/` | Create a task, 201 |
| GET | `/api/tasks/{id}/` | Read a task, 200 |
| PUT | `/api/tasks/{id}/` | Replace editable task fields, 200 |
| PATCH | `/api/tasks/{id}/` | Update only supplied task fields, 200 |
| DELETE | `/api/tasks/{id}/` | Delete a task, 204 with no response body |
| GET, POST | `/api/projects/` | List projects with JOIN counts, or create one |
| GET, PUT, PATCH, DELETE | `/api/projects/{id}/` | Project details with its tasks, update or delete |
| GET, POST | `/api/labels/` | List labels with task counts, or create one |
| GET, PATCH, DELETE | `/api/labels/{id}/` | Read, update or delete a label |
| GET | `/api/reports/project-summary/` | Project/label aggregate matrix for JOIN tests |

All task endpoints, `/auth/me/` and `/auth/logout/` require a session. Passwords are never returned. Other users' tasks return 404 for read, update and delete.

## Request examples

Registration:

```json
{
  "username": "qa_student",
  "email": "student@example.com",
  "password1": "TrainingPassword_8642!",
  "password2": "TrainingPassword_8642!",
  "terms": true
}
```

Login:

```json
{"username": "qa_student", "password": "TrainingPassword_8642!", "next": "/tasks/"}
```

`next` is optional; external redirect destinations are rejected in favor of `/tasks/`. Login and registration return `user`, `csrfToken`, `redirect_url` and `message`. They return JSON, not HTTP redirects. The interface navigates after receiving success.

Create or replace a task:

```json
{
  "title": "Check registration",
  "description": "Cover both valid and invalid data.",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-10-01",
  "project_id": 2,
  "label_ids": [1, 4]
}
```

Title: 3–120 characters after trimming. Description: optional, up to 2000 characters. `status`: `todo`, `in_progress`, `done`. `priority`: `low`, `medium`, `high`. Due date: optional ISO date; null or an empty string clears it. `project_id` is an owned project ID or null. `label_ids` is an array of owned label IDs. Past dates are allowed. POST and PUT require title, status and priority; omitted optional fields are cleared. PATCH preserves omitted fields:

```json
{"status": "done"}
```

Task responses contain `task` with its ID, editable fields, labels, creation timestamp and page URL. Successful writes also contain `message` and `redirect_url`.

## Search and pagination

`GET /api/tasks/?q=registration&status=todo&priority=high&project_id=2&label_id=4&sort=newest&page=1&page_size=6`

- `q`: searches title and description. SQLite case-insensitive matching is reliable for ASCII.
- `status` and `priority`: optional filters combined with AND.
- `project_id` and `label_id`: relational filters combined with the other filters.
- `has_project=true|false`: include only assigned or unassigned tasks.
- `sort`: `newest` (default), `oldest`, or `title`; ID breaks ties.
- `page`: positive integer, default 1.
- `page_size`: 1–100, default 6.

The response contains `results`, `count`, `page`, `page_size`, `pages`, `next`, `previous`, and `stats` (`total`, `active`, `done`). Next and previous are page numbers or null. Count includes filters; stats count all of the current user's tasks. An empty result has page 1, one page and an empty results list. Invalid filters/pagination return 400; a page beyond the last returns 404.

## Relational resources

Create a project with `{"name":"Checkout","description":"Payment flows"}`. Create a label with `{"name":"Smoke","color":"red"}`; colors are `blue`, `green`, `amber`, `red`, and `purple`. Names are unique per user.

Project list/detail responses expose `task_count`, `done_count`, and the distinct `label_count`. Label responses expose `task_count`. Deleting a project keeps its tasks and sets `project_id` to null. Deleting a label removes only rows in the task-label join table. Other users' relation IDs are rejected.

`GET /api/reports/project-summary/` returns `projects`, `labels`, `unassigned_tasks`, and a `matrix` containing every project/label combination with its task count. See [JOIN examples](JOIN_EXAMPLES.md) for equivalent SQLite queries.

## Errors

```json
{
  "error": {
    "code": "validation_error",
    "message": "Please correct the highlighted fields.",
    "fields": {"title": ["This field is required."]}
  }
}
```

`fields` is present for validation failures. General form errors use `__all__`.

| Status | Meaning |
| --- | --- |
| 400 | Invalid JSON, wrong field types, unknown body fields, invalid form or query parameters |
| 401 | Missing session or incorrect login credentials |
| 403 | Missing or invalid CSRF token |
| 404 | Unknown endpoint, unavailable task or page |
| 405 | Unsupported method; see the Allow header |
| 409 | Registering while logged in, or concurrent username conflict |
| 415 | Missing/wrong Content-Type for a JSON write |

A username already present during normal form validation returns 400. A conflicting concurrent creation at save time returns 409. CSRF middleware runs before the endpoint: unsafe requests without a token return 403 even when authentication or payload validation would otherwise fail.

## PowerShell example

```powershell
$base = 'http://127.0.0.1:8000'
$csrf = Invoke-RestMethod "$base/api/auth/csrf/" -SessionVariable session
$headers = @{ 'X-CSRFToken' = $csrf.csrfToken }
$body = @{ username = 'demo'; password = 'DemoPass123!' } | ConvertTo-Json
$login = Invoke-RestMethod "$base/api/auth/login/" -Method Post -WebSession $session -Headers $headers -ContentType 'application/json' -Body $body
$headers['X-CSRFToken'] = $login.csrfToken
Invoke-RestMethod "$base/api/tasks/?page_size=3" -WebSession $session
$task = @{ title = 'API practice'; status = 'todo'; priority = 'high' } | ConvertTo-Json
Invoke-RestMethod "$base/api/tasks/" -Method Post -WebSession $session -Headers $headers -ContentType 'application/json' -Body $task
```

Demo credentials require `python manage.py seed_demo` first. For independent test runs, register separate users. The UI sends API requests for authentication, task writes, task detail reads, search, reset and pagination. Forms retain ordinary HTML submission as a fallback when JavaScript is disabled.
