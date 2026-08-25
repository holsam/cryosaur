'''
CRYOSAUR: renders a session's lamellae (status/notes/points/screenshot) as a single Markdown report
'''

# -- Import external dependencies
import os
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.project.schema import LamellaRecord, SessionRecord

# -- render_report_markdown: returns the full Markdown document text for session, given each lamella paired with its get_annotations_for_lamella() dict
def render_report_markdown(session: SessionRecord, lamellae_with_annotations: list[tuple[LamellaRecord, dict]], output_dir: Path) -> str:
    lines = [f'# {session.session_name}', '']
    for lamella, annotations in lamellae_with_annotations:
        lines.append(f'## {lamella.lamella_name}')
        lines.append(f'Status: {lamella.status or "(none)"}')
        lines.append('')

        for screenshot in annotations['screenshots']:
            screenshot_path = Path(screenshot.path)
            rel = os.path.relpath(screenshot_path, output_dir)
            image_link = rel if not rel.startswith('..') else str(screenshot_path)
            lines.append(f'![{lamella.lamella_name}]({image_link})')
            lines.append('')

        if annotations['notes']:
            lines.append('**Notes:**')
            for note in annotations['notes']:
                lines.append(f'- {note.text}')
            lines.append('')

        if annotations['points']:
            lines.append('**Points:**')
            for point in annotations['points']:
                lines.append(f'- {point.label or "(unlabelled)"}: ({point.x:.1f}, {point.y:.1f}, {point.z:.1f})')
            lines.append('')

    return '\n'.join(lines)