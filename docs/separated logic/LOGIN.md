# Login specification

Baseline: 2026-10-02. Language: English. This standalone specification covers login only: UI behavior, API contract, validation, persistence and acceptance scenarios. CSRF acquisition is included as a prerequisite. Other account and workspace operations are outside its scope.

## 1. Entry points

| Purpose | Request |
| --- | --- |
| Open the form | `GET /login/` |
| Submit through the JSON API | `POST /api/auth/login/` |
| Submit without JavaScript | `POST /login/` (form-encoded) |
| Obtain a CSRF token | `GET /api/auth/csrf/` |

The browser uses the JSON API when JavaScript is enabled and ordinary form submission otherwise. All URLs include a trailing slash.

## 2. Login requirements

### 2.1 Form

The page displays **Welcome back**, the subtitle **Log in to continue working.**, a **Log in** submit button, a Back link to `/`, and a **Create one** link to `/register/`.

| Field | API name / test ID | Required | Rules |
| --- | --- | --- | --- |
| Username | `username` | Yes | Existing account username; uses Django's authentication form. Surrounding whitespace is trimmed and Unicode normalization is applied. Email is not an alternative login identifier. |
| Password | `password` | Yes | Must match the stored password. Case and whitespace are significant. |
| Redirect destination | `next` | No | API string; not a visible form input. The JavaScript client takes it from the login page's query string, defaulting to `/tasks/`. |

### 2.2 Behavior

| ID | Requirement |
| --- | --- |
| LOGIN-01 | Valid credentials for an active account authenticate the user and establish a Django session. |
| LOGIN-02 | Without a valid `next`, success navigates to `/tasks/`. The JavaScript flow displays `Logged in successfully.`. |
| LOGIN-03 | Safe relative destinations and allowed same-host URLs are accepted as `next`. Disallowed external destinations fall back to `/tasks/`. For HTTPS requests, the destination must also satisfy Django's HTTPS safety check. |
| LOGIN-04 | Empty or missing username/password produces field validation errors and API status 400. |
| LOGIN-05 | A nonexistent username, incorrect password or inactive account is rejected. Authentication-form non-field errors produce API status 401 and appear under `fields.__all__`. Do not require a distinct inactive-account message: the configured backend may reject it as invalid credentials. |
| LOGIN-06 | Failed login does not create a user or establish a new authenticated session. If a session was already authenticated, a failed login attempt does not explicitly clear it. |
| LOGIN-07 | An authenticated visitor can still open `/login/`; the page is not configured to automatically redirect them. The API also permits login while already authenticated, including switching to another valid account. |

### 2.3 API request and success response

```http
POST /api/auth/login/
Content-Type: application/json
X-CSRFToken: <token>
Cookie: <cookies retained from the CSRF request>
```

```json
{
  "username": "qa_student",
  "password": "TrainingPassword_8642!",
  "next": "/tasks/"
}
```

Success: **200 OK**.

```json
{
  "user": {
    "id": 42,
    "username": "qa_student",
    "email": "student@example.com"
  },
  "csrfToken": "<new-token>",
  "redirect_url": "/tasks/",
  "message": "Logged in successfully."
}
```

Successful login returns JSON rather than an HTTP redirect. The browser navigates using `redirect_url` after receiving success. The `user` object contains only ID, username and email.

## 3. CSRF and request validation

Before the POST, request `GET /api/auth/csrf/`. It is public and returns **200 OK** with `{"csrfToken":"<token>"}` and the CSRF cookie. Retain response cookies and send the token as `X-CSRFToken`. A session is not required before login, but CSRF validation is required.

After successful login, Django rotates the CSRF token; use the new `csrfToken` and updated cookies in subsequent requests. The JavaScript client fetches a token before its first write and updates its cached token from successful authentication responses. On a CSRF failure it clears the cache, displays the error, and fetches a fresh token on the next attempt; it does not automatically replay the failed request.

Validation order is significant:

1. Django middleware checks CSRF for unsafe requests.
2. The endpoint checks the HTTP method.
3. POST requires `Content-Type: application/json`, valid JSON and a top-level object.
4. Unknown fields and incorrect JSON types are rejected.
5. The login form validates credentials and performs authentication.

Allowed login keys are exactly `username`, `password`, `next`. All supplied values must be strings. Null, numeric or array values are not valid substitutes. Unknown keys such as `id`, `is_staff` or `remember_me` are rejected. An empty object is valid JSON but fails required-field validation.

### 3.1 Errors

Errors use the following envelope. `fields` is included for validation errors; each field maps to an array of messages. General form errors use `__all__`.

```json
{
  "error": {
    "code": "validation_error",
    "message": "Please correct the highlighted fields.",
    "fields": {
      "username": ["This field is required."]
    }
  }
}
```

