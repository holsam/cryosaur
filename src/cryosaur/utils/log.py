'''
CRYOSAUR: log file set up and handling
'''

# -- Import external dependencies
import sys, time
from datetime import datetime
from loguru import logger as logger
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

# -- Import cryosaur utilities
import cryosaur.utils.icon as icon
import cryosaur.utils.io as io

# -- Define constants
DEFAULT_LOG_NAME = 'cryosaur.log'
INPUT_LEVEL = 'INPUT'
LOG_FORMAT = '<dim>{time:YYYY-MM-DD HH:mm:ss}</> <lvl>[{level}]</> {message}'
PROGRESS_LEVEL = 'PROGRESS'

# -- Define dictionary to map verbosity values to levels
VERBOSITY_TO_LEVEL = {
    0: 'WARNING',
    1: 'INFO',
    2: PROGRESS_LEVEL,
    3: 'DEBUG'
}

# -- _CryosaurLogger: class for logger, which proxies standard log methods through opt(colours=True) so messages don't have to include every time
class _CryosaurLogger:
    def _log(self, level: str, message: str, *args, **kwargs) -> None:
        logger.opt(colors=True, depth=2).log(level, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._log('DEBUG', message, *args, **kwargs)

    def progress(self, message: str, *args, **kwargs) -> None:
        self._log(PROGRESS_LEVEL, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._log('INFO', message, *args, **kwargs)

    def input(self, message: str, *args, **kwargs):
        # Check if in interactive session
        interactive = sys.stdin.isatty()
        # Get default answer from kwargs
        default = kwargs.get('default')
        if not interactive:
            # If not in an interactive session, just use provided default value
            answer = default
        else:
            console = Console(stderr=True)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            styled_prompt = (
                f'[dim]{timestamp}[/dim] [bold green]{"[INPUT]"}[/] [white]{message}[/]'
            )
            prompt_obj = Prompt(
                styled_prompt,
                console=console,
                choices=kwargs.get('choices'),
                show_default=kwargs.get('show_default', True),
                show_choices=kwargs.get('show_choices', True),
                case_sensitive=kwargs.get('case_sensitive', True),
            )
            answer = prompt_obj(default=default)
            # Work out how many terminal rows the prompt (and the typed answer, if echoed) actually occupied, so wrapped prompts get fully erased rather than leaving fragments behind
            rendered = prompt_obj.make_prompt(default)
            total_len = len(rendered.plain) + len(str(answer))
            width = console.width or 80
            rows = max(1, -(-total_len // width))  # ceil division
            for _ in range(rows):
                console.file.write("\x1b[1A\x1b[2K")
            console.file.write("\r")
            console.file.flush()
        log_entry = f'{message}: {answer}'
        self._log(INPUT_LEVEL, log_entry, *args, **kwargs)
        return answer

    def warning(self, message: str, *args, **kwargs) -> None:
        self._log('WARNING', message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._log('ERROR', message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        self._log('CRITICAL', message, *args, **kwargs)

# -- register_custom_levels: returns None, but registers custom levels INPUT and PROGRESS and updates default loguru colour scheme 
def register_custom_levels() -> None:
    # Add custom INPUT and PROGRESS levels
    for name, no, colour in (
        (PROGRESS_LEVEL, 15, '<cyan><bold>'),
        (INPUT_LEVEL, 25, '<green><bold>'),
    ):
        try:
            logger.level(name, no=no, color=colour)
        except ValueError:
            # If level is already registered, skip registration instead of raising error
            pass
    # Change default loguru level colour scheme
    for name, colour in (
        ('DEBUG', '<yellow><bold>'),
        ('INFO', '<blue><bold>'),
        ('WARNING', '<fg 178><bold>'),
    ):
        try:
            logger.level(name, color=colour)
        except ValueError:
            # If level/colour is already registered, skip registration instead of raising error
            pass

# -- resolve_level: returns string corresponding to resolved log level to use from verbosity and quiet arguments
def resolve_level(verbosity: int, quiet: bool) -> str:
    if quiet:
        return 'ERROR'
    return VERBOSITY_TO_LEVEL[verbosity]

# -- build_level_filter: returns functions _filter to use as loguru sink filter, which enforces specified level while always allowing INPUT-level messages
def build_level_filter(level_name: str):
    threshold_no = logger.level(level_name).no
    def _filter(record) -> bool:
        if record['level'].name == INPUT_LEVEL:
            return True
        return record['level'].no >= threshold_no
    return _filter

# -- resolve_log_directory: returns Path indicating which directory to write the log file within (follows hierarchy: specified directory -> current working directory -> home directory)
def resolve_log_directory(specified_dir: Path | None):
    dirs = [Path.cwd(), Path.home()]
    if specified_dir is not None:
        dirs.insert(0, specified_dir)
    for d in dirs:
        # Get absolute path to directory
        d = io._resolve_abspath(d)
        # If directory doesn't exist, try to create (logging warning if not possible)
        if not d.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.warning(f'Could not create log file parent directory {d}')
                continue
        # If directory is writable, return otherwise raise warning
        if io._is_writable(d):
            return d
        logger.warning(f'No write permissions for {d} to create log file')
    # If all options exhausted, raise an error
    raise PermissionError('No writable directory found for log file')

# -- resolve_log_path: returns a tuple of Path and bool, indicating the path to the final log file and whether the header needs to be written to it
def resolve_log_path(
    directory: Path,
    mode: str
) -> tuple[Path, bool]:
    '''
    write_header boolean determined by mode:
        - append: reuse existing file if present, don't rewrite header
        - new: use a new file path, write header
        - overwrite: reuse the same path, rewrite header
    '''
    path = directory / DEFAULT_LOG_NAME
    if mode == 'overwrite':
        return path, True
    if mode == 'new':
        return _next_available_path(path), True
    if mode == 'append':
        write_header = not path.exists()
        return path, write_header
    raise ValueError(f'Unknown mode {mode}, expected one of: concat, overwrite, create')

# -- configure_logging: returns Path to log file after configuring logging sinks
def configure_logging(
    directory: Path | None,
    mode: str,
    quiet: bool,
    verbosity: int,
) -> Path:
    register_custom_levels()
    level_name = resolve_level(verbosity, quiet)
    level_filter = build_level_filter(level_name)
    # Remove default logging handler
    logger.remove() # Remove
    # Add terminal sink
    logger.add(sys.stderr, format=LOG_FORMAT, filter=level_filter, colorize=True)
    # Print header
    icon.print_icon_header()
    # Add a temporary buffer sink to catch any warning logs raised during log file directory resolution
    buffer: list[str] = []
    buffer_sink = logger.add(buffer.append, format=LOG_FORMAT, filter=level_filter, colorize=False)
    # Resolve log file directory/path and remove buffer sink
    log_dir = resolve_log_directory(directory)
    log_path, write_header = resolve_log_path(log_dir, mode)
    logger.remove(buffer_sink)
    # Based on mode, open log file as write or append
    file_open_mode = 'w' if mode in ['new', 'overwrite'] else 'a'
    with open(log_path, file_open_mode, encoding='utf-8') as f:
        if write_header:
            f.write(icon.DINO_ICON + '\n')
        f.writelines(buffer)
    # Set up actual log file sink
    logger.add(log_path, format=LOG_FORMAT, filter=level_filter, colorize=False, mode='a')
    # Return log file path
    return log_path

# -- Create logger as instance of _CryosaurLogger
log = _CryosaurLogger()
