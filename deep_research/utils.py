#***********************************************
#      Filename: utils.py
#   Description: Until functions
#***********************************************
import os
import yaml
from datetime import datetime
from deep_research.configmodels import StageConfig

from typing import Any

def get_today_str() -> str:
    # return a date in the format of Sun Jul 5, 2026
    # a: weekday name, abbreviated
    # b: month name, abbreviated
    # %-d: day of month, no leading zero
    # %Y: 4-digit year
    return datetime.now().strftime("%a %b %-d, %Y")

# config loader
def load_config(stage_name: str="prod", config_path:str | None = None) -> StageConfig:
    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH", "config.yml")
    raw = _get_config_file(config_path, "stages", stage_name)
    return StageConfig.model_validate(_expand_environment_variables(raw))


def _expand_environment_variables(value: Any) -> Any:
    """Expand ``$VAR`` and ``${VAR}`` references in configuration values."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {key: _expand_environment_variables(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_environment_variables(item) for item in value]
    return value

def _get_config_file(path, section_name, subsection_name=None) -> dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No such file {path}")
    with open(path, encoding="utf8") as f:
        data = yaml.safe_load(f)
        try:
            return data[section_name][subsection_name] if subsection_name is not None else data[section_name]
        except (KeyError, TypeError) as e:
            raise KeyError(
                f"No such section or subsection in config file: {section_name}, {subsection_name}. Config file: {path}"
            ) from e

# python -m deep_research.utils
if __name__ == "__main__":
    print(get_today_str())
    cfg = load_config(stage_name="prod")
    for name, role in cfg.cognition.items():
        print(f"{name}, {role}")



