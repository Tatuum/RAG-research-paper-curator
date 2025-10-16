from pathlib import Path
from pydantic import Field
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT_PATH = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT_PATH/ ".env"

class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
    )

class ArxivSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="ARXIV__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    base_url: str = "https://export.arxiv.org/api/query"
    pdf_cache_dir: str = "./data/arxiv_pdfs"
    rate_limit_delay: float = 3.0
    timeout_seconds: int = 30
    max_results: int = 15
    download_max_retries: int = 3
    download_retry_delay_base: float = 5.0
    search_category: str = "cs.AI"
    max_concurrent_downloads: int = 5
    max_concurrent_parsing: int = 1

    namespaces: dict = {
        "atom": "http://www.w3.org/2005/Atom",
       # "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

class PDFParserSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="PDF_PARSER__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    max_pages: int = 30
    max_file_size_mb: int = 20
    do_ocr: bool = False
    do_table_structure: bool = True
    
class Settings(BaseConfigSettings):
    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    #service_name: str = "rag-api"

    arxiv: ArxivSettings = Field(default_factory=ArxivSettings)
    pdf_parser: PDFParserSettings = Field(default_factory=PDFParserSettings)

def get_settings() -> Settings:
    return Settings()