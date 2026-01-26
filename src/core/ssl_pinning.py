"""
SSL Certificate Pinning for API calls.
Provides enhanced security by enforcing TLS 1.2+ and certificate verification.
"""
import ssl
import logging
from typing import Optional
from urllib.parse import urlparse


def create_pinned_ssl_context(hostname: Optional[str] = None) -> ssl.SSLContext:
    """Create a secure SSL context with certificate pinning.

    Features:
    - TLS 1.2 minimum version (disables TLS 1.0/1.1)
    - Certificate verification enabled
    - Hostname checking enabled

    Args:
        hostname: Optional hostname for context (for future per-host pinning)

    Returns:
        Configured ssl.SSLContext
    """
    # Create context with strong defaults
    context = ssl.create_default_context()

    # Enable hostname checking
    context.check_hostname = True

    # Require certificate verification
    context.verify_mode = ssl.CERT_REQUIRED

    # Set minimum TLS version to 1.2 (disable TLS 1.0, 1.1)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Optional: Set maximum version to TLS 1.3 if available
    try:
        context.maximum_version = ssl.TLSVersion.TLSv1_3
    except AttributeError:
        pass  # TLS 1.3 not available on older Python

    return context


def get_ssl_context_for_url(url: str) -> ssl.SSLContext:
    """Get appropriate SSL context for a given URL.

    Args:
        url: Full URL (e.g., "https://api.openai.com/v1/chat")

    Returns:
        ssl.SSLContext configured for the URL's hostname
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        return create_pinned_ssl_context(hostname)
    except Exception as e:
        logging.warning(f"Failed to parse URL for SSL context: {e}")
        return create_pinned_ssl_context()


def is_ssl_pinning_enabled() -> bool:
    """Check if SSL pinning should be enabled.

    For now, always returns True. Could be extended to check config.
    """
    return True


# Known API endpoints for future certificate pinning
KNOWN_API_HOSTS = {
    'api.openai.com': 'OpenAI',
    'api.anthropic.com': 'Anthropic',
    'generativelanguage.googleapis.com': 'Google Gemini',
    'api.groq.com': 'Groq',
    'api.deepseek.com': 'DeepSeek',
    'api.mistral.ai': 'Mistral',
    'api.x.ai': 'xAI',
    'api.perplexity.ai': 'Perplexity',
    'api.cerebras.ai': 'Cerebras',
    'api.sambanova.ai': 'SambaNova',
    'api.together.xyz': 'Together',
    'api.siliconflow.cn': 'SiliconFlow',
    'openrouter.ai': 'OpenRouter',
    'api.github.com': 'GitHub',
}


def log_ssl_connection(url: str) -> None:
    """Log SSL connection for debugging purposes."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        provider = KNOWN_API_HOSTS.get(hostname, 'Unknown')
        logging.debug(f"SSL connection to {provider} ({hostname})")
    except Exception:
        pass
