'''
CRYOSAUR: Streamlit dashboard for annotations
'''

# -- Import external dependencies
import argparse, subprocess, sys
import streamlit as st

# -- Import cryosaur utilities
from cryosaur.utils.project import store

# -- _parse_args: returns the --db-path passed after Streamlit's own `--` separator
def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', required=True)
    return parser.parse_args()

# -- main: renders the dashboard
def main() -> None:
    args = _parse_args()
    db_path = args.db_path

    st.title('cryosaur project view')

    sessions = store.list_sessions(db_path)
    if not sessions:
        st.info(f'No sessions found in {db_path}')
        return

    session_names = {s.session_name: s.session_id for s in sessions}
    chosen_name = st.selectbox('Session', list(session_names.keys()))
    session_id = session_names[chosen_name]
    session = store.get_session(db_path, session_id)

    st.caption(f'Paths: {session.paths}')

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
