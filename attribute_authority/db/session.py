from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

from ..core.config import settings

sqlalchemy_database_uri = settings.SQLALCHEMY_DATABASE_URI
print(f"Using SQLAlchemy database URI: {sqlalchemy_database_uri}")

engine = create_engine(
    sqlalchemy_database_uri,
    pool_pre_ping=True,
    json_serializer=lambda obj: obj  # Ensures proper JSON handling
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async database session for better performance
async_engine = create_async_engine(
    sqlalchemy_database_uri.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    future=True,
)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Async dependency to get DB session
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session