#***********************************************
#      Filename: llm.py
#***********************************************


from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from deep_research.utils import load_config
from deep_research.configmodels import StageConfig, RoleConfig
from pathlib import Path

DEFAULT_STAGE = "prod"
# the key is used to distinguish the stage, and config path
_CONFIG_CACHE: Dict[tuple[str, str], StageConfig] = {}
logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # deep_research/utils.py → project root

def get_chat_model(role: str, *, stage: str | None = None, max_tokens: str | None = None) -> BaseChatModel:
    config_path = os.environ.get("CONFIG_PATH", str(PROJECT_ROOT / "config.yml"))
    resolved_stage = _resolve_stage(stage)
    cfg = load_config(resolved_stage, config_path)
    roles_config = cfg.roles
    if role not in roles_config:
        _CONFIG_CACHE.clear()
        _CONFIG_CACHE = load_config(stage, config_path)
        roles_config = _CONFIG_CACHE.roles
    role_config = roles_config[role]
    backend = role_config.backend
    handle = role_config.handle
    if not backend or not handle:
        raise LLMConfigError(f"Role '{role}' is missing backend or handle")
    # stages:
    # prod:
    # cognition:
    # openai:
    # base_url: https: // api.openai.com / v1
    # api_key: xxxx
    # organization: xxxxx
    # default_model: gpt - 5.4 - mini
    # temperature: 0
    # timeout_seconds: 600
    # models:
    # gpt - 5.4 - mini:
    # max_tokens: 128000
    api_cfg = cfg.cognition.get(backend)
    if api_cfg is None:
        raise LLMConfigError(f"api config is missing for backend '{backend}'")
    resolved_timeout = _resolve_timeout_seconds(api_cfg, role_config)
    logger.info(
        "Selected cognition backend '%s' for role '%s' with handle '%s' (timeout=%s)",
        backend,
        role,
        handle,
        resolved_timeout,
    )
    resolved_max_tokens = max_tokens
    if max_tokens is not None:
        resolved_max_tokens = _resolve_config_max_tokens(api_cfg, handle)
    build_kwargs = _build_kwargs
    kwargs: Dict[str, Any] = build_kwargs(
        backend=backend,
        handle=handle,
        api_cfg=api_cfg,
        max_tokens=resolved_max_tokens,
        timeout_seconds=resolved_timeout,
    )

    return init_chat_model(**kwargs)

def _resolve_stage(stage: str | None):
    return stage or os.environ.get("STAGE") or DEFAULT_STAGE

def _load_stage_config(stage_name, path) -> StageConfig:
    cache_key = (os.environ.get("CONFIG_PATH", "config.yml"), stage_name, id(load_config))
    if cache_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[cache_key]
    cfg = load_config(stage_name, path)
    if cfg is None:
        raise LLMConfigError(f"No config found for stage '{stage_name}'")
    _CONFIG_CACHE[cache_key] = cfg
    return cfg

def _build_kwargs(
        backend: str,
        handle: str,
        api_cfg: Dict[str: Any],
        max_tokens : int | None,
        timeout_seconds: int | None) -> Dict[str: Any]:
    if backend == 'openai':
        return _build_openai_kwargs(
            handle=handle,
            api_cfg=api_cfg,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    else:
        raise LLMConfigError(f"Unsupported backend '{backend}'")

def _build_openai_kwargs(
        handle: str,
        api_cfg: Dict[str, Any],
        max_tokens: int | None,
        timeout_seconds: int | None
) -> Dict[str, Any]:
     # https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI
     model = handle or api_cfg.get("default_model")
     if not model:
         raise LLMConfigError(f"No model found for handle '{handle}'")

     kwargs: Dict[str, Any] = {
         "model": model,
     }
     for key in ("api_key", "base_url", "organization"):
         if api_cfg.get(key):
             kwargs[key] = api_cfg[key]
    # need to distinguish 0 and None
     if api_cfg.get("temperature") is not None:
        kwargs["temperature"] = api_cfg.get("temperature")
     if max_tokens is not None:
         kwargs["max_tokens"] = max_tokens
     if timeout_seconds is not None:
         kwargs["timeout"] = timeout_seconds
         kwargs["request_timeout"] = timeout_seconds
     model_kwargs: Dict[str, Any] = {}
     if model_kwargs:
         kwargs["model_kwargs"] = model_kwargs
     return kwargs

def _resolve_config_max_tokens(api_cfg: Dict[str, Any], handle: str) -> int | None:
    models_cfg = api_cfg.get("models") or {}
    model_cfg = models_cfg.get(handle) or {}
    return model_cfg.get("max_tokens")

def _resolve_timeout_seconds(api_cfg: Dict[str, Any], role_cfg: RoleConfig) -> int | None:
    if role_cfg.timeout_seconds is not None:
        return role_cfg.timeout_seconds
    for cfg in (role_cfg, api_cfg):
        if cfg.get("timeout_seconds") is not None:
          return cfg.get(key)
    return None

class LLMConfigError(ValueError):
    pass



