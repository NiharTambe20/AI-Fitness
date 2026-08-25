from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

# Configure SQLite specific connection arguments if using SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy database session.
    Automatically closes session after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_exercises(db):
    """
    Idempotently seeds the 20 exercises from Member 3 ExerciseRegistry into the exercises table.
    """
    from exercises import ExerciseRegistry
    from backend.models.exercise import ExerciseModel

    registered_exercises = ExerciseRegistry.list_exercises()
    seeded_count = 0

    for key, name in registered_exercises:
        existing = db.query(ExerciseModel).filter(ExerciseModel.name == name).first()
        if not existing:
            exercise = ExerciseModel(
                name=name,
                description=f"{name} exercise tracker powered by YOLO Pose",
                difficulty="Intermediate"
            )
            db.add(exercise)
            seeded_count += 1

    if seeded_count > 0:
        db.commit()
        print(f"[INFO] Seeded {seeded_count} new exercises into the database.")

def _migrate_user_table():
    """
    Ensures newly added user columns exist in SQLite users table.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        with engine.begin() as conn:
            if "password_hash" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            if "age" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN age INTEGER"))
            if "height" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN height FLOAT"))
            if "weight" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN weight FLOAT"))
            if "gender" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN gender VARCHAR(50)"))
            if "updated_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))

def init_db():
    """
    Creates database tables and triggers idempotent seed routines.
    """
    # Import all models to ensure they are registered with Base metadata
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_user_table()

    db = SessionLocal()
    try:
        seed_exercises(db)
    finally:
        db.close()


