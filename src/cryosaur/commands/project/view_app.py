'''
CRYOSAUR: Streamlit dashboard for annotations
'''

# -- Import external dependencies
import argparse, subprocess, sys, uuid
import streamlit as st
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.project import import_folder, store, toml_io

# -- _PATH_KINDS: preset session.paths keys offered in the import-folder form
_PATH_KINDS = ['raw', 'relion_project', 'segmentations', 'other']

# -- _parse_args: returns the --db-path passed after Streamlit's own `--` separator
def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', required=True)
    return parser.parse_args()

# -- _render_import_folder_form: returns None, but renders the "Import folder" form and applies it on submit
def _render_import_folder_form(db_path: str, sessions: list) -> None:
    with st.expander('Import folder'):
        with st.form('import_folder_form'):
            session_names = {s.session_name: s.session_id for s in sessions}
            target = st.selectbox('Session', ['<new session>'] + list(session_names.keys()))
            new_session_name = st.text_input('New session name', disabled=target != '<new session>')

            folder = st.text_input('Folder path')
            path_kind = st.selectbox('Folder contains', _PATH_KINDS)
            custom_kind = st.text_input('Custom key', disabled=path_kind != 'other')
            scan_for_mrcs = st.checkbox('Recursively register lamellae from .mrc files', value=(path_kind == 'raw'))
            recursive = st.checkbox('Recurse into subdirectories', value=True, disabled=not scan_for_mrcs)

            submitted = st.form_submit_button('Import')
            if not submitted:
                return

            if not folder:
                st.error('Folder path is required')
                return
            folder_path = Path(folder).expanduser()
            if not folder_path.is_dir():
                st.error(f'{folder_path} is not a directory')
                return

            if target == '<new session>':
                if not new_session_name:
                    st.error('New session needs a name')
                    return
                session_id = uuid.uuid4().hex[:12]
                store.add_session(db_path, session_id, new_session_name, {})
            else:
                session_id = session_names[target]

            resolved_kind = custom_kind if path_kind == 'other' else path_kind
            added = import_folder.import_folder(db_path, session_id, folder_path, resolved_kind, scan_for_mrcs, recursive)

            st.success(f'Set {resolved_kind!r} path for session, registered {len(added)} new lamella/lamellae')
            st.rerun()

# -- _render_toml_controls: returns None, but renders the export/import TOML buttons
def _render_toml_controls(db_path: str, session_id: str | None) -> None:
    export_col, import_col = st.columns(2)
    with export_col:
        export_path = Path(db_path).with_suffix('.toml')
        toml_io.export_session_to_toml(db_path, export_path, session_id)
        st.download_button('Export session to TOML', export_path.read_bytes(), file_name=export_path.name)
    with import_col:
        uploaded = st.file_uploader('Import TOML', type='toml')
        if uploaded is not None and st.button('Run import'):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.toml', delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = Path(tmp.name)
            toml_io.import_toml(db_path, tmp_path)
            tmp_path.unlink()
            st.success('Imported. Reload to see the new records.')
            st.rerun()

# -- main: renders the dashboard
def main() -> None:
    args = _parse_args()
    db_path = args.db_path

    st.title('cryosaur project view')

    sessions = store.list_sessions(db_path)
    _render_import_folder_form(db_path, sessions)
    if not sessions:
        st.info(f'No sessions found in {db_path}')
        return

    session_names = {s.session_name: s.session_id for s in sessions}
    chosen_name = st.selectbox('Session', list(session_names.keys()))
    session_id = session_names[chosen_name]
    session = store.get_session(db_path, session_id)

    st.caption(f'Paths: {session.paths}')
    _render_toml_controls(db_path, session_id)

    if st.button('Add annotations'):
        subprocess.Popen(['cryosaur', 'project', 'annotate', '--db-path', str(db_path), '--session-id', session_id])
        st.info("Annotation window launched. Reload this page once you're finished to see updates.")

    lamellae = store.list_lamellae(db_path, session_id)
    rows = []
    for lamella in lamellae:
        annotations = store.get_annotations_for_lamella(db_path, lamella.id)
        rows.append({
            'name': lamella.lamella_name,
            'milling_order': lamella.milling_order,
            'status': lamella.status,
            'notes': len(annotations['notes']),
            'points': len(annotations['points']),
        })
    st.dataframe(rows, use_container_width=True)

    for lamella in lamellae:
        annotations = store.get_annotations_for_lamella(db_path, lamella.id)
        for overlay in annotations['overlays']:
            st.image(overlay.thumbnail_path, caption=f'{lamella.lamella_name} ({overlay.seg_type})')

if __name__ == '__main__':
    main()
