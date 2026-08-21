'''
CRYOSAUR: command registration
'''

# -- Import external dependencies
from collections.abc import Callable
from dataclasses import dataclass


# -- _RegisteredCommand: a registered command function, its visibility, which subcommand group (if any) it belongs to, and which Rich help panel it's listed under
@dataclass
class _RegisteredCommand:
    func: Callable
    hidden: bool
    group: str | None
    panel: str | None

# -- _REGISTRY: dictionary mapping command names to _RegisteredCommand instances
_REGISTRY: dict[str, _RegisteredCommand] = {}

# -- register: decorator that registers a command function under the given CLI name, optionally nested under a subcommand group (e.g. group='utils' -> `cryosaur utils <name>`) and/or listed under a named rich help panel
def register(name: str, *, hidden: bool = False, group: str | None = None, panel: str | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        _REGISTRY[name] = _RegisteredCommand(func=func, hidden=hidden, group=group, panel=panel)
        return func
    return decorator

# -- registered_commands: returns every registered command mapping name to its registration details
def registered_commands() -> dict[str, _RegisteredCommand]:
    return dict(_REGISTRY)
