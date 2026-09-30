# Functional specification

Implementation baseline: 2026-09-30. This document describes the functionality present in this repository, including implementation limitations. Requirement IDs provide stable references for manual and automated tests. The complete HTTP contract is in [API specification](API.md); relational SQL examples are in [JOIN examples](JOIN_EXAMPLES.md).

## 1. Scope and actors

Practice is an English-language QA training workspace for personal tasks, projects and labels. Anonymous visitors can view the landing page, register and log in. Authenticated users manage their own workspace. Authorized staff use the separate Django administration interface.

The application uses Django 5.2.17, SQLite, Django sessions and CSRF protection. Dates and times displayed by server templates use `Asia/Tbilisi`. The default configuration is for local development, with DEBUG enabled. The automated test project is maintained separately.

## 2. Pages and navigation

| ID | Route | Behavior |
| --- | --- | --- |
| NAV-01 | `/` | Public landing page with a static sample task board and feature descriptions. The board does not represent stored user tasks. |
| NAV-02 | `/register/` | Account creation form; an authenticated visitor is redirected to `/tasks/`. |
| NAV-03 | `/login/` | Login form with a registration link. Authenticated visitors are not automatically redirected by this page. |
| NAV-04 | `/tasks/` | Private task list, counters, search, filters and pagination. |
| NAV-05 | `/tasks/new/` | Private task creation form. |
| NAV-06 | `/tasks/{id}/` | Private task detail page. |
| NAV-07 | `/tasks/{id}/edit/` | Private task edit form. |
| NAV-08 | `/projects/` | Private project and label lists and creation forms. |
| NAV-09 | `/admin/` | Django administration; requires an active staff account and relevant permissions. |

The header always includes the home brand link and **My tasks**. Anonymous visitors see **Log in** and **Create account**. Authenticated users see **Projects**, their username and **Log out**. The home CTA points to `/tasks/`, with **Get started** for visitors and **Open tasks** for authenticated users. Private pages redirect anonymous visitors to login with a `next` destination.

## 3. Accounts and sessions

| ID | Requirement / acceptance criterion |
| --- | --- |
| AUTH-01 | Registration requires username, valid email, password, matching password confirmation and accepted terms. Missing or invalid fields produce validation errors and do not create an account. |
| AUTH-02 | Username follows Django's built-in UserCreationForm rules: maximum 150 characters, Unicode letters/digits and `@ . + - _`; duplicate usernames are rejected. Email is required but is not unique across accounts. |
| AUTH-03 | Password validation uses Django's configured similarity, minimum-length (8 characters), common-password and numeric-password validators. Passwords must match. |
| AUTH-04 | Successful registration creates and immediately authenticates the user, opens `/tasks/`, and displays `Account created. Welcome!`. A new account has no automatically seeded tasks, projects or labels. |
| AUTH-05 | Login requires username and password. Invalid credentials and inactive accounts are rejected. Successful login opens a safe `next` destination, or `/tasks/`, and the JavaScript flow displays `Logged in successfully.`. |
| AUTH-06 | Logout ends the session and opens `/`. Subsequent private requests require authentication. The JavaScript flow displays `Logged out.`. |
| AUTH-07 | Registration while authenticated redirects in the HTML flow and returns 409 in the API flow. Ordinary duplicate-username validation returns 400 through the API; a concurrent save conflict returns 409. |
| AUTH-08 | Terms acceptance is validated during registration but is not stored as a dedicated consent record. There is no email verification, profile editor, password-reset page or self-service account deletion. |

## 4. Data and validation

Text form fields trim surrounding whitespace except password fields. Limits below apply after form normalization. Ownership and creation timestamps are assigned by the application, not editable public API fields.

