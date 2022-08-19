import os
import yaml

from enum import Enum


def load_config():
    conf = os.getenv("CONFIG", "config.yml")
    try:
        return yaml.safe_load(open(conf))
    except OSError as e:
        return {}


def env_to_list(name: str):
    return " ".join(os.getenv(name, "").split(",")).split()


def list_to_enum(name: str, koptv: list):
    return Enum(name, [f"{kv}:{kv}".split(":")[:2] for kv in koptv])
