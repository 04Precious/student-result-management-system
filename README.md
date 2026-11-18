# Student Result Management System — Shoolini Online

A Flask + SQLite academic project with student, subject, marks, result, admin login and student result lookup modules.

## Run locally
1. Create/activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables for production (recommended): `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
4. Run: `python app.py`
5. Visit `http://127.0.0.1:5000/login` for admin or `/student` for the student lookup portal.

Default development credentials (local only): `admin` / `admin123`. Change these before public deployment.

## Deployment notes
- Set a strong random `SECRET_KEY` and unique admin username/password in the host's environment settings.
- Configure `DATABASE_PATH` to a persistent disk location if the hosting provider's filesystem is ephemeral.
- Student access by roll number alone is demonstration-level and is not suitable for real sensitive student records without additional verification.
- Do not upload the database, secrets, or virtual environment to GitHub.