| Entity / field | Required | Rules |
| --- | --- | --- |
| Task title | Yes | 3–120 characters; duplicate titles allowed. |
| Task description | No | Up to 2,000 characters; multiline plain text. |
| Task status | Yes | `todo` (To do), `in_progress` (In progress), `done` (Done). New UI form defaults to `todo`. |
| Task priority | Yes | `low` (Low), `medium` (Medium), `high` (High). New UI form defaults to `medium`. |
| Task due date | No | Date; API clients should use `YYYY-MM-DD`. Past dates allowed. No reminder or overdue workflow. |
| Task project | No | Zero or one project belonging to the task owner. |
| Task labels | No | Zero or more labels belonging to the task owner. A label cannot occur twice on one task. |
| Project name | Yes | 2–80 characters; unique per owner under database equality rules. |
| Project description | No | Up to 500 characters. |
| Label name | Yes | 2–40 characters; unique per owner under database equality rules. |
| Label color | Yes | `blue`, `green`, `amber`, `red`, `purple`; new UI form defaults to `blue`. |

Project and label names may be reused by different users. The application does not explicitly normalize name case; do not assume case-insensitive uniqueness. Users own many tasks, projects and labels. Task-to-project is an optional foreign key; task-to-label is many-to-many.

## 5. Task lifecycle

| ID | Requirement / acceptance criterion |
| --- | --- |
| TASK-01 | **New task** opens a form containing all editable task fields, an owned-project selector and an owned-label multiselect. Successful save creates a task for the current user, opens its detail page and displays `Task created.`. |
| TASK-02 | Invalid saves keep the form visible, retain entered values, show errors and do not persist the submitted changes. Cancel or Back opens the task list without saving. |
| TASK-03 | Detail displays task ID, title, description, status, priority, project, labels, due date and creation time. Missing values display `No description added.`, `Unassigned`, `No labels` and `No due date`. Description line breaks are preserved. |
| TASK-04 | Due dates display as `DD.MM.YYYY`; creation time displays as `DD.MM.YYYY HH:mm`. Detail data is initially server-rendered and refreshed from the API when JavaScript runs. |
| TASK-05 | **Edit task** opens prefilled fields. Save updates the existing task, preserves ID/owner/creation timestamp, opens detail and displays `Task saved.`. Clearing optional fields removes their previous values. |
| TASK-06 | Any valid status may change directly to any other valid status, including reopening a completed task. There are no enforced transition rules. The task-list checkmark is a status indicator, not an interactive completion control. |
| TASK-07 | **Delete** opens a native confirmation dialog showing the task title and an irreversible-action message. Cancel closes it without mutation. Confirm deletes the task and its label associations, retains projects/labels, and returns to the task list. A subsequent detail request returns 404. |
| TASK-08 | With JavaScript, task deletion displays `Deleted successfully.` because the API returns an empty 204. HTML POST deletion displays `Task deleted.`. |

## 6. Task list, search and pagination

| ID | Requirement / acceptance criterion |
| --- | --- |
| LIST-01 | Only the current user's tasks appear. Each row links to detail and displays title, project when assigned, due date or placeholder, colored labels, priority and status. |
| LIST-02 | Counters show all owned tasks: Total, Active (everything except `done`) and Completed (`done`). Filters do not change these counters. `Found` shows the filtered count. |
| LIST-03 | Search matches a substring in title OR description after trimming the search query. SQLite case-insensitive matching is reliable for ASCII; full Unicode case folding is not guaranteed. |
| LIST-04 | Status, priority, project and label filters combine with search using AND. Empty selections mean no filter. Only owned projects and labels appear as choices. |
| LIST-05 | Sorting supports newest first (creation time descending, ID descending), oldest first (creation time ascending, ID ascending), and title (database ordering, ID ascending). Default is newest first. |
| LIST-06 | Default page size is six. Previous/Next preserve filters; controls and page number appear only when multiple pages exist. A normal filter-form submission starts at page 1. Reset clears parameters and restores the default list. |
| LIST-07 | Zero owned tasks shows `Start with one task` and a creation link. A filter returning zero matches for a nonempty workspace shows `No matches` and a reset link. |
| LIST-08 | With JavaScript, initial loading, Search, Reset and pagination use the API and replace list contents. Successful navigation updates the URL; browser Back/Forward reloads corresponding results. Typing or selecting alone does not apply filters. |
| LIST-09 | An in-progress list request is aborted when a newer one starts. The list exposes `aria-busy` while loading. Failures display an error near the filters and leave the previous list visible. |
| LIST-10 | API-only query options include `has_project` and `page_size`. They can also be passed in a list-page URL for its JavaScript API fetch, but have no dedicated UI controls and are not retained by a normal filter-form submission. |

