'''
CRYOSAUR: shared error handling for CLI commands
'''

# -- Import external dependencies
import typer
from collections.abc import Callable
from functools import wraps

# -- Import cryosaur utilities
from cryosaur.utils.log import log

# -- CryosaurError: base class for cryosaur's own expected errors (caught at the CLI boundary and logged via log.error, rather than surfacing as an unhandled traceback)
class CryosaurError(Exception):
    pass


# -- handle_errors: decorator that catches CryosaurError, logs it, and exits cleanly instead of letting Typer/rich render its own traceback
def handle_errors(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except CryosaurError as exc:
            log.error(str(exc))
            log.info('cryosaur completed with exit code 1')
            print()
            raise typer.Exit(code=1)
        log.info('cryosaur completed with exit code 0')
        print()
        return result
    return wrapper
