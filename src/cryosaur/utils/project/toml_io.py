'''
CRYOSAUR: TOML export/import for the annotation store, for human-readable portability
'''

# -- Import external dependencies
import tomllib, tomli_w
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.log import log

# -- SessionDiff: existing-vs-incoming comparison for one session that already exists in the target db
@dataclass
class SessionDiff:
    session_id: str
    existing_name: str
    incoming_name: str
    existing_paths: dict[str, str]
    incoming_paths: dict[str, str]

# -- LamellaDiff: existing-vs-incoming comparison for one lamella (matched by session_id + lamella_name) that already exists
@dataclass
class LamellaDiff:
    session_id: str
    lamella_name: str
    existing_grid_name: str | None
    incoming_grid_name: str | None
    existing_status: str | None
    incoming_status: str | None
    existing_notes: int
    incoming_notes: int
    existing_points: int
    incoming_points: int
    existing_overlays: int
    incoming_overlays: int

# -- ImportPlan: what a TOML import would do, computed without writing anything
@dataclass
class ImportPlan:
    data: dict
    new_sessions: list[str] = field(default_factory=list)
    conflicting_sessions: list[SessionDiff] = field(default_factory=list)
    new_lamellae: list[tuple[str, str]] = field(default_factory=list)
    conflicting_lamellae: list[LamellaDiff] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicting_sessions or self.conflicting_lamellae)

# -- ImportSummary: counts of what apply_import actually did
@dataclass
class ImportSummary:
    sessions_created: int = 0
    sessions_skipped: int = 0
    sessions_replaced: int = 0
    lamellae_created: int = 0
    lamellae_skipped: int = 0
    lamellae_replaced: int = 0

# -- export_session_to_toml_bytes: returns the exported TOML as bytes (session_id, or every session if None), with no disk write
def export_session_to_toml_bytes(db_path: Path, session_id: str | None = None) -> bytes:
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
            lamella_entry['screenshots'] = [s.model_dump() for s in annotations['screenshots']]
            session_entry['lamellae'].append(lamella_entry)
        data['sessions'].append(session_entry)

    return tomli_w.dumps(data).encode('utf-8')

# -- export_session_to_toml: returns None, but writes the same bytes as export_session_to_toml_bytes to output_path
def export_session_to_toml(db_path: Path, output_path: Path, session_id: str | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(export_session_to_toml_bytes(db_path, session_id))
    log.info(f'Exported to <cyan>{output_path}</cyan>')

# -- plan_import: returns an ImportPlan describing what importing path into db_path would do, without writing anything
def plan_import(db_path: Path, path: Path) -> ImportPlan:
    with path.open('rb') as f:
        data = tomllib.load(f)

    plan = ImportPlan(data=data)
    for session_entry in data.get('sessions', []):
        session_id = session_entry['session_id']
        existing_session = store.get_session(db_path, session_id)
        if existing_session is None:
            plan.new_sessions.append(session_id)
        else:
            plan.conflicting_sessions.append(SessionDiff(
                session_id=session_id,
                existing_name=existing_session.session_name,
                incoming_name=session_entry['session_name'],
                existing_paths=existing_session.paths,
                incoming_paths=session_entry.get('paths', {}),
            ))

        for lamella_entry in session_entry.get('lamellae', []):
            existing_lamella = None if existing_session is None else store.get_lamella_by_name(db_path, session_id, lamella_entry['lamella_name'])
            if existing_lamella is None:
                plan.new_lamellae.append((session_id, lamella_entry['lamella_name']))
                continue
            existing_annotations = store.get_annotations_for_lamella(db_path, existing_lamella.id)
            plan.conflicting_lamellae.append(LamellaDiff(
                session_id=session_id,
                lamella_name=lamella_entry['lamella_name'],
                existing_grid_name=existing_lamella.grid_name,
                incoming_grid_name=lamella_entry.get('grid_name'),
                existing_status=existing_lamella.status,
                incoming_status=lamella_entry.get('status'),
                existing_notes=len(existing_annotations['notes']),
                incoming_notes=len(lamella_entry.get('notes', [])),
                existing_points=len(existing_annotations['points']),
                incoming_points=len(lamella_entry.get('points', [])),
                existing_overlays=len(existing_annotations['overlays']),
                incoming_overlays=len(lamella_entry.get('overlays', [])),
            ))
    return plan

# -- _apply_lamella_entry: returns None, but creates a lamella (and its notes/points/overlays) from one TOML lamella entry
def _apply_lamella_entry(db_path: Path, session_id: str, lamella_entry: dict) -> None:
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
            db_path, lamella.id, point_entry['x'], point_entry['y'], point_entry['z'],
            label=point_entry.get('label'), note_id=note_id_map.get(point_entry.get('note_id')),
        )
    for overlay_entry in lamella_entry.get('overlays', []):
        store.add_overlay(
            db_path, lamella.id, overlay_entry['seg_type'], overlay_entry['thumbnail_path'],
            mesh_cache_path=overlay_entry.get('mesh_cache_path'),
        )
    for screenshot_entry in lamella_entry.get('screenshots', []):
        store.add_screenshot(db_path, lamella.id, screenshot_entry['path'], screenshot_entry['sidecar_path'])

# -- apply_import: returns an ImportSummary after committing plan against db_path, applying on_conflict to every conflicting session/lamella
def apply_import(db_path: Path, plan: ImportPlan, on_conflict: Literal['skip', 'replace'] = 'skip') -> ImportSummary:
    summary = ImportSummary()
    for session_entry in plan.data.get('sessions', []):
        session_id = session_entry['session_id']
        existing_session = store.get_session(db_path, session_id)

        if existing_session is None:
            store.add_session(db_path, session_id, session_entry['session_name'], session_entry.get('paths', {}))
            summary.sessions_created += 1
        elif on_conflict == 'replace':
            store.update_session(db_path, session_id, session_name=session_entry['session_name'], paths=session_entry.get('paths', {}))
            summary.sessions_replaced += 1
        else:
            summary.sessions_skipped += 1

        for lamella_entry in session_entry.get('lamellae', []):
            existing_lamella = store.get_lamella_by_name(db_path, session_id, lamella_entry['lamella_name'])
            if existing_lamella is not None:
                if on_conflict == 'skip':
                    summary.lamellae_skipped += 1
                    continue
                store.delete_lamella(db_path, existing_lamella.id)
                summary.lamellae_replaced += 1
            else:
                summary.lamellae_created += 1
            _apply_lamella_entry(db_path, session_id, lamella_entry)

    log.info(f'Import complete: {summary}')
    return summary

# -- import_toml: returns an ImportSummary after planning and applying path into db_path in one call (skip on conflict by default)
def import_toml(db_path: Path, path: Path, on_conflict: Literal['skip', 'replace'] = 'skip') -> ImportSummary:
    return apply_import(db_path, plan_import(db_path, path), on_conflict)