## 7. Projects, labels and reports

| ID | Requirement / acceptance criterion |
| --- | --- |
| REL-01 | The workspace displays project count, label count and unassigned-task count for the current user. Projects and labels are ordered by name, then ID. |
| REL-02 | Project cards show name, description (`No description.` when empty), task count, completed-task count and number of distinct labels used across project tasks. **Open tasks** applies the project filter. Empty state: `No projects yet`. |
| REL-03 | New project validates name/description, creates an owned project, reloads the workspace and displays `Project created.`. Duplicate-name message: `You already have a project with this name.`. |
| REL-04 | Label rows show name, color and task count. **Filter tasks** applies the label filter. Empty state: `No labels yet.`. |
| REL-05 | New label validates name/color, creates an owned label, reloads the workspace and displays `Label created.`. Duplicate-name message: `You already have a label with this name.`. |
| REL-06 | Project deletion executes immediately from its Delete button, without a confirmation dialog. Tasks survive and become unassigned; their labels remain. |
| REL-07 | Label deletion executes immediately, removes its task associations, and preserves tasks, projects and other labels. |
| REL-08 | JavaScript project/label deletion displays `Deleted successfully.`. HTML deletion displays `Project deleted. Its tasks are now unassigned.` or `Label deleted.`. |
| REL-09 | Project editing (PUT/PATCH), label editing (PATCH), project detail with tasks, and the project-summary report are available through the API. There are no corresponding workspace edit or report pages. |
| REL-10 | Report aggregates include projects with zero tasks and labels with zero usage. The matrix includes every owned project/label pair, including zero counts. Unassigned tasks contribute to label totals but not project matrix cells. |
| REL-11 | Deleting a user through administration cascades to their tasks, projects and labels. Ownership consistency for selected relations is enforced by workspace forms; direct database or administrator edits are outside that guarantee. |

## 8. Shared UI behavior and access control

| ID | Requirement / acceptance criterion |
| --- | --- |
| UI-01 | JavaScript forms disable the submit button, show `Please wait…`, and set `aria-busy` during submission. Repeat submits while busy are ignored. The original button state returns after completion/failure. |
| UI-02 | API validation errors display an alert summary and field errors, mark matching fields invalid and focus the first matched invalid input. General/unmatched field errors appear in the summary. Prior errors clear on retry. |
| UI-03 | Successful JavaScript mutations carry a one-time notification through session storage to the destination page. When browser storage is unavailable, the mutation/navigation still works but that notification may be absent. |
| UI-04 | API writes include the session cookie and a fetched CSRF token. Login/registration update the cached token. A CSRF failure clears it for the next attempt; the failing write is not automatically retried. |
| UI-05 | User text is escaped by templates or inserted using `textContent`. Descriptions are not rendered as user-supplied HTML. |
| UI-06 | Layout adjusts at 850px and 620px breakpoints. Narrow layouts stack the landing content and project workspace, wrap task rows/navigation, and move relation creation forms ahead of the project list. |
| SEC-01 | Public workspace resource reads, updates and deletes resolve objects by current owner. Missing and other-user resource IDs return the same 404 behavior. |
| SEC-02 | Relation assignment validates ownership. Sending another user's or a nonexistent project/label ID fails validation. Numeric relation filters simply return matching owned tasks, normally an empty result for another user's ID. |
| SEC-03 | All unsafe requests require CSRF validation, including login and registration. Private API requests without a session return 401 after method/CSRF checks; private HTML pages redirect to login. |

