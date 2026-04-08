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

Default demo account:

- `admin / admin123`

## Deployment note

- Locally, the app uses SQLite.
- On Render, the app uses `DATABASE_URL` from Neon automatically.
- Demo admin user and hospitals are created automatically on startup.