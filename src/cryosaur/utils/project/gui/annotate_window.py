'''
CRYOSAUR: lamella annotation main window (lamella list/reorder panel, notes/points list plus a PyVista 3D view)
'''

# -- Import external dependencies
from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from pyvistaqt import QtInteractor

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.project import store
from cryosaur.utils.project.schema import LamellaRecord, SessionRecord
from cryosaur.utils.log import log

_Qt_UserRole = Qt.ItemDataRole.UserRole
_STATUS_OPTIONS = ['', 'milled', 'collected', 'discarded']

# -- AnnotateWindow: main window for `cryosaur project annotate`
class AnnotateWindow(QMainWindow):
    # geometry_ready: emitted on the worker thread pool once a lamella's mesh has been loaded/cached, so the UI can pick it up on the main thread
    geometry_ready = Signal(object)

    def __init__(self, db_path: Path, session: SessionRecord):
        super().__init__()
        self.db_path = db_path
        self.session = session
        self.setWindowTitle(f'cryosaur -- annotate: {session.session_name}')

        self._pool = QThreadPool.globalInstance()
        self._current_lamella: LamellaRecord | None = None
        self._mesh_actor = None
        self._points_actor = None

        self._lamella_list = QListWidget()
        self._lamella_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._lamella_list.model().rowsMoved.connect(self._on_reordered)
        self._lamella_list.currentItemChanged.connect(self._on_lamella_selected)

        self._status_combo = QComboBox()
        self._status_combo.addItems(_STATUS_OPTIONS)
        self._status_combo.currentTextChanged.connect(self._on_status_changed)

        delete_lamella_button = QPushButton('Delete lamella')
        delete_lamella_button.clicked.connect(self._on_delete_lamella)

        self._notes_list = QListWidget()
        self._new_note_box = QPlainTextEdit()
        add_note_button = QPushButton('Add note')
        add_note_button.clicked.connect(self._on_add_note)
        delete_note_button = QPushButton('Delete selected note')
        delete_note_button.clicked.connect(self._on_delete_note)

        self._points_list = QListWidget()
        delete_point_button = QPushButton('Delete selected point')
        delete_point_button.clicked.connect(self._on_delete_point)

        self._plotter = QtInteractor(self)
        self._plotter.enable_point_picking(callback=self._on_point_picked, show_message=False, use_picker=True)
        self.geometry_ready.connect(self._on_geometry_ready)

        left_panel = QVBoxLayout()
        left_panel.addWidget(self._lamella_list)
        left_panel.addWidget(QLabel('Status'))
        left_panel.addWidget(self._status_combo)
        left_panel.addWidget(delete_lamella_button)
        left_panel.addWidget(QLabel('Notes'))
        left_panel.addWidget(self._notes_list)
        left_panel.addWidget(self._new_note_box)
        left_panel.addWidget(add_note_button)
        left_panel.addWidget(delete_note_button)
        left_panel.addWidget(QLabel('Points (click the mesh to add one)'))
        left_panel.addWidget(self._points_list)
        left_panel.addWidget(delete_point_button)

        layout = QHBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        layout.addWidget(left_widget, stretch=1)
        layout.addWidget(self._plotter.interactor, stretch=3)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._reload_lamellae()

    # -- _reload_lamellae: returns None but refreshes the list widget from metadata only
    def _reload_lamellae(self) -> None:
        self._lamella_list.clear()
        for lamella in store.list_lamellae(self.db_path, self.session.session_id):
            item = QListWidgetItem(f'{lamella.milling_order}: {lamella.lamella_name}')
            item.setData(_Qt_UserRole, lamella.id)
            self._lamella_list.addItem(item)

    # -- _on_reordered: returns None, but persists the list widget's current order via a single atomic reorder_session call
    def _on_reordered(self, *_args) -> None:
        ordered_ids = [self._lamella_list.item(row).data(_Qt_UserRole) for row in range(self._lamella_list.count())]
        store.reorder_session(self.db_path, self.session.session_id, ordered_ids)
        self._reload_lamellae()

    # -- _on_lamella_selected: returns None, but loads metadata/notes/points immediately and kicks off background geometry loading
    def _on_lamella_selected(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
            self._current_lamella = None
            return
        lamella_id = current.data(_Qt_UserRole)
        self._current_lamella = store.get_lamella(self.db_path, lamella_id)

        self._status_combo.blockSignals(True)
        self._status_combo.setCurrentText(self._current_lamella.status or '')
        self._status_combo.blockSignals(False)

        self._reload_notes()
        self._reload_points()

        from cryosaur.commands.project.utils.geometry_worker import GeometryWorker
        self._pool.start(GeometryWorker(self.db_path, self._current_lamella, self.geometry_ready))

    # -- _on_geometry_ready: returns None but updates the existing PyVista mesh actor in place rather than clearing/rebuilding the scene
    def _on_geometry_ready(self, mesh) -> None:
        if self._mesh_actor is None:
            self._mesh_actor = self._plotter.add_mesh(mesh, reset_camera=False)
        else:
            self._mesh_actor.mapper.SetInputData(mesh)
        self._plotter.render()

    # -- _on_status_changed: returns None, but persists the newly selected status for the current lamella
    def _on_status_changed(self, text: str) -> None:
        if self._current_lamella is None:
            return
        store.update_lamella(self.db_path, self._current_lamella.id, status=text or None)

    # -- _on_delete_lamella: returns None, but deletes the current lamella (cascading to its notes/points/overlays) after confirmation
    def _on_delete_lamella(self) -> None:
        if self._current_lamella is None:
            return
        confirm = QMessageBox.question(self, 'Delete lamella', f'Delete {self._current_lamella.lamella_name!r} and all its notes/points/overlays? This cannot be undone.')
        if confirm != QMessageBox.StandardButton.Yes:
            return
        store.delete_lamella(self.db_path, self._current_lamella.id)
        self._current_lamella = None
        self._reload_lamellae()

    # -- _reload_notes: returns None, but refreshes the notes list for the current lamella
    def _reload_notes(self) -> None:
        self._notes_list.clear()
        if self._current_lamella is None:
            return
        annotations = store.get_annotations_for_lamella(self.db_path, self._current_lamella.id)
        for note in annotations['notes']:
            item = QListWidgetItem(note.text)
            item.setData(_Qt_UserRole, note.id)
            self._notes_list.addItem(item)

    # -- _on_add_note: returns None, but writes the new-note box's contents to the store for the currently selected lamella
    def _on_add_note(self) -> None:
        if self._current_lamella is None:
            log.warning('No lamella selected, nothing to attach the note to')
            return
        text = self._new_note_box.toPlainText().strip()
        if not text:
            return
        store.add_note(self.db_path, self._current_lamella.id, text)
        self._new_note_box.clear()
        self._reload_notes()

    # -- _on_delete_note: returns None, but deletes the selected note
    def _on_delete_note(self) -> None:
        item = self._notes_list.currentItem()
        if item is None:
            return
        store.delete_note(self.db_path, item.data(_Qt_UserRole))
        self._reload_notes()

    # -- _reload_points: returns None, but refreshes the points list and redraws every point as a glyph (plan.md §4: glyphs reserved for the small number of interactively placed points)
    def _reload_points(self) -> None:
        import pyvista as pv

        self._points_list.clear()
        if self._points_actor is not None:
            self._plotter.remove_actor(self._points_actor)
            self._points_actor = None
        if self._current_lamella is None:
            return

        annotations = store.get_annotations_for_lamella(self.db_path, self._current_lamella.id)
        coords = []
        for point in annotations['points']:
            item = QListWidgetItem(f'{point.label or "(unlabelled)"} ({point.x:.1f}, {point.y:.1f}, {point.z:.1f})')
            item.setData(_Qt_UserRole, point.id)
            self._points_list.addItem(item)
            coords.append((point.x, point.y, point.z))

        if coords:
            cloud = pv.PolyData(coords)
            self._points_actor = self._plotter.add_mesh(
                cloud, render_points_as_spheres=True, point_size=14, color='yellow', reset_camera=False,
            )
        self._plotter.render()

    # -- _on_point_picked: returns None, but prompts for a label and stores a point at the picked position (pyvistaqt picking callback)
    def _on_point_picked(self, point) -> None:
        if self._current_lamella is None:
            log.warning('No lamella selected, ignoring pick')
            return
        label, _ok = QInputDialog.getText(self, 'Label point', 'Label (optional):')
        try:
            store.add_point(self.db_path, self._current_lamella.id, float(point[0]), float(point[1]), float(point[2]), label=label or None)
        except CryosaurError as exc:
            QMessageBox.warning(self, 'Could not add point', str(exc))
            return
        self._reload_points()

    # -- _on_delete_point: returns None, but deletes the selected point
    def _on_delete_point(self) -> None:
        item = self._points_list.currentItem()
        if item is None:
            return
        store.delete_point(self.db_path, item.data(_Qt_UserRole))
        self._reload_points()
