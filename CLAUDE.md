# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 6.0 web application for The School of Critical Thinking — an educational platform centered around a diagnostic assessment tool that identifies critical thinking gaps and recommends tailored learning modules.

## Development Commands

```bash
python manage.py runserver       # Start development server
python manage.py migrate         # Apply database migrations
python manage.py makemigrations  # Create new migrations
python manage.py collectstatic   # Compile static files (production)
```

**Runtime:** Python 3.12.10
**Database:** SQLite (development), PostgreSQL (production via `dj-database-url`)

## Architecture

### Apps

- **`config/`** — Django project settings, root URL conf, WSGI/ASGI
- **`pages/`** — Marketing pages (home, about, books, contact), robots.txt
- **`articles/`** — Markdown-based article system with Cloudinary image storage
- **`diagnostic/`** — Core product: multi-step assessment wizard with session state

### Diagnostic App (Core Product)

The diagnostic is a wizard that flows: `intro → questions → results → email → syllabus → pdf`

**Session state** is tracked with keys prefixed `diagnostic_v0_1_*`. Question order is randomized per session.

**Data is YAML-driven** (all in `diagnostic/`):
- `questions.yaml` — ~20 questions, each answer tagged with cognitive "breakpoints"
- `modules.yaml` — 16 modules mapped to breakpoints (e.g., "Paralysis Until Certainty")
- `resources.yaml` — Reading lists, videos, and exercises per module
- `module_pages/` — Markdown content for each module

**Scoring:** Answers are tallied against 16 predefined breakpoints; the top 2 determine which modules are recommended.

**Models:**
- `DiagnosticLead` — Captures user info (email, name, organization, selected modules)

### Articles App

- `Article` model stores content as Markdown with YAML front-matter
- Summaries are validated: must end with punctuation, max 2 sentences
- `ArticleImage` stores inline images on Cloudinary

### Static Content

`static/python-detective/` contains a standalone HTML/JS lesson application (Python Detective course) — `index.html` and `lesson-01.html` through `lesson-04.html`. These are self-contained and not part of the Django template system.

## Key Libraries

| Library | Purpose |
|---|---|
| WeasyPrint 68.1 | HTML→PDF (primary); falls back to ReportLab |
| Cloudinary | Media storage and delivery (production) |
| WhiteNoise 6.6 | Static file serving |
| markdown + BeautifulSoup4 | Article rendering + TOC generation |
| gunicorn | Production WSGI server |

## Deployment

Hosted on Heroku. Required environment variables for production:
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `CLOUDINARY_URL`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DATABASE_URL` (auto-set by Heroku Postgres)

The `Procfile` runs `python manage.py migrate --noinput` on release before starting `gunicorn config.wsgi`.
