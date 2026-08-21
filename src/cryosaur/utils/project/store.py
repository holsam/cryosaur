'''
CRYOSAUR: SQLite-backed annotation store
'''

# -- Import external dependencies
import json, sqlite3
from contextlib import contextmanager
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.project.schema import (
    LamellaRecord,
    NoteAnnotation,
    OverlayRecord,
    PointAnnotation,
    SessionRecord,
)
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- _UNSET: sentinel distinguishing "field not given" from "field explicitly set to None" in update_lamella
_UNSET = object()

# -- _SCHEMA: every table, executed once by init_db
_SCHEMA = '''
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    paths        TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lamellae (
    id            INTEGER PRIMARY KEY,
    lamella_name  TEXT NOT NULL,
    session_id    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    grid_name     TEXT,
    milling_order INTEGER,
    status        TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE(session_id, lamella_name)
);
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY,
    lamella_id INTEGER NOT NULL REFERENCES lamellae(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS point_annotations (
    id         INTEGER PRIMARY KEY,
    lamella_id INTEGER NOT NULL REFERENCES lamellae(id) ON DELETE CASCADE,
    x          REAL NOT NULL,
    y          REAL NOT NULL,
    z          REAL NOT NULL,
    label      TEXT,
    note_id    INTEGER REFERENCES notes(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS overlays (
    id              INTEGER PRIMARY KEY,
    lamella_id      INTEGER NOT NULL REFERENCES lamellae(id) ON DELETE CASCADE,
    seg_type        TEXT NOT NULL,
    thumbnail_path  TEXT NOT NULL,
    mesh_cache_path TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lamellae_session_id ON lamellae(session_id);
CREATE INDEX IF NOT EXISTS idx_notes_lamella_id ON notes(lamella_id);
CREATE INDEX IF NOT EXISTS idx_points_lamella_id ON point_annotations(lamella_id);
CREATE INDEX IF NOT EXISTS idx_overlays_lamella_id ON overlays(lamella_id);
 '''

# -- init_db: returns None, but creates every table in db_path if not already present
def init_db(db_path: Path) -> None:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CryosaurError(f'Could not create <cyan>{db_path.parent}</cyan>: {exc}') from exc
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
    log.info(f'Initialised annotation store at <cyan>{db_path}</cyan>')

