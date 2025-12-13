"""
Hybrid tools combining best features from both projects.
Now with async support, connection pooling, caching, and enhanced error handling!
"""

from .web_scraper import get_rendered_html
from .code_executor import run_code
from .send_request import post_request, reset_submission_tracking, get_wrong_questions, get_quiz_summary
from .download_file import download_file
from .add_dependencies import add_dependencies
from .audio_transcriber import transcribe_audio
from .context_extractor import extract_context
from .image_analyzer import analyze_image
from .data_visualizer import create_visualization, create_chart_from_data, get_last_base64

# Optimized modules
from .http_client import get_http_client, close_http_client
from .cache_manager import get_html_cache
from .error_utils import create_error_response, get_http_error_suggestion, analyze_code_error

__all__ = [
    "get_rendered_html",
    "run_code",
    "post_request",
    "download_file",
    "add_dependencies",
    "transcribe_audio",
    "extract_context",
    "analyze_image",
    "create_visualization",
    "create_chart_from_data",
    "get_last_base64",
    "http_client",
    "cache_manager",
    "reset_submission_tracking",
    "get_wrong_questions",
    "get_quiz_summary",
    "get_html_cache",
    "create_error_response",
    "get_http_error_suggestion",
    "analyze_code_error",
]
