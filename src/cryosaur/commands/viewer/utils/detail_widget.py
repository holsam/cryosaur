'''
CRYOSAUR: viewer tomogram detail page (volume render, orthogonal slice sliders, click-to-annotate)
'''

# -- Import external dependencies
import uuid
import pyvista as pv
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from pyvistaqt import QtInteractor

# -- Import cryosaur utilities
from cryosaur.commands.viewer.utils.models import Annotation
from cryosaur.commands.viewer.utils.storage import load_annotations, save_annotations
from cryosaur.commands.viewer.utils.volume import load_volume
from cryosaur.utils.log import log

# -- Define constants
_BIN_FACTOR = 2
_ANNOTATION_COLUMNS = ('Label', 'Note', 'Position')

# -- _AnnotationDialog: small form for entering a new annotation's label and note
class _AnnotationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add annotation')
        self.label_input = QLineEdit()
        self.note_input = QLineEdit()
        form = QFormLayout()
        form.addRow('Label', self.label_input)
        form.addRow('Note', self.note_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

# -- TomogramDetailWidget: rotatable binned volume render, XY/XZ/YZ orthogonal slice sliders, click-to-annotate, and an annotations table
class TomogramDetailWidget(QWidget):
    '''
    self.actors is a name -> vtk actor dict so future layers can be added without restructuring
    '''

    def __init__(self, tomogram_path: Path, parent=None):
        super().__init__(parent)
        self.tomogram_path = tomogram_path
        self.grid = load_volume(tomogram_path, bin_factor=_BIN_FACTOR)
        self.annotations = load_annotations(tomogram_path)
        self.actors: dict[str, object] = {}

        self.plotter = QtInteractor(self)
        self.actors['volume'] = self.plotter.add_volume(self.grid, scalars='density', name='volume')

        self.xy_slider, self.xz_slider, self.yz_slider = (self._make_slice_slider() for _ in range(3))
        for slider in (self.xy_slider, self.xz_slider, self.yz_slider):
            slider.valueChanged.connect(self._update_slices)

        self.annotate_button = QPushButton('Add annotation')
        self.annotate_button.setCheckable(True)
        self.annotate_button.toggled.connect(self._toggle_picking)

        self.annotations_table = QTableWidget(0, len(_ANNOTATION_COLUMNS))
        self.annotations_table.setHorizontalHeaderLabels(_ANNOTATION_COLUMNS)
        self.annotations_table.itemSelectionChanged.connect(self._on_row_selected)

        self._build_layout()
        self._update_slices()
        self._refresh_table()

    # -- _make_slice_slider: returns a 0-100 slider defaulted to the volume's centre
    def _make_slice_slider(self) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(50)
        return slider

    def _build_layout(self):
        slice_row = QHBoxLayout()
        for label_text, slider in (('XY', self.xy_slider), ('XZ', self.xz_slider), ('YZ', self.yz_slider)):
            slice_row.addWidget(QLabel(label_text))
            slice_row.addWidget(slider)

        layout = QVBoxLayout(self)
        layout.addWidget(self.plotter.interactor)
        layout.addLayout(slice_row)
        layout.addWidget(self.annotate_button)
        layout.addWidget(self.annotations_table)

    # -- _update_slices: recomputes the three orthogonal slice planes from the current slider positions
    def _update_slices(self):
        bounds = self.grid.bounds  # (xmin, xmax, ymin, ymax, zmin, zmax)
        x = bounds[0] + (bounds[1] - bounds[0]) * self.yz_slider.value() / 100
        y = bounds[2] + (bounds[3] - bounds[2]) * self.xz_slider.value() / 100
        z = bounds[4] + (bounds[5] - bounds[4]) * self.xy_slider.value() / 100
        slices = self.grid.slice_orthogonal(x=x, y=y, z=z)
        self.actors['slices'] = self.plotter.add_mesh(slices, name='slices', scalars='density')

    def _toggle_picking(self, enabled: bool):
        if enabled:
            self.plotter.enable_point_picking(callback=self._on_pick, show_message=False, left_clicking=True)
        else:
            self.plotter.disable_picking()

    # -- _on_pick: opens the annotation dialog for a picked point, then appends and persists the result
    def _on_pick(self, point):
        dialog = _AnnotationDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        label = dialog.label_input.text().strip() or 'annotation'
        note = dialog.note_input.text().strip()
        annotation = Annotation(id=str(uuid.uuid4()), position=tuple(point), label=label, note=note)
        self.annotations.annotations.append(annotation)
        save_annotations(self.annotations)
        self._refresh_table()
        log.info(f'Added annotation <cyan>{label}</cyan> to <cyan>{self.tomogram_path.name}</cyan>')

    def _refresh_table(self):
        self.annotations_table.setRowCount(len(self.annotations.annotations))
        for row, annotation in enumerate(self.annotations.annotations):
            position_text = ', '.join(f'{v:.1f}' for v in annotation.position)
            for col, value in enumerate((annotation.label, annotation.note, position_text)):
                self.annotations_table.setItem(row, col, QTableWidgetItem(value))

    # -- _on_row_selected: drops a marker on the annotation selected in the table
    def _on_row_selected(self):
        rows = self.annotations_table.selectionModel().selectedRows()
        if not rows:
            return
        annotation = self.annotations.annotations[rows[0].row()]
        marker = pv.PolyData([annotation.position])
        self.actors['selected_annotation'] = self.plotter.add_mesh(marker, name='selected_annotation', color='yellow', point_size=20, render_points_as_spheres=True)
