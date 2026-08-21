'''
CRYOSAUR: flatten a nested directory structure to a directory of symlinks
'''

# -- Import external dependencies
import os, typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.io import _find_files_by_extension, _find_files_by_pattern, _resolve_abspath
from cryosaur.utils.log import log
from cryosaur.utils.cli.registry import register

@register('flatten', group='utils')
def flatten_directory(
    input_directory: Annotated[
        Path,
        typer.Argument(help='Path to root directory to flatten.', exists=True, dir_okay=True, metavar='INPUT_DIR')
    ],
    output_directory: Annotated[
        Path,
        typer.Argument(help='Path to output directory containing symlinks.', metavar='OUTPUT_DIR')
    ],
    recursive: Annotated[
        bool,
        typer.Option('--recursive/--not-recursive', help='Recursively flatten directories within input directory.')
    ] = True,
    extension: Annotated[
        str,
        typer.Option('-e', '--extension', help='File extension for filtering files to flatten.', show_default=False)
    ] = '*',
    pattern: Annotated[
        str,
        typer.Option('-p', '--pattern', help='Glob pattern for filtering files to flatten.', show_default=False)
    ] = '*',
    skip_confirmation: Annotated[
        bool,
        typer.Option('--skip-confirmation', help='Skip confirmation message before creating symlinks.')
    ] = False,
):
    '''
    Find files matching the given parameters, and create a flat directory containing symbolic links to these. 
    '''
    # Get absolute paths of input_directory and output_directory
    input_directory = _resolve_abspath(input_directory)
    output_directory = _resolve_abspath(output_directory)

    # Add leading '.' to extension if not present
    extension = extension if extension.startswith('.') else f'.{extension}'

    # Find files matching extension and pattern
    match_ext = _find_files_by_extension(input_dir=input_directory, extension=extension, recursive=recursive)
    log.progress(f'<white>{len(match_ext)}</white> file(s) found in <cyan>{input_directory}</cyan> with extension <cyan>{extension}</cyan>')
    log.debug(f'Matching files: {"; ".join(str(match_ext))}')
    match_pat = _find_files_by_pattern(input_dir=input_directory, pattern=pattern, recursive=recursive)
    log.progress(f'<white>{len(match_ext)}</white> file(s) found in <cyan>{input_directory}</cyan> matching pattern <cyan>{pattern}</cyan>')
    log.debug(f'Matching files: {"; ".join(str(match_pat))}')

    # Find files which fit both criteria
    matches = set(match_ext).intersection(match_pat)
    log.progress(f'<white>{len(match_ext)}</white> matching file(s) found in <cyan>{input_directory}</cyan>')
    log.debug(f'Matching files: {"; ".join(str(matches))}')
    
    # Get a dictionary mapping paths to unique file names, then prepend output_dir to each
    symlinks = _create_unique_names_dict(matches)
    for mapping in symlinks.items():
        symlinks[mapping[0]] = output_directory / mapping[1]

    # Print confirmation
    if not skip_confirmation:
        while True:
            action = log.input(f'{len(symlinks.values())} symlink(s) will be created. Enter y to link, n to cancel, or v to see files/symlinks before deciding', default='y', choices=['y', 'n', 'v'], show_default=False, show_choices=False, case_sensitive=False)
            if action == 'N':
                log.info(f'Cancelled symlink creation')
                return
            elif action == 'V':
                from rich import print
                for mapping in symlinks.items():
                    print(f'[cyan]{mapping[0]}[/] → [green]{mapping[1]}[/]')
            elif action == 'Y':
                break
        
    # Loop over each file, creating symlinks
    for i, s in enumerate(symlinks.items(), start=1):
        log.progress(f'[{i}/{len(symlinks)}] Linking <cyan>{s[0]}</cyan>')
        _create_symlink(original=s[0], link=s[1])
    log.info(f'Created {len(symlinks.values())} in <cyan>{output_directory}</cyan>')

# -- _create_unique_names_dict: given a list of paths, returns a dictionary mapping Path to unique name (prepending parent directories as required)
def _create_unique_names_dict(paths: list[Path]) -> dict[Path, str]:
    entries = [{'path': p, 'name': p.name, 'remaining': p.parent, 'depth': len(p.parts)} for p in paths]
    while True:
        groups: dict[str, list[dict]] = {}
        for entry in entries:
            groups.setdefault(entry['name'], []).append(entry)
        if all(len(group) == 1 for group in groups.values()):
            break
        for group in groups.values():
            if len(group) == 1:
                continue
            min_depth = min(entry['depth'] for entry in group)
            to_extend = [entry for entry in group if entry['depth'] > min_depth] or group
            for entry in to_extend:
                if entry['remaining'] == entry['remaining'].parent:
                    conflicting = '</cyan>, <cyan>'.join(str(e['path']) for e in group)
                    log.error(f'Could not create unique names for <cyan>{conflicting}</cyan>')
                entry['name'] = f'{entry["remaining"].name}_{entry["name"]}'
                entry['remaining'] = entry['remaining'].parent
    return {entry['path']: entry['name'] for entry in entries}

# -- _create_symlink: try to create a symlink for `original` at path `link`, raising warning if `link` already exists
def _create_symlink(original: Path, link: Path):
    try:
        # Create parent directory for link if it doesn't already exist
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(src=original, dst=link)
        log.debug(f'Created symlink {link} for {original}')
    except FileExistsError as e:
        log.warning(f'Could not create symlink {link} for {original}: {e}')
