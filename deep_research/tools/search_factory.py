import importlib
import os
from typing import Any, Dict, Protocol
from deep_research.utils import load_config
from deep_research.llm import DEFAULT_STAGE
from tavily import TavilyClient
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

class SearchConfigError(ValueError):
    """Define the Exception class for search"""
    pass

class SearchProvider(Protocol):
    def build_client(self, provider_cfg: Dict[str, Any]) -> Any:
        pass
    # The bare * in the parameter list is a keyword-only marker: every parameter after it must be passed by name, never positionally.
    def search(self,
               client: Any,
               query: str,
               *,
               max_results: int,
               include_new_content: bool,
               topic: str,
               timeout_seconds: int | None):
        pass

    def defaults(self, provider_cfg: Dict[str, Any]) -> Dict[str, Any]:
        pass


_SEARCH_CLIENT_CACHE: Dict[tuple[str, str, str], Any] = {}
# config path, backend(tavily)
_PROVIDER_CACHE: Dict[tuple[str, str], SearchProvider] = {}
# config path, stage, backend
_PROVIDER_REGISTRY: Dict[str, SearchProvider] = {}
def register_provider(name: str,  provider: SearchProvider) -> None:
    _PROVIDER_REGISTRY[name.lower()] = provider

def overried_provider(name: str, provider: SearchProvider, *, clear_cache: bool = True) -> None:
    provider_name = name.lower()
    _PROVIDER_REGISTRY[provider_name] = provider
    if not clear_cache:
        return

    for key in [k for k in list(_PROVIDER_CACHE) if k[1] == provider_name]:
        _PROVIDER_CACHE.pop(key, None)

    for key in [k for k in list(_SEARCH_CLIENT_CACHE) if k[2] == provider_name]:
        _SEARCH_CLIENT_CACHE.pop(key, None)


def _resolve_stage(stage: str | None) -> str:
    return stage or os.environ.get("STAGE") or DEFAULT_STAGE

def _load_stage_config(stage: str | None):
    stage_name = _resolve_stage(stage)
    config_path = os.environ.get("CONFIG_PATH", "config.yml")
    cfg = load_config(stage_name, config_path)
    if cfg is None:
        raise SearchConfigError(f"No config found for stage '{stage_name}'")
    return cfg

def _get_search_cfg(stage: str | None) -> Dict[str, Any]:
    cfg = _load_stage_config(stage)
    search_cfg = cfg.search
    if not search_cfg:
        raise SearchConfigError("Missing 'search' configuration block for this stage")
    return search_cfg

class TavilyProvider:
    def build_client(self, provider_cfg: Dict[str, Any]) -> TavilyProvider:
        kwargs: Dict[str: Any] = {}
        if provider_cfg.get("api_key"):
            kwargs["api_key"] = provider_cfg["api_key"]
        base_url = provider_cfg.get("api_base_url") or provider_cfg.get("base_url")
        if base_url:
            kwargs["base_url"] = base_url
        timeout_seconds = provider_cfg.get("timeout_seconds")
        if timeout_seconds is not None:
            kwargs["timeout"] = timeout_seconds
        try:
            return TavilyClient(**kwargs)
        except TypeError:
            kwargs.pop("timeout", None)
            return TavilyClient(**kwargs)

    def search(self,
               client: TavilyClient,
               query: str,
               *,
               max_results: int,
               include_raw_content: bool,
               topic: str,
               timeout_seconds: int | None,
               ) -> Any:
        search_kwargs: Dict[str, Any] = {
            "max_results": max_results,
            "include_raw_content": include_raw_content,
            "topic": topic,
            "country": "united states",
        }
        if timeout_seconds is not None:
            search_kwargs["timeout"] = timeout_seconds
        return client.search(query, **search_kwargs)

    def defaults(self, provider_cfg: Dict[str, Any]) -> Dict[str, Any]:
        # max_results、topic、include_raw_content are from tavily
        defaults = {
            "max_results": 3,
            "topic": "general",
            "include_raw_content": True,
            "timeout_seconds": None,
        }
        defaults.update({k: provider_cfg.get(k, defaults[k]) for k in defaults})
        return defaults

# register tavily client. executes when the module is loaded
register_provider("tavily", TavilyProvider())

