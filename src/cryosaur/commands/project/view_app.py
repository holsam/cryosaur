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

# -- _AUTO_REGISTER_HELP: per-path_kind tooltip for the auto-register checkbox
_AUTO_REGISTER_HELP = {
    'raw': 'Auto-register lamellae from .mrc files found in this folder.',
    'relion_project': 'Auto-register lamellae from .mrc files found in this folder.',
    'segmentations': 'Auto-register lamellae from .mrc files found in this folder.',
    'other': 'Auto-register lamellae from .mrc files found in this folder.',
}

# -- _browse_for_folder: returns a folder path chosen via a native OS dialog, or None if cancelled
def _browse_for_folder() -> str | None:
    # Streamlit runs this in a worker thread; tkinter (and AppKit on macOS) requires
    # the main thread, so the dialog has to run in its own process.
    script = (
        "import tkinter as tk\n"
        "from tkinter import filedialog\n"
        "root = tk.Tk()\n"
        "root.withdraw()\n"
        "root.wm_attributes('-topmost', 1)\n"
        "print(filedialog.askdirectory())\n"
        "root.destroy()\n"
    )
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    return result.stdout.strip() or None

# -- _label_spacer: renders a blank line matching a text-input label's height, to align a widget below it with one that has a visible label
def _label_spacer() -> None:
    st.markdown('<div style="height: 1.9rem"></div>', unsafe_allow_html=True)

# -- _section_spacer: renders extra vertical gap between form sections
def _section_spacer() -> None:
    st.markdown('<div style="height: 1.25rem"></div>', unsafe_allow_html=True)

# -- _invalid_outline: draws a red outline around the st.container/widget with the given `key` when invalid is True
def _invalid_outline(key: str, invalid: bool) -> None:
    if invalid:
        st.markdown(
            f'<style>.st-key-{key} {{ outline: 2px solid #c62828; outline-offset: 2px; border-radius: 0.5rem; }}</style>',
            unsafe_allow_html=True,
        )

# -- _parse_args: returns the --db-path passed after Streamlit's own `--` separator
def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', required=True)
    return parser.parse_args()

# -- _render_import_folder_form: returns None, but renders the "Import folder" form and applies it on submit
def _render_import_folder_form(db_path: str, sessions: list) -> None:
    with st.expander('Import folder'):
        session_names = {s.session_name: s.session_id for s in sessions}
        target = st.selectbox('Session', ['<new session>'] + list(session_names.keys()))

        new_session_name = ''
        if target == '<new session>':
            current_name = st.session_state.get('import_new_session_name', '')
            name_ok, name_message = import_folder.session_name_available(list(session_names.keys()), current_name)
            _invalid_outline('import_new_session_name', bool(current_name) and not name_ok)
            new_session_name = st.text_input(
                'New session name',
                key='import_new_session_name',
                help=name_message if current_name else None,
            )
        else:
            name_ok = True

        _section_spacer()

        current_folder = st.session_state.get('import_folder_path', '')
        with st.spinner('Checking path...', show_time=False):
            folder_ok, folder_message = (False, '') if not current_folder else import_folder.check_folder_readable(Path(current_folder).expanduser())
        _invalid_outline('import_folder_path', bool(current_folder) and not folder_ok)
        path_col, browse_col = st.columns([5, 1])
        with path_col:
            folder = st.text_input(
                'Folder path',
                value=current_folder,
                key='import_folder_path',
                help=folder_message or None,
            )
        with browse_col:
            _label_spacer()  # align button with the text input, not its label
            if st.button('Browse…'):
                chosen = _browse_for_folder()
                if chosen:
                    st.session_state['import_folder_path'] = chosen
                    st.rerun()

        recursive = st.checkbox('Recurse into subdirectories', value=True)

        _section_spacer()

        current_kind = st.session_state.get('import_path_kind', '')
        # Only flag missing once the folder path is actually valid — Streamlit can't detect
        # "opened the dropdown and clicked away without picking" on its own, and gating on
        # a valid folder (rather than just a non-empty one) keeps this independent of the
        # folder path field's own error state.
        path_kind_missing = not current_kind and folder_ok
        _invalid_outline('import_path_kind', path_kind_missing)
        path_kind = st.selectbox('Folder contains', [''] + _PATH_KINDS, key='import_path_kind', format_func=lambda k: k or 'Select…')
        scan_for_mrcs = st.checkbox(
            'Auto-register',
            value=(path_kind != 'other'),
            help=_AUTO_REGISTER_HELP.get(path_kind, 'Select a folder kind first.'),
        )

        custom_kind = ''
        if path_kind == 'other':
            with st.popover('Advanced'):
                custom_kind = st.text_input('Custom key')

        _section_spacer()

        can_submit = bool(folder) and folder_ok and bool(path_kind) and (target != '<new session>' or (new_session_name and name_ok))
        if st.button('Import', disabled=not can_submit) and can_submit:
            folder_path = Path(folder).expanduser()
            if target == '<new session>':
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
