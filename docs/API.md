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

All task, project, label and report endpoints, `/auth/me/` and `/auth/logout/` require a session. Only CSRF, registration and login endpoints are public. Passwords are never returned. Other users' tasks, projects and labels return 404 for read, update and delete.

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

Demo credentials require `python manage.py seed_demo` first. For independent test runs, register separate users. The UI sends API requests for authentication, task writes, task detail reads, search, reset and pagination. Forms retain ordinary HTML submission as a fallback when JavaScript is disabled, but the visible task-deletion dialog requires JavaScript to open.

## Complete request catalog

Source baseline: 2026-09-30, `workspace/api_urls.py` and `workspace/api.py`. This catalog expands every supported method separately. Example IDs are illustrative: use IDs returned by your own create/list requests. All request bodies below are JSON objects. GET and DELETE do not require a body; logout requires `{}`. Success responses are JSON except 204. These routes do not issue HTTP redirects; `redirect_url` instructs the client where to navigate.

### Authentication (5 operations)

| Request | Body example | Success response |
| --- | --- | --- |
| `GET /api/auth/csrf/` | None | 200: `{"csrfToken":"<token>"}`; establishes/updates the CSRF cookie. |
| `POST /api/auth/register/` | `{"username":"student","email":"student@example.com","password1":"TrainingPassword_8642!","password2":"TrainingPassword_8642!","terms":true}` | 201: `{"user":User,"csrfToken":"<new-token>","redirect_url":"/tasks/","message":"Account created. Welcome!"}`. |
| `POST /api/auth/login/` | `{"username":"demo","password":"DemoPass123!","next":"/projects/"}` | 200: `{"user":User,"csrfToken":"<new-token>","redirect_url":"/projects/","message":"Logged in successfully."}`. |
| `POST /api/auth/logout/` | `{}` | 200: `{"message":"Logged out.","redirect_url":"/"}`. |
| `GET /api/auth/me/` | None | 200: `{"user":User}`. |

