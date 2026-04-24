from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Vale Vision API"
    environment: str = "dev"
    mysql_host: str = "localhost"
    mysql_port: int = 3307
    mysql_db: str = "vale_vision"
    mysql_user: str = "app"
    mysql_password: str = "123456"
    aws_region: str = "sa-east-1"
    s3_bucket_raw: str = ""
    s3_bucket_debug: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
