from src.config import Settings


def test_settings_initialization():
    """Test settings can be initialized."""
    settings = Settings()

    assert settings.app_version == "0.1.0"
    assert settings.debug is True
    assert settings.environment == "development"
    assert settings.service_name == "rag-api"


def test_settings_arxiv_defaults():
    """Test ArXiv default configuration."""
    settings = Settings()
    assert settings.arxiv.base_url == "https://export.arxiv.org/api/query"
    assert settings.arxiv.max_results == 15


def test_settings_pdf_parser_defaults():
    """Test PDF parser default configuration."""
    settings = Settings()
    assert settings.pdf_parser.max_file_size_mb == 20
