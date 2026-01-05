from sqlalchemy import create_engine

from src.config.settings import Settings


def get_engine():
    settings = Settings()
    return create_engine(settings.db_url, pool_pre_ping=True)
