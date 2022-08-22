import json
import os

from enum import Enum

import yaml


def load_config():
    conf = os.getenv("CONFIG", "config.yml")
    try:
        return yaml.safe_load(open(conf, encoding="UTF-8"))
    except OSError:
        return {}


def env_to_list(name: str):
    return " ".join(os.getenv(name, "").split(",")).split()


def env_to_dict(name: str):
    return json.loads(os.getenv(name, "{}"))


def list_to_enum(name: str, koptv: list):
    return Enum(name, [f"{kv}:{kv}".split(":")[:2] for kv in koptv])