## 9. HTML fallback and known differences

Server-rendered forms support ordinary HTML POSTs for registration, login, logout, task create/edit and project/label create/delete. Delete endpoints are `/tasks/{id}/delete/`, `/projects/{id}/delete/` and `/labels/{id}/delete/`; they require POST and authentication. Successful HTML writes redirect and may use Django messages.

Task deletion's visible dialog requires JavaScript to open: it is not a fully usable no-JavaScript UI even though a protected HTML POST endpoint exists. Registration/login/task forms disable browser-native validation; project/label creation forms retain native validation.

HTML list handling is more permissive than the API: invalid status/priority or nonnumeric relation filters are ignored; invalid sorting falls back to newest. Django `get_page` selects page 1 for a nonnumeric page and the last page for an out-of-range page. HTML page size stays six; `has_project` and `page_size` are ignored. API queries instead follow the strict validation documented in [API specification](API.md). With JavaScript enabled, initial HTML rendering may therefore be followed by an API error for an invalid URL.

## 10. Administration and demo data

**ADMIN-01:** The Django admin registers Task, Project and Label, in addition to built-in user/group management. Staff access is permission-controlled and is not limited to the current user's workspace. Task lists expose title, owner, project, status, priority and due date; filters cover project, labels, status and priority; search covers title/description; labels use a horizontal multiselect. Project lists expose name, owner and creation time and search name/description/owner username. Label lists expose name, color, owner and creation time, filter by color and search name/owner username.

**DEMO-01:** `python manage.py seed_demo` creates `demo` (email `demo@example.com` on initial creation), with password `DemoPass123!` when newly created. It ensures three named projects and five named labels. If demo has no tasks, it creates twelve. Every invocation reassigns projects and labels on all existing demo tasks in ID order, so rerunning it is not read-only.

**DEMO-02:** `python manage.py seed_demo --reset` deletes demo-owned tasks, projects and labels, resets the password, and recreates fixtures in one transaction. Other users' data is preserved. IDs are not guaranteed to be reused.

| Fixture | Expected after reset |
| --- | --- |
| Tasks | 12 total; 8 active; 4 done; 3 unassigned; 2 labels per task |
| Statuses | 4 each of `todo`, `in_progress`, `done` |
| Priorities | 6 low, 3 medium, 3 high |
| Web application | 3 tasks, 0 done, 4 distinct labels |
| Public API | 3 tasks, 0 done, 4 distinct labels |
| Release 1.0 | 3 tasks, 3 done, 4 distinct labels |
| Labels | API/blue: 5 tasks; UI/purple: 5; Regression/green: 5; Critical/red: 5; Data/amber: 4 |
| Dates | 3 tasks have no due date; others use `2026-09-15 + zero-based task index` |
| Matrix | 15 project/label combinations, including zero-count entries |

## 11. Automation references and scope limits

Stable `data-testid` hooks include navigation (`nav-tasks`, `nav-projects`, `nav-login`, `nav-register`, `current-user`, `logout`), forms (`register-form`, `login-form`, `task-form`, `project-form`, `label-form`), task counters/list/filter controls, task detail fields, and deletion controls (`delete-dialog`, `cancel-delete`, `confirm-delete`). Form widgets use their field names as test IDs. Repeated task/project/label elements expose `data-task-id`, `data-project-id`, or `data-label-id`; scope repeated controls to their row/card. Both relation forms contain a `name` field, so a global `name` locator is ambiguous.

Acceptance coverage should include valid operations, required/length/choice boundaries, empty states, filter combinations, pagination boundaries, persistence after refresh, CSRF failures, unauthenticated access, cross-user isolation and relation deletion effects. API tests must supply valid CSRF when testing deeper authentication/validation errors.

There is no sharing, collaboration, file upload, task comments, bulk action, due-date sorting, reminders, audit history, soft delete, recovery, API token authentication or public self-service user-management API. This specification records source behavior; it does not assert that browser or runtime tests have been executed.
