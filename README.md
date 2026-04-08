# Emergency Hospital Request System

Flask application for citizens, hospital staff, and admins to manage emergency requests.

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

## Seed admin user

```bash
python seed.py
```

Default demo accounts:

- `admin / admin123`

## Deployment note

Locally, the app uses SQLite. On a hosting platform, if `DATABASE_URL` is set, the app uses that database automatically.
