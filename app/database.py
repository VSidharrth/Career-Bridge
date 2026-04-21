from pymongo import MongoClient
from app.config import settings

client = None
db = None


def connect_db():
    """Connect to MongoDB and create indexes."""
    global client, db
    client = MongoClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        socketTimeoutMS=8000,
    )
    db = client[settings.DB_NAME]
    try:
        # Force server selection so configuration/network errors fail fast.
        client.admin.command("ping")
        # Create indexes
        db.users.create_index("email", unique=True)
        db.profiles.create_index("user_id", unique=True)
        db.jobs.create_index("skills_required")
        db.applications.create_index(
            [("job_id", 1), ("candidate_id", 1)], unique=True
        )
    except Exception as exc:
        raise RuntimeError(
            "MongoDB connection failed. Verify MONGO_URI and Atlas network access allowlist."
        ) from exc
    print(f"[OK] Connected to MongoDB: {settings.DB_NAME}")


def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("[OK] MongoDB connection closed")


def get_db():
    """Return database instance."""
    return db
