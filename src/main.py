from sqlalchemy import text

from src.db.engine import get_engine


def main():
    engine = get_engine()
    with engine.connect() as conn:
        value = conn.execute(text("SELECT 1")).scalar()
    print("DB_OK:", value)


if __name__ == "__main__":
    main()
