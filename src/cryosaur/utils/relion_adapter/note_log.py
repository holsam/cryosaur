'''
CRYOSAUR: RELION5 job note.txt parser
'''

# -- Import external dependencies
from pathlib import Path

# -- NoteCommandError: raised when a note.txt command can't be found or safely modified
class NoteCommandError(Exception):
    pass

# -- read_note_commands: returns every command line in a job's note.txt, one per tomogram
def read_note_commands(note_path: Path) -> list[str]:
    return [line.strip() for line in note_path.read_text().splitlines() if line.strip()]

# -- find_command_for_tomogram: returns the single note.txt command line for tomo_name
def find_command_for_tomogram(commands: list[str], tomo_name: str) -> str:
    key = f'{tomo_name}_stack'
    matches = [c for c in commands if key in c]
    if len(matches) != 1:
        raise NoteCommandError(f'Expected exactly one note.txt command matching {key!r}, found {len(matches)}')
    return matches[0]

# -- extract_flag_value: returns the value following a space-separated CLI flag in a command string
def extract_flag_value(command: str, flag: str) -> str:
    parts = command.split()
    return parts[parts.index(flag) + 1]

# -- substitute_paths: applies a sequence of exact-match path substitutions to a command, raising if any old_path doesn't occur exactly once at the point it's applied
def substitute_paths(command: str, substitutions: list[tuple[str, str]]) -> str:
    for old_path, new_path in substitutions:
        count = command.count(old_path)
        if count != 1:
            raise NoteCommandError(f'Expected exactly one occurrence of {old_path!r}, found {count}')
        command = command.replace(old_path, new_path)
    return command
