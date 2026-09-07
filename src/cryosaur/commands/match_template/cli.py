'''
CRYOSAUR: `match-template` command CLI
'''

# -- Import external dependencies
import os, typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.cli.registry import register
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

@register('extract', group='match-template')
def extract_command():
    '''
    Extract a fixed-size subvolume from a tomogram.
    '''
    log.warning('match-template sub-vol is not yet implemented.')

@register('template', group='match-template')
def template_command():
    '''
    Align a set of subvolumes into a reference normal using normalised cross-correlation.
    '''
    log.warning('match-template template is not yet implemented.')

@register('match', group='match-template')
def match_command():
    '''
    Prepare input files for GAPSTOP_TM searching.
    '''
    log.warning('match-template match is not yet implemented.')
