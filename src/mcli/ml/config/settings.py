"""Configuration management for ML system"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="ml_system.db", description="Database name")
    user: str = Field(default="", description="Database user")
    password: str = Field(default="", description="Database password")

    # Connection pool settings
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max connection overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")

    @property
    def url(self) -> str:
        """Get database URL"""
        # Use SQLite for local development if no user is specified
        if not self.user:
            return f"sqlite:///{self.name}"
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_url(self) -> str:
        """Get async database URL"""
        # Use aiosqlite for local development if no user is specified
        if not self.user:
            return f"sqlite+aiosqlite:///{self.name}"
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Redis configuration"""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")

    # Connection settings
    max_connections: int = Field(default=50, description="Max connections")
    socket_timeout: int = Field(default=5, description="Socket timeout")

    @property
    def url(self) -> str:
        """Get Redis URL"""
        auth_part = f":{self.password}@" if self.password else ""
        return f"redis://{auth_part}{self.host}:{self.port}/{self.db}"


class MLflowSettings(BaseSettings):
    """MLflow configuration"""

    model_config = SettingsConfigDict(env_prefix="MLFLOW_")

    tracking_uri: str = Field(
        default="http://localhost:5000", description="MLflow tracking server URI"
    )
    experiment_name: str = Field(
        default="politician_trading", description="Default experiment name"
    )
    artifact_root: Optional[str] = Field(default=None, description="Artifact storage root")

    # Authentication
    username: Optional[str] = Field(default=None, description="MLflow username")
    password: Optional[str] = Field(default=None, description="MLflow password")


class ModelSettings(BaseSettings):
    """Model configuration"""

    model_config = SettingsConfigDict(env_prefix="MODEL_")

    # Model paths
    model_dir: Path = Field(default=Path("models"), description="Model storage directory")
    cache_dir: Path = Field(default=Path("cache"), description="Model cache directory")

    # Training settings
    batch_size: int = Field(default=32, description="Training batch size")
    learning_rate: float = Field(default=0.001, description="Learning rate")
    epochs: int = Field(default=100, description="Training epochs")

    # Hardware settings
    device: str = Field(default="auto", description="Device to use (cpu, cuda, auto)")
    num_workers: int = Field(default=4, description="Number of worker processes")

    # Model serving
    serving_host: str = Field(default="0.0.0.0", description="Model serving host")
    serving_port: int = Field(default=8000, description="Model serving port")

    @field_validator("model_dir", "cache_dir", mode="before")
    @classmethod
    def validate_paths(cls, v):
        """Ensure paths are Path objects"""
        return Path(v) if not isinstance(v, Path) else v


class DataSettings(BaseSettings):
    """Data configuration"""

    model_config = SettingsConfigDict(env_prefix="DATA_")

    # Data paths
    data_dir: Path = Field(default=Path("data"), description="Data storage directory")
    raw_dir: Path = Field(default=Path("data/raw"), description="Raw data directory")
    processed_dir: Path = Field(
        default=Path("data/processed"), description="Processed data directory"
    )

    # DVC settings
    dvc_remote: str = Field(default="local", description="DVC remote storage")
    dvc_cache_dir: Path = Field(default=Path(".dvc/cache"), description="DVC cache directory")

    # Data processing
    chunk_size: int = Field(default=10000, description="Data processing chunk size")
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Max file size in bytes")

    @field_validator("data_dir", "raw_dir", "processed_dir", "dvc_cache_dir", mode="before")
    @classmethod
    def validate_paths(cls, v):
        """Ensure paths are Path objects"""
        return Path(v) if not isinstance(v, Path) else v


class APISettings(BaseSettings):
    """API configuration"""

    model_config = SettingsConfigDict(env_prefix="API_")

    # Server settings
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=1, description="Number of workers")

    # Security
    secret_key: str = Field(default="your-secret-key", description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiry in minutes")

    # Rate limiting
    rate_limit: int = Field(default=100, description="Requests per minute")

    # API Keys for external services
    alpha_vantage_key: Optional[str] = Field(default=None, description="Alpha Vantage API key")
    polygon_key: Optional[str] = Field(default=None, description="Polygon.io API key")
    quiver_key: Optional[str] = Field(default=None, description="QuiverQuant API key")


class MonitoringSettings(BaseSettings):
    """Monitoring configuration"""

    model_config = SettingsConfigDict(env_prefix="MONITORING_")

    # Metrics
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="structured", description="Log format (structured, plain)")

    # Alerting
    enable_alerts: bool = Field(default=True, description="Enable alerting")
    alert_webhook_url: Optional[str] = Field(default=None, description="Webhook URL for alerts")

    # Drift detection
    drift_check_interval: int = Field(default=3600, description="Drift check interval in seconds")
    drift_threshold: float = Field(default=0.05, description="Drift detection threshold")