| HTTP status | Code | Condition / message |
| --- | --- | --- |
| 400 | `invalid_json` | Malformed/empty JSON: `The request body must be valid JSON.` Non-object JSON: `The request body must be a JSON object.` |
| 400 | `validation_error` | Wrong types/unknown fields: `Invalid fields.` Form errors: `Please correct the highlighted fields.` |
| 401 | `validation_error` | Login authentication/non-field error; details in `fields.__all__`. |
| 403 | `csrf_failed` | `Refresh the CSRF token and try again.` |
| 405 | `method_not_allowed` | `Method not allowed.` with `Allow: POST` for login, or `Allow: GET` for CSRF acquisition. |
| 415 | `unsupported_media_type` | `Use Content-Type: application/json.` |

Missing CSRF can mask payload or method errors with 403. API paths without the required trailing slash reach the API catch-all and return JSON 404. Exact framework validation messages follow the installed Django version; tests should assert stable status, code and field keys where exact wording is not necessary.

## 4. Form interaction and HTML fallback

| ID | Requirement |
| --- | --- |
| LOGIN-FORM-01 | The form uses `novalidate`, so server validation handles errors instead of native browser validation popups. Password inputs mask their values. |
| LOGIN-FORM-02 | JavaScript submission clears previous errors, disables the submit button, changes its text to `Please wait…`, and marks the form `aria-busy="true"`. Further submissions while busy are ignored. |
| LOGIN-FORM-03 | API errors display an alert summary. Matching field errors mark inputs with `aria-invalid` and `aria-errormessage`; the first matched invalid field receives focus. General errors appear in the summary. |
| LOGIN-FORM-04 | A failed JavaScript request leaves the user on the form with entered values available for correction. The button and busy state are restored after the request. |
| LOGIN-FORM-05 | Successful JavaScript submission stores a one-time notification in session storage before navigating. If storage is unavailable, authentication and navigation still work, but the notification may be absent. |
| LOGIN-FORM-06 | Without JavaScript, login POSTs use form-encoded input and the hidden CSRF form token. Invalid submissions re-render the form with errors and HTTP 200; password fields are not repopulated by Django. |
| LOGIN-FORM-07 | Successful HTML login redirects to a safe `next` or `/tasks/` with HTTP 302; no custom login-success message is configured for that fallback. |

Automation hooks: `login-form`, the visible field names `username` and `password`, `submit`, `form-errors`, `error-{field}`, and `notification`. Scope field and submit locators to the relevant form. The authenticated header exposes `current-user` for checking the resulting username.

## 5. Persistence checks

Successful login authenticates an existing `auth_user` row rather than creating a new user. Django verifies the stored password hash and updates the user's login timestamp. Login does not change the username, email, password or staff privileges. Session persistence uses Django's configured session backend.

Verify that the authenticated session remains effective after navigating or refreshing and that the user count is unchanged. Failed login does not establish a new authenticated session; an already authenticated session is not explicitly cleared. No multifactor authentication, social login, custom login throttling or account-lockout flow is implemented in this handler.

## 6. Acceptance scenarios

Use isolated users and valid CSRF cookies/tokens unless CSRF failure is the intended test. Each row describes a separate scenario or a parameterized set of cases.

| ID | Scenario | Expected result |
| --- | --- | --- |
| LOGIN-T01 | Submit correct credentials for an active user with no `next`. | 200; authenticated session; new CSRF token; destination `/tasks/`. |
| LOGIN-T02 | Submit missing credentials, then wrong password, then nonexistent username, then an inactive account. | Missing fields: 400; authentication failures: 401; no new authenticated session. |
| LOGIN-T03 | Submit safe relative `next`; separately use an external or unsafe destination. | Safe destination returned; unsafe destination replaced with `/tasks/`. |
| LOGIN-T04 | Submit credentials while already authenticated. | Valid credentials may switch account; invalid attempt does not explicitly end the existing session. |
| LOGIN-API-T01 | Submit malformed JSON, a JSON array, incorrect field types, and unknown body keys. | 400 with appropriate code/field errors. |
| LOGIN-API-T02 | Submit without JSON content type; separately omit/alter CSRF token. | Valid-CSRF media-type failure: 415; CSRF failure: 403. |
| LOGIN-API-T03 | GET the login API endpoint. | 405 with `Allow: POST`. |
| LOGIN-API-T04 | Submit twice while the first browser request is pending. | One in-flight form operation; disabled button and busy state visible. |
| LOGIN-API-T05 | Correct a failed submission and retry. | Previous errors clear; corrected data is accepted; user reaches the success destination. |
| LOGIN-API-T06 | Disable JavaScript and repeat valid and invalid form submissions. | HTML response/redirect behavior matches section 4. |

## 7. Source references

- [Forms](../../workspace/forms.py): `LoginForm`, stable field test IDs.
- [API](../../workspace/api.py): request validation, CSRF, `sign_in`, error serialization.
- [API routes](../../workspace/api_urls.py) and [page routes](../../workspace/urls.py).
- [Form template](../../templates/form.html), [browser behavior](../../static/app.js).
- [Settings](../../config/settings.py): password validators, middleware and login destination.

This document was checked against repository source. Its acceptance scenarios are specifications, not a report of executed runtime tests.
