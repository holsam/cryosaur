'''
CRYOSAUR: viewer main window (tabs for collections and tomograms)
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

# -- Import cryosaur utilities
from cryosaur.commands.viewer.utils.tomograms_tab import TomogramsTab

# -- _CollectionsTabStub: stub for Collections tab
class _CollectionsTabStub(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Collections view is not yet available.'))

# -- MainWindow: top-level viewer window, Collections and Tomograms as tabs
class MainWindow(QMainWindow):
    def __init__(self, project_dir: Path):
        super().__init__()
        self.setWindowTitle(f'cryosaur viewer - {project_dir}')
        tabs = QTabWidget()
        tabs.addTab(_CollectionsTabStub(), 'Collections')
        tabs.addTab(TomogramsTab(project_dir), 'Tomograms')
        self.setCentralWidget(tabs)
        self.resize(1200, 800)
