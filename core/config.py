"""
Configuration management for SignalWatch
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Keys
    COMPANIES_HOUSE_API_KEY = os.getenv('COMPANIES_HOUSE_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    XAI_API_KEY = os.getenv('XAI_API_KEY', '')
    OPENCORPORATES_API_KEY = os.getenv('OPENCORPORATES_API_KEY', '')
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', 600))
    RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', 300))  # 5 minutes
    
    # Flask
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Directories
    BASE_DIR = Path(__file__).parent
    DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
    CACHE_DIR = Path(os.getenv('CACHE_DIR', BASE_DIR / 'cache'))
    EXPORTS_DIR = Path(os.getenv('EXPORTS_DIR', BASE_DIR / 'exports'))
    TEMPLATES_DIR = BASE_DIR / 'templates'
    STATIC_DIR = BASE_DIR / 'static'
    
    # Companies House API
    CH_BASE_URL = 'https://api.company-information.service.gov.uk'
    CH_DOCUMENT_URL = 'https://document-api.company-information.service.gov.uk'
    
    # OpenCorporates API
    OC_BASE_URL = 'https://api.opencorporates.com/v0.4'
    
    # GitHub Storage
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    
    # Processing settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    BATCH_SIZE = 50
    CHECKPOINT_INTERVAL = 10  # Save checkpoint every N companies
    
    # PDF Processing
    OCR_LANGUAGE = 'eng'
    PDF_DPI = 300
    
    # AI Model Selection (for PDF extraction)
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'xai')  # 'openai' or 'xai'
    XAI_MODEL = os.getenv('XAI_MODEL', 'grok-2-vision-1212')  # Vision model for image inputs
    XAI_BASE_URL = 'https://api.x.ai/v1'
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        for directory in [cls.DATA_DIR, cls.CACHE_DIR, cls.EXPORTS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_api_key(cls):
        """Check if Companies House API key is configured"""
        if not cls.COMPANIES_HOUSE_API_KEY:
            raise ValueError(
                "COMPANIES_HOUSE_API_KEY not found. "
                "Please set it in .env file or environment variables."
            )
        return True
