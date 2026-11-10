# Persistence rules
- Only repositories touch the DB (SQLAlchemy) and blob storage; services call repositories.
- Models live in `app/models.py`; never hard-code `DATABASE_URL` (env var, default SQLite in `backend/data/`).
- Blob storage is a swappable class (local folder now, S3/Azure later); store pointers in SQL, files in blob.
