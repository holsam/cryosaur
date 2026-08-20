'''
CRYOSAUR: TOML export/import for the annotation store, for human-readable portability
'''

# -- Import external dependencies
import tomllib, tomli_w
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.log import log

# -- export_session_to_toml: returns None, but writes session_id (or every session, if None) plus its lamellae/notes/points/overlays to output_path
def export_session_to_toml(db_path: Path, output_path: Path, session_id: str | None = None) -> None:
    sessions = [store.get_session(db_path, session_id)] if session_id else store.list_sessions(db_path)
    sessions = [s for s in sessions if s is not None]

    data: dict = {'sessions': []}
    for session in sessions:
        session_entry = session.model_dump()
        session_entry['lamellae'] = []
        for lamella in store.list_lamellae(db_path, session.session_id):
            lamella_entry = lamella.model_dump()
            annotations = store.get_annotations_for_lamella(db_path, lamella.id)
            lamella_entry['notes'] = [n.model_dump() for n in annotations['notes']]
            lamella_entry['points'] = [p.model_dump() for p in annotations['points']]
            lamella_entry['overlays'] = [o.model_dump() for o in annotations['overlays']]
            session_entry['lamellae'].append(lamella_entry)
        data['sessions'].append(session_entry)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        tomli_w.dump(data, f)
    log.info(f'Exported {len(sessions)} session(s) to <cyan>{output_path}</cyan>')

# -- import_toml: returns None, but upserts every session/lamella/note/point/overlay in path into db_path
def import_toml(db_path: Path, path: Path) -> None:
    with path.open('rb') as f:
        data = tomllib.load(f)

    for session_entry in data.get('sessions', []):
        session_id = session_entry['session_id']
        if store.get_session(db_path, session_id) is None:
            store.add_session(db_path, session_id, session_entry['session_name'], session_entry.get('paths', {}))

        # Map imported lamella names to freshly assigned ids
        for lamella_entry in session_entry.get('lamellae', []):
            lamella = store.add_lamella(
                db_path,
                session_id,
                lamella_entry['lamella_name'],
                grid_name=lamella_entry.get('grid_name'),
                status=lamella_entry.get('status'),
            )
            note_id_map: dict[int, int] = {}
            for note_entry in lamella_entry.get('notes', []):
                note = store.add_note(db_path, lamella.id, note_entry['text'])
                if note_entry.get('id') is not None:
                    note_id_map[note_entry['id']] = note.id
            for point_entry in lamella_entry.get('points', []):
                store.add_point(
                    db_path,
                    lamella.id,
                    point_entry['x'],
                    point_entry['y'],
                    point_entry['z'],
                    label=point_entry.get('label'),
                    note_id=note_id_map.get(point_entry.get('note_id')),
                )
            for overlay_entry in lamella_entry.get('overlays', []):
                store.add_overlay(
                    db_path,
                    lamella.id,
                    overlay_entry['seg_type'],
                    overlay_entry['thumbnail_path'],
                    mesh_cache_path=overlay_entry.get('mesh_cache_path'),
                )
    log.info(f'Imported <cyan>{path}</cyan> into <cyan>{db_path}</cyan>')
