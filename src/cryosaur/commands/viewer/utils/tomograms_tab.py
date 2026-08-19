'''
CRYOSAUR: viewer tomogram gallery tab (thumbnail grid of every MRC file, opens detail view on double-click)
'''

# -- Import external dependencies
import mrcfile, numpy as np
from pathlib import Path
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStackedWidget, QVBoxLayout, QWidget

# -- Import cryosaur utilities
from cryosaur.utils.io import _find_files_by_extension
from cryosaur.commands.viewer.utils.detail_widget import TomogramDetailWidget

# -- Define constants
_THUMBNAIL_SIZE = 128

# -- _middle_slice_thumbnail: returns a QPixmap of the tomogram's middle Z slice, normalised to 8-bit
def _middle_slice_thumbnail(mrc_path: Path) -> QPixmap:
    try:
        with mrcfile.open(mrc_path, permissive=True) as mrc:
            data = mrc.data
    except ValueError, RuntimeWarning as e:
        log.error(f'Could not load MRC from <cyan>{path}</cyan>: {e}')
        raise CryosaurError(f'Could not load MRC from <cyan>{path}</cyan>: {e}')
    plane = data[data.shape[0] // 2]
    plane = plane - plane.min()
    if plane.max() > 0:
        plane = plane / plane.max() * 255
    image = Image.fromarray(plane.astype(np.uint8)).convert('L')
    image.thumbnail((_THUMBNAIL_SIZE, _THUMBNAIL_SIZE))
    return QPixmap.fromImage(ImageQt(image))

# -- TomogramsTab: gallery of every tomogram in a project directory, clickable to open detail page
class TomogramsTab(QWidget):
    def __init__(self, project_dir: Path, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir
        self.tomogram_paths = _find_files_by_extension(project_dir, 'mrc')

        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.IconMode)
        self.gallery.setIconSize(QSize(_THUMBNAIL_SIZE, _THUMBNAIL_SIZE))
        self.gallery.setResizeMode(QListWidget.Adjust)
        for path in self.tomogram_paths:
            item = QListWidgetItem(QIcon(_middle_slice_thumbnail(path)), path.name)
            item.setData(Qt.UserRole, path)
            self.gallery.addItem(item)
        self.gallery.itemDoubleClicked.connect(self._open_detail)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.gallery)

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)

    # -- _open_detail: opens (or reuses) the detail widget
    def _open_detail(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        detail = TomogramDetailWidget(path)
        self.stack.addWidget(detail)
        self.stack.setCurrentWidget(detail)
