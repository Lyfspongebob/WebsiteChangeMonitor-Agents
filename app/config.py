import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_db: str
    output_dir: str
    request_timeout: int
    log_level: str


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    # 优先从项目根目录的 .env 加载，避免在不同 cwd 下运行时读取失败
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        # override=True: 若系统环境变量里存在同名空值，也允许被 .env 正确覆盖
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)
    _settings = Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        mysql_host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
        mysql_user=os.getenv("MYSQL_USER", "root"),
        mysql_password=os.getenv("MYSQL_PASSWORD", ""),
        mysql_db=os.getenv("MYSQL_DB", "web_monitor"),
        output_dir=os.getenv("OUTPUT_DIR", "outputs"),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
    return _settings
