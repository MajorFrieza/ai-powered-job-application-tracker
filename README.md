# AI-Powered Job Application Tracker

A portfolio project for organizing a job search. Create an account, keep job applications in one place, review them on a kanban board, and use an LLM to summarize a job description and identify skills to emphasize.

## Features

- Sign up, log in, and log out with Django authentication.
- Add, edit, list, and delete job applications.
- Track applications in Applied, Interview, Offer, and Rejected statuses.
- Move cards between statuses on the kanban board without reloading.
- Analyze a job description for a summary, required skills, and skills to highlight.
- View a dashboard with application counts by status.
- Keep each user's application data scoped to their account.

## Screenshots

Screenshots are not captured yet. After configuring MongoDB and the AI API key, run the app, add sample applications, and save screenshots of:

1. The dashboard with status counts.
2. The kanban board with at least one card in multiple columns.
3. The edit page with a saved job-description analysis.

Add the images under `docs/screenshots/` and embed them here, for example:

```markdown
![Application dashboard](docs/screenshots/dashboard.png)
```

## Technology stack

- **Backend:** Python 3.12+ and Django 5.2
- **REST API:** Django REST Framework
- **Application data:** MongoDB via PyMongo
- **Authentication and sessions:** Django auth backed by SQLite
- **Frontend:** Django templates, Bootstrap 5, HTML, CSS, and vanilla JavaScript `fetch`
- **AI:** Gemini API via Google's GenAI Python SDK, called from the Django server
- **Deployment preparation:** Render, Gunicorn, and WhiteNoise

## Local setup

### Requirements

- Python 3.12 or later
- A MongoDB instance (MongoDB Atlas is suitable)
- A Gemini API key for live AI analysis (optional for the rest of the app)

### First-time setup

Open PowerShell in the project folder (the folder containing `manage.py`). If you have not created the virtual environment yet:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local `.env` from the example only if you do not already have one:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

If `.env` already exists, open it with `notepad .env` and edit it there. **Do not copy `.env.example` over an existing `.env`**—that can overwrite your local settings. The real `.env` is ignored by Git and must never be committed, pasted into chat, or shown in a screenshot.

Generate a Django secret key:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated value in `DJANGO_SECRET_KEY` in `.env`. Configure `MONGODB_URI` with the URI from your Atlas cluster's **Connect → Drivers** screen and set `MONGODB_DATABASE=job_tracker`. The URI must use a MongoDB **database user** created for the cluster, not your Atlas website login. Make sure your development IP is allowed in Atlas Network Access. URL-encode special characters in the database user's password if needed.

`GEMINI_API_KEY` is only needed for live job-description analysis. Create a key in Google AI Studio and put it in the private `.env` file. You can leave its placeholder while setting up the tracker; AI analysis will not work until you add a valid key. The key is used only on the server and must never be placed in browser JavaScript. Review the current [Gemini API pricing and free-tier details](https://ai.google.dev/gemini-api/docs/pricing); availability, limits, and data terms vary by model and account.
Set `GEMINI_MODEL=gemini-3.8-flash` in `.env` to use the current model available to new Gemini API users.

After changing `requirements.txt`, update the packages in your virtual environment:

```powershell
python -m pip install -r requirements.txt
```

### Run the app later

Whenever you want to start the app again, open PowerShell in the project folder. The virtual environment only needs to be activated in each new terminal session:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in your browser. To stop the server, press **Ctrl+C** in PowerShell. Closing the terminal also stops the local server; repeat the commands above the next time you want to use the app. Your MongoDB application records remain in Atlas.

If PowerShell blocks activation because of its execution policy, you can activate it for just the current PowerShell process, then start the server:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Run these setup checks after installing dependencies or changing project configuration:

```powershell
python manage.py migrate
python manage.py check
```

Create an account at `/accounts/signup/`, add applications at `/applications/`, view the board at `/board/`, and see the dashboard at `/`.

### Test

```powershell
python manage.py test applications accounts
node --check static\applications\board.js
node --check static\applications\analyze.js
```

The automated tests mock MongoDB and the AI provider; they do not require credentials or make API calls. For a complete demo, configure MongoDB and (if you want to show AI analysis) a Gemini API key, then verify those services locally.

## API endpoints

All application API endpoints require the user to be authenticated.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` / `POST` | `/api/applications/` | List or create applications |
| `GET` / `PUT` / `DELETE` | `/api/applications/{id}/` | Retrieve, replace, or delete one application |
| `PATCH` | `/api/applications/{id}/status/` | Update an application's status |
| `POST` | `/api/applications/{id}/analyze/` | Analyze and save a job description |

## Technical decisions

- **PyMongo for application documents:** The project stores job applications in MongoDB without adding an ORM abstraction. Django's built-in ORM remains responsible for users, sessions, and authentication in SQLite.
- **Owner ID on every application:** Each MongoDB document stores the authenticated Django user's ID. Reads and writes include that owner ID in their MongoDB filters, so clients cannot select another user's records by changing an ID in a request.
- **DRF serializers and Django forms:** Both API and template submissions are validated on the server. Browser validation improves usability but is not trusted as a security boundary.
- **AI calls stay on the server:** The browser sends a job description to Django; Django reads the secret API key from the environment, makes one provider request, validates the structured response, and saves the result to MongoDB.
- **Vanilla JavaScript for the board:** The board uses `fetch` with a CSRF token to request JSON and patch only the status field. No client-side framework or full-page reload is required.
- **SQLite for Django auth:** This keeps Django's user and session features on its supported ORM path. For hosted demos, SQLite persistence depends on the hosting filesystem; on ephemeral instances, users can be lost after a restart or redeploy. Use a persistent disk or a managed relational database if durable hosted accounts are required.

## Deployment preparation: Render

`render.yaml` describes a Render web service. To deploy:

1. Push this repository to GitHub and create MongoDB Atlas and Google AI Studio credentials if using AI analysis.
2. In Render, create a Blueprint from the repository and select the service in `render.yaml`.
3. In the service's environment settings, set:
   - `DJANGO_ALLOWED_HOSTS` to the Render hostname, such as `your-service.onrender.com`.
   - `DJANGO_CSRF_TRUSTED_ORIGINS` to the full HTTPS origin, such as `https://your-service.onrender.com`.
   - `MONGODB_URI` and `GEMINI_API_KEY` to their private values.
4. Deploy and check the Render logs and the service URL.

The Blueprint generates `DJANGO_SECRET_KEY`. Never commit real keys or URIs to this repository. SQLite on an ephemeral Render filesystem is not durable across instance replacement; configure persistent storage or accept that demo accounts may need to be recreated. MongoDB application data remains stored in the configured MongoDB deployment.
