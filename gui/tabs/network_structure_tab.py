from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QFrame,
    QSplitter,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Optional
from parsers.mermaid_parser import MermaidParser
from core.network import IrrigationNetwork

class NetworkStructureTab(QWidget):
    """Tab for displaying and analyzing irrigation network structure"""
    
    def __init__(self):
        super().__init__()
        self.network: Optional[IrrigationNetwork] = None
        self.parser = MermaidParser()
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Create main splitter for left/right panel layout
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel - Network Structure
        left_panel = self.create_left_panel()
        self.main_splitter.addWidget(left_panel)
        
        # Right Panel - Component Details
        right_panel = self.create_right_panel()
        self.main_splitter.addWidget(right_panel)
        
        # Add file upload section at top
        upload_frame = self.create_upload_section()
        main_layout.addWidget(upload_frame)
        
        # Add splitter
        main_layout.addWidget(self.main_splitter)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
    
    def create_upload_section(self) -> QFrame:
        """Create the file upload section"""
        upload_frame = QFrame()
        upload_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        upload_layout = QHBoxLayout(upload_frame)
        
        self.upload_btn = QPushButton("Upload Network File")
        self.upload_btn.clicked.connect(self.upload_file)
        upload_layout.addWidget(self.upload_btn)
        
        self.file_label = QLabel("No file selected")
        upload_layout.addWidget(self.file_label)
        
        return upload_frame
    
    def create_left_panel(self) -> QWidget:
        """Create the left panel containing network structure view"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Level selection
        level_layout = QHBoxLayout()
        level_label = QLabel("Hierarchy Level:")
        self.level_combo = QComboBox()
        self.level_combo.currentIndexChanged.connect(self.on_level_selected)
        level_layout.addWidget(level_label)
        level_layout.addWidget(self.level_combo)
        layout.addLayout(level_layout)
        
        # Network tree
        self.network_tree = QTreeWidget()
        self.network_tree.setHeaderLabels(["Component", "Type", "Level"])
        self.network_tree.itemClicked.connect(self.on_component_selected)
        layout.addWidget(self.network_tree)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel containing component details"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Component details section
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        details_layout = QVBoxLayout(details_frame)
        
        details_label = QLabel("Component Details")
        details_layout.addWidget(details_label)
        
        self.details_tree = QTreeWidget()
        self.details_tree.setHeaderLabels(["Property", "Value"])
        details_layout.addWidget(self.details_tree)
        
        layout.addWidget(details_frame)
        
        # Paths section
        paths_frame = QFrame()
        paths_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        paths_layout = QVBoxLayout(paths_frame)
        
        paths_label = QLabel("Connected Paths")
        paths_layout.addWidget(paths_label)
        
        self.paths_tree = QTreeWidget()
        self.paths_tree.setHeaderLabels(["Path", "Components"])
        paths_layout.addWidget(self.paths_tree)
        
        layout.addWidget(paths_frame)
        
        return panel
    
    def upload_file(self):
        """Handle network file upload"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Network File",
            "",
            "Mermaid Files (*.mermaid);;All Files (*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r') as file:
                    content = file.read()
                self.file_label.setText(f"Loaded: {file_name}")
                
                # Parse network
                self.network = self.parser.parse(content)
                
                # Update UI
                self.update_level_combo()
                self.display_network_structure()
                
            except Exception as e:
                self.file_label.setText(f"Error loading file: {str(e)}")
    
    def update_level_combo(self):
        """Update hierarchy level combo box"""
        self.level_combo.clear()
        if self.network:
            levels = self.network.get_components_by_level()
            self.level_combo.addItem("All Levels")
            for level in sorted(levels.keys()):
                self.level_combo.addItem(f"Level {level}", level)
    
    def display_network_structure(self):
        """Display complete network structure in tree"""
        self.network_tree.clear()
        if not self.network:
            return
        
        # Start with root components (level 0)
        root_components = [comp_id for comp_id, comp 
                         in self.network.components.items() 
                         if comp.level == 0]
        
        for root_id in root_components:
            root_comp = self.network.components[root_id]
            root_item = self.create_tree_item(None, root_id, root_comp)
            self.add_child_components(root_item, root_id)
    
    def create_tree_item(self, parent: Optional[QTreeWidgetItem], 
                        comp_id: str, component: 'NetworkComponent') -> QTreeWidgetItem:
        """Create a tree item for a component"""
        if parent is None:
            item = QTreeWidgetItem(self.network_tree)
        else:
            item = QTreeWidgetItem(parent)
        
        item.setText(0, comp_id)
        item.setText(1, component.component_type)
        item.setText(2, str(component.level))
        return item
    
    def add_child_components(self, parent_item: QTreeWidgetItem, parent_id: str):
        """Add child components to tree"""
        if parent_id not in self.network.components:
            return
        
        parent = self.network.components[parent_id]
        for child_id in sorted(parent.connections_to):
            child = self.network.components[child_id]
            child_item = self.create_tree_item(parent_item, child_id, child)
            self.add_child_components(child_item, child_id)
    
    def on_level_selected(self, index: int):
        """Handle hierarchy level selection"""
        if not self.network or index < 0:
            return
        
        self.network_tree.clear()
        
        if index == 0:  # "All Levels" selected
            self.display_network_structure()
            return
        
        # Get components for selected level
        level = self.level_combo.currentData()
        components = self.network.get_components_by_level().get(level, [])
        
        # Add components to tree
        for comp_id in sorted(components):
            comp = self.network.components[comp_id]
            item = self.create_tree_item(None, comp_id, comp)
            # Add immediate children
            for child_id in sorted(comp.connections_to):
                if child_id in self.network.components:
                    child = self.network.components[child_id]
                    self.create_tree_item(item, child_id, child)
    
    def on_component_selected(self, item: QTreeWidgetItem):
        """Handle component selection in tree"""
        if not self.network:
            return
        
        component_id = item.text(0)
        if component_id in self.network.components:
            self.display_component_details(component_id)
            self.display_component_paths(component_id)
    
    def display_component_details(self, component_id: str):
        """Display component details in right panel"""
        self.details_tree.clear()
        
        component = self.network.components[component_id]
        details = {
            'ID': component_id,
            'Type': component.component_type,
            'Level': component.level,
            'Label': component.label,
            'Connections To': ', '.join(sorted(component.connections_to)) or 'None',
            'Connections From': ', '.join(sorted(component.connections_from)) or 'None'
        }
        
        for key, value in details.items():
            item = QTreeWidgetItem(self.details_tree)
            item.setText(0, key)
            item.setText(1, str(value))
    
    def display_component_paths(self, component_id: str):
        """Display paths connected to the component"""
        self.paths_tree.clear()
        
        # Get all paths that include this component
        if component_id.startswith('F'):  # If it's a field
            paths = self.network.get_field_feeding_path(component_id)
        else:  # For other components, find all paths that contain it
            paths = self.find_paths_containing_component(component_id)
        
        # Display paths
        for i, path in enumerate(paths, 1):
            item = QTreeWidgetItem(self.paths_tree)
            item.setText(0, f"Path {i}")
            item.setText(1, " → ".join(path))
    
    def find_paths_containing_component(self, component_id: str) -> List[List[str]]:
        """Find all paths that contain the given component"""
        paths = []
        visited = set()
        
        def dfs(current: str, path: List[str]):
            if current in visited:
                return
            visited.add(current)
            path.append(current)
            
            if not self.network.components[current].connections_to:
                if component_id in path:
                    paths.append(path.copy())
            else:
                for next_id in self.network.components[current].connections_to:
                    dfs(next_id, path.copy())
            
            visited.remove(current)
        
        # Start from root components
        root_components = [comp_id for comp_id, comp 
                         in self.network.components.items() 
                         if not comp.connections_from]
        
        for root_id in root_components:
            dfs(root_id, [])
        
        return paths