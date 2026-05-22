from fastapi import HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from models.config import settings
from models.database import get_db_session

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-KEY header",
        )
    return api_key

def get_db() -> Session:
    # Helper dependency to yield db session cleanly
    return next(get_db_session())
