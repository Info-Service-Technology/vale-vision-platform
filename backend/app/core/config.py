from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Vale Vision API"
    environment: str = "dev"
    frontend_public_url: str = "http://localhost:5174"
    api_public_url: str = "http://localhost:8000"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_db: str = "vale_vision"
    mysql_user: str = "app"
    mysql_password: str = "123456"
    aws_region: str = "sa-east-1"
    s3_bucket_raw: str = ""
    s3_bucket_debug: str = ""
    jwt_secret_key: str = "trocar-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480
    password_reset_token_expire_minutes: int = 60
    email_enabled: bool = False
    email_from_name: str = "SensX Vision Platform"
    email_from_address: str = "no-reply@sensxvisionplatform.com"
    email_reply_to: str | None = None
    email_support_address: str | None = None
    email_debug_return_tokens: bool = True
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
