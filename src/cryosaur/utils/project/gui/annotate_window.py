'''
CRYOSAUR: lamella annotation main window (lamella list/reorder panel plus a PyVista 3D view)
'''

# -- Import external dependencies
from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from pyvistaqt import QtInteractor

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.project.schema import LamellaRecord, SessionRecord
from cryosaur.utils.log import log

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
        self._plotter_actor = None  # reused across lamella switches, see §4 of the design plan

        self._lamella_list = QListWidget()
        self._lamella_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        # Debounced: fires once on drop, not per mouse-move
        self._lamella_list.model().rowsMoved.connect(self._on_reordered)
        self._lamella_list.currentItemChanged.connect(self._on_lamella_selected)

        self._notes_box = QPlainTextEdit()
        add_note_button = QPushButton('Add note')
        add_note_button.clicked.connect(self._on_add_note)

        self._plotter = QtInteractor(self)
        self.geometry_ready.connect(self._on_geometry_ready)

        left_panel = QVBoxLayout()
        left_panel.addWidget(self._lamella_list)
        left_panel.addWidget(self._notes_box)
        left_panel.addWidget(add_note_button)

        layout = QHBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        layout.addWidget(left_widget, stretch=1)
        layout.addWidget(self._plotter.interactor, stretch=3)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._reload_lamellae()

    # -- _reload_lamellae: returns None, but refreshes the list widget from metadata only (no 3D geometry loaded here, see §4)
    def _reload_lamellae(self) -> None:
        self._lamella_list.clear()
        for lamella in store.list_lamellae(self.db_path, self.session.session_id):
            item = QListWidgetItem(f'{lamella.milling_order}: {lamella.lamella_name}')
            item.setData(Qt_UserRole, lamella.id)
            self._lamella_list.addItem(item)

    # -- _on_reordered: returns None, but persists the list widget's current order via a single atomic reorder_session call
    def _on_reordered(self, *_args) -> None:
        ordered_ids = [
            self._lamella_list.item(row).data(Qt_UserRole)
            for row in range(self._lamella_list.count())
        ]
        store.reorder_session(self.db_path, self.session.session_id, ordered_ids)
        self._reload_lamellae()

    # -- _on_lamella_selected: returns None, but kicks off background geometry loading for the newly selected lamella
    def _on_lamella_selected(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
            return
        lamella_id = current.data(Qt_UserRole)
        lamellae = {l.id: l for l in store.list_lamellae(self.db_path, self.session.session_id)}
        self._current_lamella = lamellae[lamella_id]

        from cryosaur.utils.project.geometry_worker import GeometryWorker
        worker = GeometryWorker(self.db_path, self._current_lamella, self.geometry_ready)
        self._pool.start(worker)

    # -- _on_geometry_ready: returns None, but updates the existing PyVista actor in place rather than clearing/rebuilding the scene
    def _on_geometry_ready(self, mesh) -> None:
        if self._plotter_actor is None:
            self._plotter_actor = self._plotter.add_mesh(mesh, reset_camera=False)
        else:
            self._plotter_actor.mapper.SetInputData(mesh)
        self._plotter.render()

    # -- _on_add_note: returns None, but writes the notes box's contents to the store for the currently selected lamella
    def _on_add_note(self) -> None:
        if self._current_lamella is None:
            log.warning('No lamella selected, nothing to attach the note to')
            return
        text = self._notes_box.toPlainText().strip()
        if not text:
            return
        store.add_note(self.db_path, self._current_lamella.id, text)
        self._notes_box.clear()


from PySide6.QtCore import Qt
Qt_UserRole = Qt.ItemDataRole.UserRole