class SecuritySettings(BaseSettings):
    """Security configuration"""

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    # Authentication
    enable_auth: bool = Field(default=True, description="Enable authentication")
    admin_username: str = Field(default="admin", description="Admin username")
    admin_password: str = Field(default="change_me", description="Admin password")

    # HTTPS
    ssl_cert_path: Optional[Path] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[Path] = Field(default=None, description="SSL key path")

    # CORS
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")

    @field_validator("ssl_cert_path", "ssl_key_path", mode="before")
    @classmethod
    def validate_ssl_paths(cls, v):
        """Ensure SSL paths are Path objects if provided"""
        return Path(v) if v and not isinstance(v, Path) else v


class Settings(BaseSettings):
    """Main application settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Environment
    environment: str = Field(
        default="development", description="Environment (development, staging, production)"
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    mlflow: MLflowSettings = Field(default_factory=MLflowSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    api: APISettings = Field(default_factory=APISettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value"""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._create_directories()

    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.model.model_dir,
            self.model.cache_dir,
            self.data.data_dir,
            self.data.raw_dir,
            self.data.processed_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy"""
        return {
            "pool_size": self.database.pool_size,
            "max_overflow": self.database.max_overflow,
            "pool_timeout": self.database.pool_timeout,
            "pool_pre_ping": True,
            "echo": self.debug,
        }

    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            "host": self.redis.host,
            "port": self.redis.port,
            "db": self.redis.db,
            "password": self.redis.password,
            "max_connections": self.redis.max_connections,
            "socket_timeout": self.redis.socket_timeout,
            "decode_responses": True,
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings


def update_settings(**kwargs) -> Settings:
    """Update settings with new values"""
    global settings

    # Create new settings instance with updated values
    current_dict = settings.model_dump()
    current_dict.update(kwargs)
    settings = Settings(**current_dict)

    return settings


# Environment-specific configurations
def get_development_config() -> Dict[str, Any]:
    """Get development-specific configuration overrides"""
    return {
        "debug": True,
        "database": {
            "host": "localhost",
            "name": "ml_system_dev",
        },
        "redis": {
            "db": 1,
        },
        "mlflow": {
            "tracking_uri": "http://localhost:5000",
        },
        "monitoring": {
            "log_level": "DEBUG",
            "enable_alerts": False,
        },
        "security": {
            "enable_auth": False,
        },
    }


def get_production_config() -> Dict[str, Any]:
    """Get production-specific configuration overrides"""
    return {
        "debug": False,
        "monitoring": {
            "log_level": "INFO",
            "enable_alerts": True,
        },
        "security": {
            "enable_auth": True,
            "cors_origins": ["https://yourdomain.com"],
        },
    }


def get_testing_config() -> Dict[str, Any]:
    """Get testing-specific configuration overrides"""
    return {
        "debug": True,
        "database": {
            "name": "ml_system_test",
        },
        "redis": {
            "db": 2,
        },
        "monitoring": {
            "enable_alerts": False,
            "enable_metrics": False,
        },
    }


# Configuration factory
def create_settings(environment: str = "development") -> Settings:
    """Create settings for specific environment"""
    base_config = {}

    if environment == "development":
        base_config.update(get_development_config())
    elif environment == "production":
        base_config.update(get_production_config())
    elif environment == "testing":
        base_config.update(get_testing_config())

    base_config["environment"] = environment
    return Settings(**base_config)


# Example usage and validation
if __name__ == "__main__":
    # Test settings loading
    print("Loading settings...")

    # Test different environments
    for env in ["development", "production", "testing"]:
        print(f"\n{env.upper()} Configuration:")
        env_settings = create_settings(env)
        print(f"  Debug: {env_settings.debug}")
        print(f"  Database URL: {env_settings.database.url}")
        print(f"  Redis URL: {env_settings.redis.url}")
        print(f"  Model Dir: {env_settings.model.model_dir}")

    # Test validation
    try:
        invalid_settings = Settings(environment="invalid")
    except ValueError as e:
        print(f"\nValidation working: {e}")

    print("\nSettings validation complete!")
