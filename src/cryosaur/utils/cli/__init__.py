'''
CRYOSAUR: commands module
'''

# -- Import cryosaur utilities
from cryosaur.utils.log import log

# -- Define all commands to import
cryosaur_commands = [
    # project subcommands
    'cryosaur.commands.project.annotate',
    'cryosaur.commands.project.export_report',
    'cryosaur.commands.project.import_toml',
    'cryosaur.commands.project.ingest',
    'cryosaur.commands.project.render',
    'cryosaur.commands.project.session',
    'cryosaur.commands.project.view',
    # pipelines
    'cryosaur.commands.destripe_lamella.cli',
    'cryosaur.commands.morpho_analysis.cli',
    # tools
    'cryosaur.commands.trim_vol.cli',
    # utilities
    'cryosaur.commands.config.config',
    'cryosaur.commands.utils.check_external_tools',
    'cryosaur.commands.utils.flatten',
]

# -- Loop over all commands and try to import, logging warning if exception raised
for command in cryosaur_commands:
    try:
        __import__(command)
    except (ModuleNotFoundError, ImportError):
        continue
