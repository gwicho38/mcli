# TODO: Not yet implemented
from typing import Any, NoReturn

GLOBALS = {"MCLI": {}, "APP": {}, "MCLI_TOKEN": {}, "MCLI_URL": {}}


def set_global(global_name: str, global_value: Any) -> None:
    global GLOBALS
    GLOBALS[global_name] = global_value


def get_global(global_name: str) -> Any:
    global GLOBALS
    return GLOBALS[global_name]
