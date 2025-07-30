from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, PostgresDsn, field_validator, ValidationInfo
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Attribute Authority API"
    API_V1_STR: str = "/api/v1"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[str, List[AnyHttpUrl]] = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and v:
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []
    
    # Database Connection
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "userinfo"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> Any: # pylint: disable=no-self-argument
        if not v.strip():
            v = None
        elif isinstance(v, str):
            return v
        
        # Convert port to integer
        port_str = info.data.get("POSTGRES_PORT")
        port = int(port_str) if port_str else None
        
        return str(PostgresDsn.build(
            scheme="postgresql",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_SERVER"),
            port=port,
            path=f"{info.data.get('POSTGRES_DB') or ''}",
        ))
    
    # OIDC Configuration
    TRUSTED_OP_LIST: str = ""  # Comma-separated list of trusted OPs
    # TOKEN_CACHE_LIFETIME: int = 120  # seconds

    LOG_LEVEL: str = "INFO"

    @field_validator("LOG_LEVEL", mode="before")
    def validate_log_level(cls, v: Optional[str]) -> str: # pylint: disable=no-self-argument
        if v is None:
            return "INFO"
        return str(v).upper()
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
