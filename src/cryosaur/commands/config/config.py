'''
CRYOSAUR: manage cryosaur's config.toml
'''

# -- Import external dependencies
import os, subprocess, typer
from typing import Annotated, Literal

# -- Import cryosaur utilities
from cryosaur.commands.config.print import print_toml
from cryosaur.utils.cli.registry import register
from cryosaur.utils.cluster.cluster import _DEFAULT_RESOURCE_FACTORIES_KEYS, get_backend, default_resources
from cryosaur.utils.config import CONFIG_PATH
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- _build_template: build config.toml depending on passed arguments
def _build_template(
    cluster_seed
) -> str:
    template = '# cryosaur configuration file'
    # Add cluster section
    template += '\n\n'
    if cluster_seed is None:
        template += '''\
            [cluster]
            # scheduler = "slurm"
            # default_resources = "<an id defined below>"

            [cluster.modules]
            # name = "actual/module/version"

            [cluster.resources.<id>]
            # partition = ""
            # gpus = 0
            # cpus_per_task = 1
            # mem_per_gpu = ""
            # time = "24:00:00"
            # modules = []
            '''
    else:
        scheduler = defaults_id.split('_')[0]
        defaults = default_resources(defaults_id, 'config')
        template += f'''\
            [cluster]
            scheduler = "{scheduler}"
            default_resources = "default"
            
            [cluster.modules]
            # name = "actual/module/version"
            
            [cluster.resources.default]
            partition = ""  # REQUIRED: set your partition
            cpus_per_task = {defaults.cpus_per_task}
            mem = "{defaults.mem}"
            time = "{defaults.time}"
            modules = []
            '''  
    # Add project section
    template += '\n\n'
    template += '''\
        [project]
        db_path = ""
        '''
    # Return config template
    return template

# -- config_init: writes a new config file, without overwriting an existing one
@register('init', group='config')
def config_init(
    seed: Annotated[
        Literal[_DEFAULT_RESOURCE_FACTORIES_KEYS] | None,
        typer.Option('--seed', help="Seed the file with a registered scheduler backend's defaults.", show_default=False),
    ] = None,
):
    '''
    Write a new cryosaur config file.
    '''
    if CONFIG_PATH.exists():
        raise CryosaurError(f'Config file already exists at <cyan>{CONFIG_PATH}</cyan>; edit it directly or remove first')

    template = _build_template(seed)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(template)
    log.info(f'Wrote config file to <cyan>{CONFIG_PATH}</cyan>')

# -- config_edit: opens the config file in $EDITOR, creating it first if missing
@register('edit', group='config')
def config_edit(
    editor: Annotated[
        str | None,
        typer.Option('--editor', help='Editor to use instead of $EDITOR/vi.', show_default=False)
    ] = None
):
    '''
    Open the cryosaur config file in $EDITOR, creating it first if it doesn't exist.
    '''
    if not CONFIG_PATH.exists():
        log.info(f'No config file found; creating a new one at <cyan>{CONFIG_PATH}</cyan>')
        config_init(cluster=None)
    if editor is not None:
        from shutil import which
        editor_path = which(editor)
        if editor_path:
            try:
                subprocess.call([editor_path, str(CONFIG_PATH)])
                return
            except Exception as e:
                log.error(f'Could not open <cyan>{CONFIG_PATH}</cyan> in editor {editor}: {e}')
                raise CryosaurError(f'Could not open <cyan>{CONFIG_PATH}</cyan> in editor {editor}, use alternative editor')    
    editor = os.environ.get('EDITOR', 'vi')
    subprocess.call([editor, str(CONFIG_PATH)])

# -- config_show: prints the config file's contents
@register('show', group='config')
def config_show():
    '''
    Print the current cryosaur config file, or a message if none exists.
    '''
    if not CONFIG_PATH.exists():
        log.info(f'No config file found at <cyan>{CONFIG_PATH}</cyan>. Run `cryosaur config init` first.')
        return
    print_toml(CONFIG_PATH)