def _maybe_import_provider(backend: str) -> None:
    """dynamically import the provider when necessary.
    Only matters if users define new search engine, in addition to tavily"""
    module_candidates = [
        f"deep_research.providers.{backend}",
        f"deep_research_search_{backend}",
        backend
    ]

    for mod_name in module_candidates:
        try:
            module = importlib.import_module(mod_name)
            logger.debug("Imported module '%s' for backend '%s'", mod_name, backend)
        except Exception as exc:  # pragma: no cover - import guards
            logger.debug("Module import failed for '%s' (backend='%s'): %s", mod_name, backend, exc)
            continue

        # 实现provider自注册
        provider_obj = getattr(module, "PROVIDER", None)
        if provider_obj is not None:
            logger.debug("Registering provider via PROVIDER attribute for backend '%s'", backend)
            register_provider(backend, provider_obj)

        # 或者实现一个显式的注册hook
        register_fn = getattr(module, "register_search_provider", None) or getattr(module, "register_provider", None)
        if callable(register_fn):
            logger.debug("Invoking registration hook in module '%s' for backend '%s'", mod_name, backend)
            register_fn(register_provider)

        if backend.lower() in _PROVIDER_REGISTRY:
            logger.debug("Provider resolved for backend '%s' after importing '%s'", backend, mod_name)
            return

    logger.warning("No provider registered after attempting imports for backend '%s'", backend)

# return search backend name, and search backend
def _get_provider(search_cfg: Dict[str, Any]) -> tuple[str, SearchProvider]:
    backend = (search_cfg.get("backend") or "tavily").lower()
    cache_key = (os.environ.get("CONFIG_PATH", "config.yml"), backend)
    if cache_key in _PROVIDER_CACHE:
        logger.debug("Using cached provider '%s'", backend)
        return backend, _PROVIDER_CACHE[cache_key]
    provider = _PROVIDER_REGISTRY.get(backend)
    if provider is None:
        logger.info("No registered provider for backend='%s'; attempting dynamic import", backend)
        _maybe_import_provider(backend)
        provider = _PROVIDER_REGISTRY.get(backend)
    if provider is None:
        raise SearchConfigError(
            f"Unsupported search backend '{backend}'. "
            "Ensure the provider module register a provider via override_provider/register_provider."
        )
    _PROVIDER_CACHE[cache_key] = provider
    logger.debug("Search provider resolved and cached for backend='%s'", backend)
    return backend, provider

def get_search_client(*, stage: str | None = None):
    stage_name = _resolve_stage(stage)
    search_cfg = _get_search_cfg(stage_name)
    backend, provider = _get_provider(search_cfg)

    cache_key = (os.environ.get("CONFIG_PATH", "config.yml"), stage_name, backend)
    if cache_key in _SEARCH_CLIENT_CACHE:
        logger.debug("Using cached search client for backend='%s' stage='%s'", backend, stage_name)
        return _SEARCH_CLIENT_CACHE[cache_key]
    backend_cfg = search_cfg.get(backend, {}) if isinstance(search_cfg, dict) else {}
    if not isinstance(backend_cfg, dict):
        raise SearchConfigError(
            f"Search config for backend '{backend}' must be a mapping, got {type(backend_cfg).__name__}"
        )
    logger.info(f"Using backend '{backend}' for stage '{stage_name}'")
    try:
        client = provider.build_client(backend_cfg)
    except Exception as exc:
        logger.exception(f"Failed to build client for stage '{stage_name}' with exception {exc}")
        raise
    _SEARCH_CLIENT_CACHE[cache_key] = client
    return client

def get_search_provider(*, stage: str | None = None) -> SearchProvider:
    search_cfg = _get_search_cfg(stage)
    _, provider = _get_provider(search_cfg)
    return provider

def get_search_defaults(*, stage: str | None = None) -> Dict[str, Any]:
    search_cfg = _get_search_cfg(stage)
    backend, provider = _get_provider(search_cfg)
    backend_cfg = search_cfg.get(backend, {}) if isinstance(search_cfg, dict) else {}
    if not isinstance(backend_cfg, dict):
        raise SearchConfigError(
            f"Search config for backend '{backend}' must be a mapping, got {type(backend_cfg).__name__}"
        )
    return provider.defaults(backend_cfg)

def clear_cache() -> None:
    _SEARCH_CLIENT_CACHE.clear()
    _PROVIDER_CACHE.clear()