# -- _connect: returns a sqlite3 connection with foreign keys enforced and WAL journalling, usable as a context manager
@contextmanager
def _connect(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except sqlite3.OperationalError as exc:
        conn.rollback()
        raise CryosaurError(f'Could not access <cyan>{db_path}</cyan>: {exc} (another cryosaur process may have it open)') from exc
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise CryosaurError(f'{db_path}: {exc}') from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# -- add_session: returns the created SessionRecord
def add_session(db_path: Path, session_id: str, session_name: str, paths: dict[str, str]) -> SessionRecord:
    record = SessionRecord(session_id=session_id, session_name=session_name, paths=paths)
    with _connect(db_path) as conn:
        conn.execute('INSERT INTO sessions (session_id, session_name, paths, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', (record.session_id, record.session_name, json.dumps(record.paths), record.created_at, record.updated_at))
    return record

# -- update_session_paths: returns the updated SessionRecord, with paths[key] set to value (or removed, if value is None)
def update_session_paths(db_path: Path, session_id: str, key: str, value: str | None) -> SessionRecord:
    session = get_session(db_path, session_id)
    if session is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan> to update paths for')
    paths = dict(session.paths)
    if value is None:
        paths.pop(key, None)
    else:
        paths[key] = value
    with _connect(db_path) as conn:
        conn.execute('UPDATE sessions SET paths = ?, updated_at = datetime("now") WHERE session_id = ?', (json.dumps(paths), session_id))
    return get_session(db_path, session_id)

# -- get_session: returns the SessionRecord for session_id, or None if it doesn't exist
def get_session(db_path: Path, session_id: str) -> SessionRecord | None:
    with _connect(db_path) as conn:
        row = conn.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
    if row is None:
        return None
    return _session_from_row(row)

# -- list_sessions: returns every SessionRecord, most recently created first
def list_sessions(db_path: Path) -> list[SessionRecord]:
    with _connect(db_path) as conn:
        rows = conn.execute('SELECT * FROM sessions ORDER BY created_at DESC').fetchall()
    return [_session_from_row(row) for row in rows]

# -- _session_from_row: returns a SessionRecord built from a sqlite3.Row
def _session_from_row(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(
        session_id=row['session_id'],
        session_name=row['session_name'],
        paths=json.loads(row['paths']),
        created_at=row['created_at'],
        updated_at=row['updated_at'],
    )

# -- _validate_lamella_name: returns None, but raises CryosaurError if name could escape the segmentation cache directory
def _validate_lamella_name(name: str) -> None:
    if '/' in name or '\\' in name or '..' in name:
        raise CryosaurError(f'Invalid lamella name {name!r}: must not contain "/", "\\\\" or ".."')

# -- add_lamella: returns the created LamellaRecord, its id populated
def add_lamella(
    db_path: Path,
    session_id: str,
    lamella_name: str,
    grid_name: str | None = None,
    status: str | None = None,
) -> LamellaRecord:
    if get_session(db_path, session_id) is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan> to add lamella to')
    _validate_lamella_name(lamella_name)
    with _connect(db_path) as conn:
        # New lamella goes to the end of the session's milling order
        next_order = conn.execute('SELECT COALESCE(MAX(milling_order), 0) + 1 FROM lamellae WHERE session_id = ?', (session_id,)).fetchone()[0]
        record = LamellaRecord(lamella_name=lamella_name, session_id=session_id, grid_name=grid_name, milling_order=next_order, status=status)
        cursor = conn.execute('INSERT INTO lamellae (lamella_name, session_id, grid_name, milling_order, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)', (record.lamella_name, record.session_id, record.grid_name, record.milling_order, record.status, record.created_at, record.updated_at))
        record.id = cursor.lastrowid
    return record

# -- list_lamellae: returns every LamellaRecord for session_id, ordered by milling_order
def list_lamellae(db_path: Path, session_id: str) -> list[LamellaRecord]:
    with _connect(db_path) as conn:
        rows = conn.execute('SELECT * FROM lamellae WHERE session_id = ? ORDER BY milling_order ASC', (session_id,)).fetchall()
    return [_lamella_from_row(row) for row in rows]

# -- _lamella_from_row: returns a LamellaRecord built from a sqlite3.Row
def _lamella_from_row(row: sqlite3.Row) -> LamellaRecord:
    return LamellaRecord(
        id=row['id'],
        lamella_name=row['lamella_name'],
        session_id=row['session_id'],
        grid_name=row['grid_name'],
        milling_order=row['milling_order'],
        status=row['status'],
        created_at=row['created_at'],
        updated_at=row['updated_at'],
    )

# -- reorder_session: returns None but rewrites milling_order for every lamella in session_id to match ordered_lamella_ids as a single transaction
def reorder_session(db_path: Path, session_id: str, ordered_lamella_ids: list[int]) -> None:
    existing_ids = {lamella.id for lamella in list_lamellae(db_path, session_id)}
    if set(ordered_lamella_ids) != existing_ids:
        raise CryosaurError(f'reorder_session for <cyan>{session_id}</cyan> must include every lamella exactly once')
    with _connect(db_path) as conn:
        conn.executemany('UPDATE lamellae SET milling_order = ?, updated_at = datetime("now") WHERE id = ?', [(order, lamella_id) for order, lamella_id in enumerate(ordered_lamella_ids, start=1)])

# -- add_note: returns the created NoteAnnotation with its id populated
def add_note(db_path: Path, lamella_id: int, text: str) -> NoteAnnotation:
    record = NoteAnnotation(lamella_id=lamella_id, text=text)
    with _connect(db_path) as conn:
        cursor = conn.execute('INSERT INTO notes (lamella_id, text, created_at) VALUES (?, ?, ?)', (record.lamella_id, record.text, record.created_at))
        record.id = cursor.lastrowid
    return record

# -- add_point: returns the created PointAnnotation with its id populated
def add_point(
    db_path: Path,
    lamella_id: int,
    x: float,
    y: float,
    z: float,
    label: str | None = None,
    note_id: int | None = None,
) -> PointAnnotation:
    record = PointAnnotation(lamella_id=lamella_id, x=x, y=y, z=z, label=label, note_id=note_id)
    with _connect(db_path) as conn:
        cursor = conn.execute('INSERT INTO point_annotations (lamella_id, x, y, z, label, note_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)', (record.lamella_id, record.x, record.y, record.z, record.label, record.note_id, record.created_at))
        record.id = cursor.lastrowid
    return record

# -- add_overlay: returns the created OverlayRecord, its id populated
def add_overlay(
    db_path: Path,
    lamella_id: int,
    seg_type: str,
    thumbnail_path: str,
    mesh_cache_path: str | None = None,
) -> OverlayRecord:
    record = OverlayRecord(lamella_id=lamella_id, seg_type=seg_type, thumbnail_path=thumbnail_path, mesh_cache_path=mesh_cache_path)
    with _connect(db_path) as conn:
        cursor = conn.execute('INSERT INTO overlays (lamella_id, seg_type, thumbnail_path, mesh_cache_path, created_at) VALUES (?, ?, ?, ?, ?)', (record.lamella_id, record.seg_type, record.thumbnail_path, record.mesh_cache_path, record.created_at))
        record.id = cursor.lastrowid
    return record

# -- get_annotations_for_lamella: returns a dict of every note, point and overlay recorded against lamella_id
def get_annotations_for_lamella(db_path: Path, lamella_id: int) -> dict[str, list]:
    with _connect(db_path) as conn:
        notes = conn.execute('SELECT * FROM notes WHERE lamella_id = ? ORDER BY created_at ASC', (lamella_id,)).fetchall()
        points = conn.execute('SELECT * FROM point_annotations WHERE lamella_id = ? ORDER BY created_at ASC', (lamella_id,)).fetchall()
        overlays = conn.execute('SELECT * FROM overlays WHERE lamella_id = ? ORDER BY created_at ASC', (lamella_id,)).fetchall()
    return {
        'notes': [NoteAnnotation(**dict(row)) for row in notes],
        'points': [PointAnnotation(**dict(row)) for row in points],
        'overlays': [OverlayRecord(**dict(row)) for row in overlays],
    }

# -- get_lamella: returns the LamellaRecord for lamella_id, or None if it doesn't exist
def get_lamella(db_path: Path, lamella_id: int) -> LamellaRecord | None:
    with _connect(db_path) as conn:
        row = conn.execute('SELECT * FROM lamellae WHERE id = ?', (lamella_id,)).fetchone()
    return None if row is None else _lamella_from_row(row)

# -- get_lamella_by_name: returns the LamellaRecord named lamella_name within session_id, or None
def get_lamella_by_name(db_path: Path, session_id: str, lamella_name: str) -> LamellaRecord | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            'SELECT * FROM lamellae WHERE session_id = ? AND lamella_name = ?', (session_id, lamella_name)
        ).fetchone()
    return None if row is None else _lamella_from_row(row)

# -- update_lamella: returns the updated LamellaRecord, changing only the fields explicitly passed
def update_lamella(
    db_path: Path,
    lamella_id: int,
    lamella_name: str | None = _UNSET,
    grid_name: str | None = _UNSET,
    status: str | None = _UNSET,
) -> LamellaRecord:
    if get_lamella(db_path, lamella_id) is None:
        raise CryosaurError(f'No lamella with id <cyan>{lamella_id}</cyan>')

    fields: dict[str, str | None] = {}
    if lamella_name is not _UNSET:
        _validate_lamella_name(lamella_name)
        fields['lamella_name'] = lamella_name
    if grid_name is not _UNSET:
        fields['grid_name'] = grid_name
    if status is not _UNSET:
        fields['status'] = status
    if not fields:
        return get_lamella(db_path, lamella_id)

    set_clause = ', '.join(f'{key} = ?' for key in fields)
    with _connect(db_path) as conn:
        conn.execute(
            f'UPDATE lamellae SET {set_clause}, updated_at = datetime("now") WHERE id = ?',
            (*fields.values(), lamella_id),
        )
    return get_lamella(db_path, lamella_id)

# -- delete_lamella: returns None, cascading to its notes/points/overlays (ON DELETE CASCADE)
def delete_lamella(db_path: Path, lamella_id: int) -> None:
    if get_lamella(db_path, lamella_id) is None:
        raise CryosaurError(f'No lamella with id <cyan>{lamella_id}</cyan>')
    with _connect(db_path) as conn:
        conn.execute('DELETE FROM lamellae WHERE id = ?', (lamella_id,))
    log.info(f'Deleted lamella <cyan>{lamella_id}</cyan>')

# -- delete_session: returns None, cascading to every lamella (and, transitively, their notes/points/overlays)
def delete_session(db_path: Path, session_id: str) -> None:
    if get_session(db_path, session_id) is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan>')
    with _connect(db_path) as conn:
        conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
    log.info(f'Deleted session <cyan>{session_id}</cyan>')

# -- delete_note: returns None
def delete_note(db_path: Path, note_id: int) -> None:
    with _connect(db_path) as conn:
        cursor = conn.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    if cursor.rowcount == 0:
        raise CryosaurError(f'No note with id <cyan>{note_id}</cyan>')

# -- delete_point: returns None
def delete_point(db_path: Path, point_id: int) -> None:
    with _connect(db_path) as conn:
        cursor = conn.execute('DELETE FROM point_annotations WHERE id = ?', (point_id,))
    if cursor.rowcount == 0:
        raise CryosaurError(f'No point annotation with id <cyan>{point_id}</cyan>')

# -- delete_overlay: returns None
def delete_overlay(db_path: Path, overlay_id: int) -> None:
    with _connect(db_path) as conn:
        cursor = conn.execute('DELETE FROM overlays WHERE id = ?', (overlay_id,))
    if cursor.rowcount == 0:
        raise CryosaurError(f'No overlay with id <cyan>{overlay_id}</cyan>')

# -- update_session: returns the updated SessionRecord, changing only the fields explicitly passed
def update_session(
    db_path: Path,
    session_id: str,
    session_name: str | None = _UNSET,
    paths: dict[str, str] | None = _UNSET,
) -> SessionRecord:
    if get_session(db_path, session_id) is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan>')

    fields: dict[str, str] = {}
    if session_name is not _UNSET:
        fields['session_name'] = session_name
    if paths is not _UNSET:
        fields['paths'] = json.dumps(paths)
    if not fields:
        return get_session(db_path, session_id)

    set_clause = ', '.join(f'{key} = ?' for key in fields)
    with _connect(db_path) as conn:
        conn.execute(f'UPDATE sessions SET {set_clause}, updated_at = datetime("now") WHERE session_id = ?', (*fields.values(), session_id))
    return get_session(db_path, session_id)
