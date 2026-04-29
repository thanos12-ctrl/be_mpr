"""
Database connection and utilities
"""
import databases
import sqlalchemy
from config import settings

# Database instance
database = databases.Database(settings.DATABASE_URL)

# SQLAlchemy metadata (for raw queries if needed)
metadata = sqlalchemy.MetaData()


async def connect_db():
    """Connect to database"""
    await database.connect()
    print("[SUCCESS] Database connected")


async def disconnect_db():
    """Disconnect from database"""
    await database.disconnect()
    print("[OFF] Database disconnected")


async def get_db():
    """Dependency for database access"""
    return database
