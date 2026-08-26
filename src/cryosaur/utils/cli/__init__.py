'''
CRYOSAUR: commands module
'''

# -- Wrap all import in a try...except block so failed imports don't prevent cryosaur from running
try:
    # -- Import cryosaur commands: projects (if dependencies available)
    from cryosaur.commands.project import annotate as _project_annotate_cli
    from cryosaur.commands.project import export_report as _project_export_report
    from cryosaur.commands.project import import_toml as _project_import_toml_cli
    from cryosaur.commands.project import ingest as _project_ingest_screenshots_cli
    from cryosaur.commands.project import render as _project_render_cli
    from cryosaur.commands.project import session as _project_session_cli
    from cryosaur.commands.project import view as _project_view_cli

    # -- Import cryosaur commands: pipelines
    from cryosaur.commands.destripe_lamella import cli as _destripe_lamella_cli

    # -- Import cryosaur commands: tools
    from cryosaur.commands.trim_vol import cli as _trim_volume_cli

    # -- Import cryosaur commands: utilities
    from cryosaur.commands.config import config as _config_cli
    from cryosaur.commands.utils import check_external_tools as _check_tools_cli
    from cryosaur.commands.utils import flatten as _flatten_cli

except ModuleNotFoundError:
    pass