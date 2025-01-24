from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QSpinBox,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QTreeWidget, QTreeWidgetItem, QComboBox, 
    QFrame, QSplitter, QScrollArea, QGroupBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List, Optional
from parsers.mermaid_parser import MermaidParser
from core.network import IrrigationNetwork
from core.strahler import StrahlerAnalyzer
from core.blocks import BlockManager, BlockType, JointType
from core.analyzer import NetworkAnalyzer
from collections import defaultdict

class StrahlerLevel:
    def __init__(self, level: int, components: List[str], paths: List[List[str]]):
        self.level = level
        self.components = components
        self.paths = paths
        self.is_approved = False
        self.approval_time = None

class StrahlerTab(QWidget):
    network_analyzed = pyqtSignal(IrrigationNetwork)
    
    def __init__(self):
        super().__init__()
        self.network = None
        self.block_manager = BlockManager()
        self.network_analyzer = NetworkAnalyzer()
        self.strahler_analyzer = StrahlerAnalyzer()
        self.strahler_numbers = {}
        self.current_level = None
        self.strahler_levels = []
        self.visualization = None
        self.progress_bar = QProgressBar()
        self.details_text = QLabel()
        self.comp_details_text = QLabel()
        self.file_label = QLabel("No file selected")
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel
        left_panel = self._create_left_panel()
        content_splitter.addWidget(left_panel)
        
        # Right Panel
        right_panel = self._create_right_panel()
        content_splitter.addWidget(right_panel)
        
        main_layout.addWidget(content_splitter)

    def _create_left_panel(self) -> QWidget:
        # Copy the left panel implementation from NetworkAnalysisTab
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        visualization_widget = self._create_visualization()
        left_layout.addWidget(visualization_widget)
    
        # Level Assignment Section
        level_group = QGroupBox("Manual Level Assignment")
        level_layout = QVBoxLayout(level_group)
        
        comp_layout = QHBoxLayout()
        comp_layout.addWidget(QLabel("Component:"))
        self.component_combo = QComboBox()
        comp_layout.addWidget(self.component_combo)
        
        level_layout.addLayout(comp_layout)
        left_layout.addWidget(level_group)
        
        return left_widget

    def _create_right_panel(self) -> QWidget:
        # Copy the right panel implementation from NetworkAnalysisTab
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Block Management Section
        block_group = QGroupBox("Block Management")
        block_layout = QVBoxLayout(block_group)
        
        self.block_table = QTableWidget()
        self.block_table.setColumnCount(4)
        self.block_table.setHorizontalHeaderLabels([
            "Block ID", "Type", "Level", "Components"])
        block_layout.addWidget(self.block_table)
        
        right_layout.addWidget(block_group)
        
        return right_widget

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
                self.clear_analysis()
                
                with open(file_name, 'r') as file:
                    content = file.read()
                self.file_label.setText(f"Loaded: {file_name}")
                
                parser = MermaidParser()
                self.network = parser.parse(content)
                
                self.start_analysis()
                
            except Exception as e:
                self.file_label.setText(f"Error loading file: {str(e)}")
                print(f"Error details: {str(e)}")

    def clear_analysis(self):
        """Clear the current analysis"""
        self.network = None
        self.strahler_numbers.clear()
        self.current_level = None
        self.strahler_levels.clear()
        if self.visualization:
            self.visualization.clear_levels()
        self.progress_bar.setValue(0)
        self.details_text.setText("")
        self.comp_details_text.setText("")

    def start_analysis(self):
        """Start the Strahler analysis process"""
        if not self.network:
            return
            
        try:
            # Calculate Strahler numbers
            self.strahler_numbers = self.network.get_strahler_order()
            
            # Group components by level
            level_groups = self._group_by_level()
            
            # Create StrahlerLevel objects
            self.strahler_levels = []
            for level, components in sorted(level_groups.items(), reverse=True):
                paths = self._find_level_paths(level, components)
                self.strahler_levels.append(StrahlerLevel(
                    level=level,
                    components=components,
                    paths=paths
                ))
            
            # Set progress bar maximum to number of levels
            self.progress_bar.setMaximum(len(self.strahler_levels))
            
            # Update visualization
            self.visualization.set_levels(self.strahler_levels)
            
            # Set initial current level
            if self.strahler_levels:
                self.current_level = self.strahler_levels[0].level
            
            # Update details
            self._update_analysis_details()
            
        except Exception as e:
            print(f"Error in analysis: {str(e)}")
            self.details_text.setText(f"Error during analysis: {str(e)}")
    
    def _group_by_level(self) -> Dict[int, List[str]]:
        """Group components by their Strahler number"""
        groups = {}
        for comp_id, level in self.strahler_numbers.items():
            if level not in groups:
                groups[level] = []
            groups[level].append(comp_id)
        return groups
    
    def _find_level_paths(self, level: int, components: List[str]) -> List[List[str]]:
        """Find all paths between components at a given level"""
        paths = []
        visited = set()
        
        def find_paths(start: str, current_path: List[str]):
            if start in visited:
                return
                
            visited.add(start)
            current_path.append(start)
            
            if start in components and len(current_path) > 1:
                paths.append(current_path.copy())
            
            component = self.network.components[start]
            for next_id in component.connections_to:
                if self.strahler_numbers.get(next_id) == level:
                    find_paths(next_id, current_path.copy())
            
            visited.remove(start)
        
        for comp_id in components:
            find_paths(comp_id, [])
        
        return paths
    
    def _update_analysis_details(self):
        """Update the analysis details display"""
        if not self.network or not self.strahler_numbers:
            return
            
        details = []
        
        # Basic statistics
        total_components = len(self.strahler_numbers)
        max_level = max(self.strahler_numbers.values())
        approved_levels = sum(1 for level in self.strahler_levels if level.is_approved)
        
        details.append(f"Total Components: {total_components}")
        details.append(f"Maximum Strahler Level: {max_level}")
        details.append(f"Approved Levels: {approved_levels}/{len(self.strahler_levels)}")
        
        # Level statistics
        level_counts = {}
        for level in self.strahler_numbers.values():
            level_counts[level] = level_counts.get(level, 0) + 1
        
        details.append("\nComponents per Level:")
        for level in sorted(level_counts.keys()):
            details.append(f"Level {level}: {level_counts[level]} components")
            
            # Add approval status if applicable
            level_obj = next((l for l in self.strahler_levels if l.level == level), None)
            if level_obj and level_obj.is_approved:
                approval_time = level_obj.approval_time.strftime("%H:%M:%S")
                details.append(f"  ✓ Approved at {approval_time}")
        
        self.details_text.setText("\n".join(details))
    
    def on_level_approved(self, level: int):
        """Handle level approval"""
        if level != self.current_level:
            return
            
        # Update progress
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        
        # Update analysis details
        self._update_analysis_details()
        
        # Find next unapproved level
        next_level = None
        current_index = next((i for i, l in enumerate(self.strahler_levels) 
                            if l.level == level), -1)
        
        if current_index < len(self.strahler_levels) - 1:
            next_level = self.strahler_levels[current_index + 1].level
        
        self.current_level = next_level
    
    def on_component_selected(self, component_id: str):
        """Handle component selection"""
        if not self.network or component_id not in self.network.components:
            return
            
        component = self.network.components[component_id]
        
        details = [
            f"Component ID: {component_id}",
            f"Type: {component.component_type}",
            f"Strahler Number: {self.strahler_numbers.get(component_id, 'N/A')}",
            f"Connections From: {len(component.connections_from)}",
            f"Connections To: {len(component.connections_to)}"
        ]
        
        if component.connections_from:
            details.append("\nConnected From:")
            for conn in sorted(component.connections_from):
                details.append(f"- {conn}")
                
        if component.connections_to:
            details.append("\nConnected To:")
            for conn in sorted(component.connections_to):
                details.append(f"- {conn}")
        
        self.comp_details_text.setText("\n".join(details))