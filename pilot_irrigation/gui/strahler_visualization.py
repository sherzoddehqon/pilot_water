from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout,
    QPushButton, 
    QLabel, 
    QTreeWidget, 
    QTreeWidgetItem,
    QGroupBox,
    QScrollArea,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StrahlerLevel:
    """Data class for storing Strahler level information"""
    level: int
    components: List[str]
    paths: List[List[str]]
    is_approved: bool = False
    approval_time: Optional[datetime] = None

class StrahlerLevelVisualizer(QGroupBox):
    """Widget for visualizing a single Strahler level"""
    
    level_approved = pyqtSignal(int)  # Signal emitted when level is approved
    component_selected = pyqtSignal(str)  # Signal emitted when component is selected
    
    def __init__(self, level_data: StrahlerLevel, parent=None):
        super().__init__(parent)
        self.level_data = level_data
        self.initUI()
        
    def initUI(self):
        """Initialize the UI components"""
        self.setTitle(f"Strahler Level {self.level_data.level}")
        layout = QVBoxLayout(self)
        
        # Add header with statistics
        header = QHBoxLayout()
        stats_label = QLabel(
            f"Components: {len(self.level_data.components)} | "
            f"Paths: {len(self.level_data.paths)}"
        )
        header.addWidget(stats_label)
        header.addStretch()
        
        # Add approval button
        if not self.level_data.is_approved:
            self.approve_btn = QPushButton("Approve Level")
            self.approve_btn.clicked.connect(self._on_approve)
            header.addWidget(self.approve_btn)
        else:
            approval_label = QLabel("✓ Approved")
            approval_label.setStyleSheet("color: green;")
            header.addWidget(approval_label)
        
        layout.addLayout(header)
        
        # Create tree widget for components and paths
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component/Path", "Type", "Details"])
        self.tree.setMinimumHeight(200)
        self.tree.itemClicked.connect(self._on_item_selected)
        self.populate_tree()
        layout.addWidget(self.tree)
        
    def populate_tree(self):
        """Populate the tree with components and paths"""
        self.tree.clear()
        
        try:
            # Components section
            comp_root = QTreeWidgetItem(self.tree)
            comp_root.setText(0, f"Components ({len(self.level_data.components)})")
            comp_root.setExpanded(True)
            
            # Group components by type
            comp_groups = self._group_components()
            for type_name, comps in comp_groups.items():
                type_item = QTreeWidgetItem(comp_root)
                type_item.setText(0, type_name)
                type_item.setText(1, str(len(comps)))
                
                for comp in sorted(comps):
                    comp_item = QTreeWidgetItem(type_item)
                    comp_item.setText(0, comp)
                    comp_item.setText(1, self._get_component_type(comp))
            
            # Paths section
            if self.level_data.paths:
                paths_root = QTreeWidgetItem(self.tree)
                paths_root.setText(0, f"Paths ({len(self.level_data.paths)})")
                paths_root.setExpanded(True)
                
                # Group paths by start component
                path_groups = self._group_paths()
                for start_comp, paths in path_groups.items():
                    start_item = QTreeWidgetItem(paths_root)
                    start_item.setText(0, f"From {start_comp}")
                    start_item.setText(1, f"{len(paths)} paths")
                    
                    for path in paths:
                        path_item = QTreeWidgetItem(start_item)
                        path_item.setText(0, " → ".join(path))
                        path_item.setText(2, f"{len(path)} nodes")
                        
        except Exception as e:
            error_item = QTreeWidgetItem(self.tree)
            error_item.setText(0, "Error in visualization")
            error_item.setText(1, str(e))
    
    def _group_components(self) -> Dict[str, List[str]]:
        """Group components by their type"""
        groups = {}
        for comp in self.level_data.components:
            comp_type = self._get_component_type(comp)
            if comp_type not in groups:
                groups[comp_type] = []
            groups[comp_type].append(comp)
        return groups
    
    def _group_paths(self) -> Dict[str, List[List[str]]]:
        """Group paths by their starting component"""
        groups = {}
        for path in self.level_data.paths:
            if not path:
                continue
            start = path[0]
            if start not in groups:
                groups[start] = []
            groups[start].append(path)
        return groups
    
    def _get_component_type(self, comp_id: str) -> str:
        """Extract component type from ID"""
        if '_' in comp_id:
            prefix = comp_id.split('_')[0]
        else:
            prefix = comp_id[:2]
            
        type_map = {
            'DP': 'Distribution Point',
            'MC': 'Main Canal',
            'SC': 'Secondary Canal',
            'TC': 'Tertiary Canal',
            'GT': 'Gate',
            'SW': 'Smart Water Device',
            'F': 'Field'
        }
        return type_map.get(prefix, 'Unknown')
    
    def _on_approve(self):
        """Handle level approval"""
        self.level_data.is_approved = True
        self.level_data.approval_time = datetime.now()
        self.approve_btn.setEnabled(False)
        self.approve_btn.setText("Approved ✓")
        self.level_approved.emit(self.level_data.level)
    
    def _on_item_selected(self, item: QTreeWidgetItem, column: int):
        """Handle tree item selection"""
        if not item.parent():  # Skip root items
            return
            
        # If it's a component item, emit the component ID
        if item.text(1) in self._get_component_type(item.text(0)):
            self.component_selected.emit(item.text(0))

class StrahlerVisualization(QWidget):
    """Main widget for visualizing Strahler analysis"""
    
    level_approved = pyqtSignal(int)  # Signal when a level is approved
    component_selected = pyqtSignal(str)  # Signal when a component is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level_widgets: Dict[int, StrahlerLevelVisualizer] = {}
        self.initUI()
        
    def initUI(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        
        # Create scrollable area for levels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for level visualizers
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.addStretch()
        scroll.setWidget(self.container)
        
        layout.addWidget(scroll)
        
    def set_levels(self, levels: List[StrahlerLevel]):
        """Set the levels to be visualized"""
        # Clear existing level widgets
        self.clear_levels()
        
        # Remove stretch if exists
        if self.container_layout.count() > 0:
            self.container_layout.takeAt(self.container_layout.count() - 1)
        
        # Add new level widgets
        for level_data in sorted(levels, key=lambda x: x.level, reverse=True):
            level_vis = StrahlerLevelVisualizer(level_data)
            level_vis.level_approved.connect(self._on_level_approved)
            level_vis.component_selected.connect(self._on_component_selected)
            
            self.container_layout.addWidget(level_vis)
            self.level_widgets[level_data.level] = level_vis
        
        # Add stretch at the end
        self.container_layout.addStretch()
    
    def clear_levels(self):
        """Clear all level visualizers"""
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.level_widgets.clear()
    
    def _on_level_approved(self, level: int):
        """Handle level approval"""
        self.level_approved.emit(level)
    
    def _on_component_selected(self, component_id: str):
        """Handle component selection"""
        self.component_selected.emit(component_id)