`User`, `Task`, `Project`, and `Label` in response notation refer to the schemas below; the notation is not literal JSON. Registration fields are all required. Login requires username/password; `next` is optional. Username/email/password rules are described in [functional specification](FUNCTIONAL_SPECIFICATION.md#3-accounts-and-sessions). Normal duplicate registration is 400; already-authenticated registration is 409. Login field errors are 400, while non-field errors such as incorrect credentials are 401. Login is also callable while already authenticated. Redirect validation allows safe relative and same-host destinations; HTTPS requests require HTTPS-compatible destinations. An absent/unsafe `next` uses `/tasks/`.

### Tasks (7 operations)

| Request | Body example | Success response |
| --- | --- | --- |
| `GET /api/tasks/options/` | None | 200: `{"statuses":[{"value":"todo","label":"To do"},{"value":"in_progress","label":"In progress"},{"value":"done","label":"Done"}],"priorities":[{"value":"low","label":"Low"},{"value":"medium","label":"Medium"},{"value":"high","label":"High"}]}`. |
| `GET /api/tasks/` | None; query parameters below | 200: paginated task collection. |
| `POST /api/tasks/` | `{"title":"Check checkout","description":"Verify payment","status":"todo","priority":"high","due_date":"2026-10-01","project_id":2,"label_ids":[1,4]}` | 201: `{"task":Task,"redirect_url":"/tasks/{id}/","message":"Task created."}`. |
| `GET /api/tasks/{id}/` | None | 200: `{"task":Task}`. |
| `PUT /api/tasks/{id}/` | `{"title":"Updated checkout","status":"in_progress","priority":"medium"}` | 200: `{"task":Task,"redirect_url":"/tasks/{id}/","message":"Task saved."}`; omitted description/date/project/labels are cleared. |
| `PATCH /api/tasks/{id}/` | `{"status":"done"}` | 200: same envelope/message as PUT; omitted fields remain unchanged. |
| `DELETE /api/tasks/{id}/` | None | 204, empty body. |

Task POST/PUT require title, status and priority even though the model has defaults. Optional values clear with `description: ""` or null, `due_date: ""` or null, `project_id: null`, and `label_ids: []`. PATCH `{}` is accepted and preserves editable values. Duplicate label IDs resolve to a single relationship. Due-date input uses Django form date parsing; ISO `YYYY-MM-DD` is the portable client format, not a custom ISO-only parser.

Current implementation detail: integer `project_id: 0` is treated as an empty project selection. Negative/nonexistent nonzero IDs fail form validation. Relation form errors use `project` and `labels` keys, rather than the JSON input names `project_id` and `label_ids`; type errors from the JSON wrapper use the JSON names.

### Projects (6 operations)

| Request | Body example | Success response |
| --- | --- | --- |
| `GET /api/projects/` | None | 200: `{"results":[Project]}`; unpaginated, ordered by name then ID. |
| `POST /api/projects/` | `{"name":"Checkout","description":"Payment flows"}` | 201: `{"project":Project,"message":"Project created."}`; initial counts are zero. |
| `GET /api/projects/{id}/` | None | 200: `{"project":Project,"tasks":[Task]}`; tasks unpaginated, newest first with descending ID tie-break. |
| `PUT /api/projects/{id}/` | `{"name":"Checkout v2"}` | 200: `{"project":Project,"message":"Project saved."}`; omitted description cleared. |
| `PATCH /api/projects/{id}/` | `{"description":"Updated scope"}` | 200: same envelope/message as PUT; omitted fields preserved. |
| `DELETE /api/projects/{id}/` | None | 204, empty body; its tasks become unassigned. |

Name is required for POST/PUT, 2–80 characters after trimming. Description is optional, at most 500 characters; empty string or null clears it. PATCH `{}` preserves the project. Duplicate owned names produce a `name` validation error. Projects have no `redirect_url` in write responses; the UI returns to `/projects/` itself.

### Labels (5 operations)

| Request | Body example | Success response |
| --- | --- | --- |
| `GET /api/labels/` | None | 200: `{"results":[Label]}`; unpaginated, ordered by name then ID. |
| `POST /api/labels/` | `{"name":"Smoke","color":"red"}` | 201: `{"label":Label,"message":"Label created."}`; initial task count is zero. |
| `GET /api/labels/{id}/` | None | 200: `{"label":Label}`. |
| `PATCH /api/labels/{id}/` | `{"color":"green"}` | 200: `{"label":Label,"message":"Label saved."}`; omitted fields preserved. |
| `DELETE /api/labels/{id}/` | None | 204, empty body; task-label associations removed, tasks preserved. |

POST requires both name (2–40 characters after trimming) and color. The model's blue default does not make color optional in the API form. Valid colors: blue, green, amber, red and purple. Duplicate owned names produce a `name` validation error. PATCH `{}` preserves the label. PUT is not supported (405). Write responses have no `redirect_url`.

### Reports (1 operation)

`GET /api/reports/project-summary/` has no body and returns 200:

```json
{
  "projects": [],
  "labels": [],
  "unassigned_tasks": 0,
  "matrix": []
}
```

For a populated workspace, `projects` and `labels` contain Project and Label objects. Each matrix row contains `project_id` (integer), `project` (name), `label_id` (integer), `label` (name), and `task_count` (integer). Rows are ordered by project name/ID, then label name/ID. All project/label pairs are present even when their task count is zero. Matrix length equals project count multiplied by label count; if either collection is empty the matrix is empty. Counts reflect the authenticated workspace. There are no report filters or pagination.

### Collection query contract

Only `/api/tasks/` implements query filtering and pagination. Unknown query keys are ignored, unlike unknown JSON body keys.

| Parameter | Default | Accepted values and behavior |
| --- | --- | --- |
| `q` | Empty | Trimmed substring search across title OR description. Whitespace-only means no search. |
| `status` | Empty | Empty or `todo`, `in_progress`, `done`; other values: 400. |
| `priority` | Empty | Empty or `low`, `medium`, `high`; other values: 400. |
| `project_id` | Empty | Empty or digit-only ID; selects matching owned tasks. Unknown/foreign IDs normally return no matches. |
| `label_id` | Empty | Empty or digit-only ID; selects matching owned tasks without duplicate results. |
| `has_project` | Empty | Empty, `true` or `false`, case-sensitive. Combined with all other filters using AND. |
| `sort` | `newest` | `newest`, `oldest`, `title`; explicit empty/unknown value: 400. |
| `page` | `1` | Parsed as integer, at least 1; explicit empty/invalid: 400; beyond last page: 404. |
| `page_size` | `6` | Parsed as integer, 1–100 inclusive; explicit empty/invalid: 400. |

Example: `GET /api/tasks/?q=checkout&status=todo&priority=high&project_id=2&label_id=4&has_project=true&sort=oldest&page=1&page_size=10`.

An empty valid collection returns exactly this shape:

```json
{
  "results": [],
  "count": 0,
  "page": 1,
  "page_size": 6,
  "pages": 1,
  "next": null,
  "previous": null,
  "stats": {"total": 0, "active": 0, "done": 0}
}
```

For populated results, `results` contains Task objects, `count` is the filtered total, `pages` is the page count and `next`/`previous` are adjacent page numbers or null. `stats` is calculated before filtering. Invalid page or page_size values both report errors under `fields.page`.

## Response schemas

| Object | Fields |
| --- | --- |
| User | `id`: integer; `username`: string; `email`: string. |
| Task | `id`: integer; `title`, `description`: strings; `status`, `status_label`, `priority`, `priority_label`: strings; `project_id`: integer or null; `project`: `{id, name}` or null; `labels`: array of `{id, name, color}`; `label_ids`: integer array in matching label order; `due_date`: ISO date string or null; `created_at`: ISO timestamp string; `url`: `/tasks/{id}/`. |
| Project | `id`: integer; `name`, `description`: strings; `created_at`: ISO timestamp; `task_count`: number of distinct tasks; `done_count`: number of distinct done tasks; `label_count`: number of distinct labels used by its tasks, excluding null/unlabeled entries. |
| Label | `id`: integer; `name`, `color`: strings; `created_at`: ISO timestamp; `task_count`: number of distinct associated tasks. |

Task label arrays are ordered by label name, then ID. Empty descriptions are returned as `""`. Public resource responses do not include owner IDs. Timestamp values are timezone-aware; consumers should parse the offset rather than assert a fixed suffix. There is no `updated_at` field.

Example task representation (illustrative IDs/timestamp):

```json
{
  "id": 12,
  "title": "Check checkout",
  "description": "Verify payment",
  "status": "todo",
  "status_label": "To do",
  "priority": "high",
  "priority_label": "High",
  "project": {"id": 2, "name": "Checkout"},
  "project_id": 2,
  "labels": [{"id": 4, "name": "Smoke", "color": "red"}],
  "label_ids": [4],
  "due_date": "2026-10-01",
  "created_at": "2026-09-30T12:00:00+00:00",
  "url": "/tasks/12/"
}
```

## Validation order and precise errors

1. Django middleware performs CSRF validation before unsafe requests reach the endpoint. Missing/invalid CSRF yields 403 even if the method, session or payload would otherwise fail.
2. The endpoint checks the method, then authentication for private endpoints.
3. POST/PUT/PATCH require `application/json`, valid JSON and a top-level object.
4. Unknown body keys and incorrect JSON types are rejected before form validation or resource lookup.
5. Resource lookup and form/query validation run inside the handler.

All body values must be strings except: `terms` must be a JSON boolean; `project_id` must be an integer or null; `label_ids` must be an array of integers; `description` and `due_date` may also be null. Booleans are not accepted as integer IDs. `label_ids: null`, numeric titles, string IDs and `terms: "true"` fail type validation. Server-managed fields such as `owner`, `id` and `created_at` are unknown write fields. DELETE does not parse a JSON body.

| Status | `error.code` | Message / condition |
| --- | --- | --- |
| 400 | `invalid_json` | `The request body must be valid JSON.` or `The request body must be a JSON object.` |
| 400 | `validation_error` | `Invalid fields.` for unknown/type errors; `Please correct the highlighted fields.` for forms; `Invalid query parameters.` for list queries. |
| 401 | `authentication_required` | `Log in to continue.` |
| 401 | `validation_error` | Login non-field errors; `fields.__all__` contains details. |
| 403 | `csrf_failed` | `Refresh the CSRF token and try again.` |
| 404 | `not_found` | `Task not found.`, `Project not found.`, `Label not found.`, `Page not found.` or `API endpoint not found.` |
| 405 | `method_not_allowed` | `Method not allowed.` with `Allow` listing supported methods. HEAD and OPTIONS are not automatically supported by these handlers. |
| 409 | `already_authenticated` | `Log out before creating another account.` |
| 409 | `validation_error` | Concurrent registration username conflict during save. |
| 415 | `unsupported_media_type` | `Use Content-Type: application/json.` |

Unknown routes beneath `/api/` use the JSON 404 catch-all. Always include trailing slashes: slashless API paths also reach that catch-all. Wrapped handler responses set `Cache-Control: no-store`, but early wrapper errors, CSRF middleware responses and catch-all 404s do not explicitly set this header. Validation message text from Django forms can depend on the installed Django version.

Current limitations: project/label duplicate names are checked by forms and database uniqueness constraints, but concurrent duplicate saves do not have the explicit IntegrityError handling implemented for registration. No idempotency keys, optimistic locking or custom throttling are implemented. Do not treat unexpected database/concurrency failures as guaranteed structured JSON errors.

## Source and related specifications

- Routing: `workspace/api_urls.py`; request handling/serialization: `workspace/api.py`.
- Forms/validation: `workspace/forms.py`; data models: `workspace/models.py`.
- [Functional specification](FUNCTIONAL_SPECIFICATION.md), including HTML fallback differences.
- [Database specification](DATABASE.md) and [JOIN examples](JOIN_EXAMPLES.md).
