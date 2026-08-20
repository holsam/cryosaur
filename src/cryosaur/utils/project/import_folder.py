'''
CRYOSAUR: register a session's path plus (optionally) bulk-register lamellae from MRC files found under it
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.io import _find_files_by_extension
from cryosaur.utils.log import log
from cryosaur.utils.project import store

# -- register_lamellae_from_folder: returns the names of newly added lamellae, skipping any MRC stem that's already a lamella in the session
def register_lamellae_from_folder(db_path: Path, session_id: str, folder: Path, recursive: bool) -> list[str]:
    existing_names = {l.lamella_name for l in store.list_lamellae(db_path, session_id)}
    mrc_paths = _find_files_by_extension(folder, 'mrc', recursive=recursive)
    added = []
    for mrc_path in mrc_paths:
        name = mrc_path.stem
        if name in existing_names:
            continue
        store.add_lamella(db_path, session_id, name)
        existing_names.add(name)
        added.append(name)
    log.info(f'Registered {len(added)} new lamella/lamellae from <cyan>{folder}</cyan>')
    return added

# -- import_folder: returns the names of any newly registered lamellae, after recording folder as session.paths[path_kind] and (if scan_for_mrcs) registering one lamella per MRC stem found under it
def import_folder(
    db_path: Path,
    session_id: str,
    folder: Path,
    path_kind: str,
    scan_for_mrcs: bool,
    recursive: bool,
) -> list[str]:
    store.update_session_paths(db_path, session_id, path_kind, str(folder))
    if not scan_for_mrcs:
        return []
    return register_lamellae_from_folder(db_path, session_id, folder, recursive)
