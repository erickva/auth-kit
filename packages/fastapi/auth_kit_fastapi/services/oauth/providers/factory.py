"""
OAuth provider factory.

Creates and caches OAuth provider instances based on configuration.
"""

from typing import Dict, List, Optional, Type

from .base import OAuthProvider
from .google import GoogleProvider
from .github import GitHubProvider
from .apple import AppleProvider


# Registry of available providers
PROVIDER_REGISTRY: Dict[str, Type[OAuthProvider]] = {
    "google": GoogleProvider,
    "github": GitHubProvider,
    "apple": AppleProvider,
}

# Cache for provider instances
_provider_cache: Dict[str, OAuthProvider] = {}


def get_provider(
    provider_name: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    team_id: Optional[str] = None,
    key_id: Optional[str] = None,
    private_key: Optional[str] = None,
    config: Optional[object] = None,
    use_cache: bool = True,
) -> OAuthProvider:
    """
    Get or create an OAuth provider instance.

    Args:
        provider_name: Name of the provider (google, github, apple)
        client_id: OAuth client ID (or from config)
        client_secret: OAuth client secret (or from config)
        team_id: Apple Team ID (Apple only)
        key_id: Apple Key ID (Apple only)
        private_key: Apple private key (Apple only)
        config: AuthConfig object to read credentials from
        use_cache: Whether to cache provider instances

    Returns:
        Configured OAuthProvider instance

    Raises:
        ValueError: If provider not found or misconfigured
    """
    provider_name = provider_name.lower()

    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown OAuth provider: {provider_name}. Available: {available}"
        )

    # Return cached instance if available
    if use_cache and provider_name in _provider_cache:
        return _provider_cache[provider_name]

    # Get credentials from config if provided
    if config is not None:
        creds = _get_credentials_from_config(config, provider_name)
        client_id = client_id or creds.get("client_id")
        client_secret = client_secret or creds.get("client_secret")
        team_id = team_id or creds.get("team_id")
        key_id = key_id or creds.get("key_id")
        private_key = private_key or creds.get("private_key")

    # Validate required credentials
    if not client_id:
        raise ValueError(f"client_id required for {provider_name} provider")

    # Create provider instance
    provider_class = PROVIDER_REGISTRY[provider_name]

    if provider_name == "apple":
        if not all([team_id, key_id, private_key]):
            raise ValueError(
                "Apple provider requires team_id, key_id, and private_key"
            )
        provider = provider_class(
            client_id=client_id,
            team_id=team_id,
            key_id=key_id,
            private_key=private_key,
        )
    else:
        if not client_secret:
            raise ValueError(f"client_secret required for {provider_name} provider")
        provider = provider_class(
            client_id=client_id,
            client_secret=client_secret,
        )

    # Cache the instance
    if use_cache:
        _provider_cache[provider_name] = provider

    return provider


def _get_credentials_from_config(config: object, provider_name: str) -> Dict[str, str]:
    """
    Extract provider credentials from AuthConfig.

    Args:
        config: AuthConfig object
        provider_name: Provider name

    Returns:
        Dictionary of credentials
    """
    if hasattr(config, "get_oauth_provider_credentials"):
        return config.get_oauth_provider_credentials(provider_name)

    # Fallback to direct attribute access
    creds = {}

    if provider_name == "google":
        creds["client_id"] = getattr(config, "oauth_google_client_id", None)
        creds["client_secret"] = getattr(config, "oauth_google_client_secret", None)
    elif provider_name == "github":
        creds["client_id"] = getattr(config, "oauth_github_client_id", None)
        creds["client_secret"] = getattr(config, "oauth_github_client_secret", None)
    elif provider_name == "apple":
        creds["client_id"] = getattr(config, "oauth_apple_client_id", None)
        creds["team_id"] = getattr(config, "oauth_apple_team_id", None)
        creds["key_id"] = getattr(config, "oauth_apple_key_id", None)
        creds["private_key"] = getattr(config, "oauth_apple_private_key", None)

    return {k: v for k, v in creds.items() if v is not None}


def get_available_providers(config: Optional[object] = None) -> List[str]:
    """
    Get list of configured/available OAuth providers.

    Args:
        config: Optional AuthConfig to check which providers are configured

    Returns:
        List of provider names that are available
    """
    if config is None:
        return list(PROVIDER_REGISTRY.keys())

    # Check which providers have credentials configured
    available = []

    for provider_name in PROVIDER_REGISTRY.keys():
        try:
            creds = _get_credentials_from_config(config, provider_name)
            if creds.get("client_id"):
                # For Apple, also check required fields
                if provider_name == "apple":
                    if all([
                        creds.get("team_id"),
                        creds.get("key_id"),
                        creds.get("private_key"),
                    ]):
                        available.append(provider_name)
                else:
                    if creds.get("client_secret"):
                        available.append(provider_name)
        except Exception:
            continue

    return available


def clear_provider_cache() -> None:
    """Clear the provider instance cache. Useful for testing."""
    global _provider_cache
    _provider_cache = {}


def is_provider_available(provider_name: str) -> bool:
    """
    Check if a provider is registered.

    Args:
        provider_name: Provider name to check

    Returns:
        True if provider is available
    """
    return provider_name.lower() in PROVIDER_REGISTRY
