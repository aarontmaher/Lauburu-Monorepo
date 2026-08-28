"""
Application configuration management using Pydantic settings.
"""

from typing import List
import os

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, ConfigDict
except (ImportError, Exception):
    from pydantic import BaseModel as BaseSettings, Field, ConfigDict  # type: ignore


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hemodynamic Cloud Server"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8085
    LOG_LEVEL: str = "INFO"
    
    # Zero-PII Cryptographic Key
    ZERO_PII_HMAC_SECRET: str = "lauburu_hemodynamic_private_key_2026"
    
    # Database Paths
    SQLITE_DB_PATH: str = os.getenv(
        "SQLITE_DB_PATH",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sqlite", "hemodynamic_sessions.db")
    )
    CHROMADB_DIR: str = os.getenv(
        "CHROMADB_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chromadb")
    )
    
    # CORS Origins
    CORS_ORIGINS: List[str] = ["*"]
    
    # AI Mesh Endpoints & Model Routing
    DEEPSEEK_R1_URL: str = os.getenv("DEEPSEEK_R1_URL", "http://100.101.39.98:8081/v1/chat/completions")
    QWEN3_VL_URL: str = os.getenv("QWEN3_VL_URL", "http://100.101.39.98:8080/v1/chat/completions")
    QWEN_CODER_URL: str = os.getenv("QWEN_CODER_URL", "http://100.101.39.98:8084/v1/chat/completions")
    GEMINI_FALLBACK_URL: str = os.getenv("GEMINI_FALLBACK_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    LLM_CONNECT_TIMEOUT_SEC: float = 3.0
    LLM_READ_TIMEOUT_SEC: float = 45.0
    
    # Biometric Inversion Calibration Parameters
    NOMINAL_BLOOD_DENSITY_KG_M3: float = 1055.0
    NOMINAL_PATH_LENGTH_M: float = 0.85
    NOMINAL_BLOOD_VOLUME_M3: float = 0.0010  # 1.0 L arterial blood volume
    E_REF_KPA: float = 400.0
    
    A_SBP: float = -50.0
    B_SBP: float = 22.0
    C_SBP: float = 45.0
    K_HR_SBP: float = 0.18
    
    A_DBP: float = -30.0
    B_DBP: float = 14.0
    C_DBP: float = 35.0
    K_HR_DBP: float = 0.08
    
    K_MOTION: float = 0.05

    model_config = ConfigDict(
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
