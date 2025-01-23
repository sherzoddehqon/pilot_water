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
    QGroupBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List, Optional
from parsers.mermaid_parser import MermaidParser
from core.network import IrrigationNetwork
from core.strahler import StrahlerAnalyzer
from core.blocks import BlockManager, BlockType, JointType
from core.analyzer import NetworkAnalyzer
from collections import defaultdict  
# This is needed for blocks_by_type in _populate_hierarchy



class AnalysisStep:
    """Represents a single analysis step"""
    def __init__(self, number: int, description: str, components: List, 
                 requires_approval: bool = False):
        self.step_number = number
        self.description = description
        self.components = components
        self.requires_approval = requires_approval
        self.approved = False

class AnalysisStepWidget(QGroupBox):
    """Widget for displaying and interacting with a single analysis step"""
    approved = pyqtSignal(int)
    
    def __init__(self, step: AnalysisStep, parent=None):
        super().__init__(parent)
        self.step = step
        print(f"\nInitializing Step {step.step_number} widget")
        self.initUI()
        
    def initUI(self):
        self.setTitle(f"Step {self.step.step_number}: {self.step.description}")
        layout = QVBoxLayout(self)
        
        # Create tree widget for components
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component", "Type", "Details"])
        self.tree.setMinimumHeight(150)
        self.populate_tree()
        layout.addWidget(self.tree)
        
        # Add approval button if required
        if self.step.requires_approval:
            approve_layout = QHBoxLayout()
            self.approve_btn = QPushButton("Approve Step")
            self.approve_btn.clicked.connect(self.on_approve)
            approve_layout.addStretch()
            approve_layout.addWidget(self.approve_btn)
            layout.addLayout(approve_layout)
            
            self.approve_btn.setEnabled(not self.step.approved)
            if self.step.approved:
                self.approve_btn.setText("Approved ✓")
    
    def populate_tree(self):
        """Populate tree with step components"""
        self.tree.clear()
        
        try:
            if self.step.step_number == 1:  # Component identification
                self._populate_components()
            elif self.step.step_number == 2:  # Block creation
                self._populate_blocks()
            elif self.step.step_number == 3:  # Hierarchy analysis
                self._populate_hierarchy()
            elif self.step.step_number == 4:  # Joint detection
                self._populate_joints()
            elif self.step.step_number == 5:  # Final structure
                self._populate_final_structure()
                
        except Exception as e:
            error_item = QTreeWidgetItem(self.tree)
            error_item.setText(0, "Error displaying components")
            error_item.setText(1, str(e))
            print(f"Error in populate_tree: {str(e)}")
    
    def _populate_components(self):
        """Populate initial component identification"""
        components_by_type = {}
        for comp in self.step.components:
            comp_type = comp.get('type', 'unknown')
            if comp_type not in components_by_type:
                components_by_type[comp_type] = []
            components_by_type[comp_type].append(comp)
        
        for comp_type, components in sorted(components_by_type.items()):
            type_item = QTreeWidgetItem(self.tree)
            type_item.setText(0, f"{comp_type.replace('_', ' ').title()} ({len(components)})")
            type_item.setExpanded(True)
            
            for comp in sorted(components, key=lambda x: x['id']):
                comp_item = QTreeWidgetItem(type_item)
                comp_item.setText(0, comp['id'])
                comp_item.setText(1, comp['type'])
                comp_item.setText(2, comp.get('label', ''))
    
    def _populate_blocks(self):
        """Populate block structure"""
        blocks_by_type = {}
        for block in self.step.components:
            block_type = block['type'].value
            if block_type not in blocks_by_type:
                blocks_by_type[block_type] = []
            blocks_by_type[block_type].append(block)
    
        # Add blocks in hierarchical order
        for block_type in ['main', 'distribution', 'terminal']:
            if block_type in blocks_by_type:
                blocks = blocks_by_type[block_type]
                type_item = QTreeWidgetItem(self.tree)
                type_item.setText(0, f"{block_type.title()} Blocks ({len(blocks)})")
                type_item.setExpanded(True)
            
                # Sort blocks by level then ID
                for block in sorted(blocks, key=lambda x: (x['level'], x['id'])):
                    block_item = QTreeWidgetItem(type_item)
                    block_item.setText(0, block['id'])
                    block_item.setText(1, str(len(block['components'])) + " components")
                    block_item.setText(2, f"Level {block['level']}")

    def _populate_hierarchy(self):
        """Populate hierarchy analysis"""
        # Sort levels in descending order (highest level first)
        for level in sorted(self.step.components.keys(), reverse=True):
            blocks = self.step.components[level]
            level_item = QTreeWidgetItem(self.tree)
            level_item.setText(0, f"Level {level}")
            level_item.setText(1, f"{len(blocks)} blocks")
            level_item.setExpanded(True)
            
            # Group blocks by type within each level
            blocks_by_type = defaultdict(list)
            for block in blocks:
                blocks_by_type[block['type'].value].append(block)
        
            # Add blocks grouped by type
            for block_type, type_blocks in sorted(blocks_by_type.items()):
                type_item = QTreeWidgetItem(level_item)
                type_item.setText(0, f"{block_type.title()} ({len(type_blocks)})")
            
                for block in sorted(type_blocks, key=lambda x: x['id']):
                    block_item = QTreeWidgetItem(type_item)
                    block_item.setText(0, block['id'])
                    block_item.setText(1, str(len(block['components'])) + " components")
                    block_item.setText(2, block['type'].value)
    
    def _populate_joints(self):
        """Populate joint analysis"""
        joints_by_type = {'internal': [], 'confluence': []}
        for joint in self.step.components:
            joint_type = joint['type'].value
            joints_by_type[joint_type].append(joint)
        
        for joint_type, joints in joints_by_type.items():
            type_item = QTreeWidgetItem(self.tree)
            type_item.setText(0, f"{joint_type.title()} Joints ({len(joints)})")
            type_item.setExpanded(True)
            
            for joint in sorted(joints, key=lambda x: x['id']):
                joint_item = QTreeWidgetItem(type_item)
                joint_item.setText(0, joint['id'])
                joint_item.setText(1, f"Level {joint['level']}")
                joint_item.setText(2, f"{len(joint['connections'])} connections")
    
    def _populate_final_structure(self):
        """Populate final network structure"""
        for block in sorted(self.step.components, key=lambda x: (x['level'], x['id'])):
            block_item = QTreeWidgetItem(self.tree)
            block_item.setText(0, block['id'])
            block_item.setText(1, f"Level {block['level']}")
            block_item.setText(2, block['type'].value)
            block_item.setExpanded(True)
            
            # Add components
            comp_item = QTreeWidgetItem(block_item)
            comp_item.setText(0, "Components")
            comp_item.setText(1, str(len(block['components'])))
            for comp_id in sorted(block['components']):
                comp_child = QTreeWidgetItem(comp_item)
                comp_child.setText(0, comp_id)
            
            # Add joints
            if block['joints']:
                joint_item = QTreeWidgetItem(block_item)
                joint_item.setText(0, "Joints")
                joint_item.setText(1, str(len(block['joints'])))
                for joint in sorted(block['joints'], key=lambda x: x['id']):
                    joint_child = QTreeWidgetItem(joint_item)
                    joint_child.setText(0, joint['id'])
                    joint_child.setText(1, joint['type'].value)
    
    def on_approve(self):
        """Handle step approval"""
        self.step.approved = True
        self.approve_btn.setText("Approved ✓")
        self.approve_btn.setEnabled(False)
        self.approved.emit(self.step.step_number)

class NetworkAnalysisTab(QWidget):
    """Main network analysis tab"""
    network_processed = pyqtSignal(IrrigationNetwork)
    proceed_to_strahler = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        # Add new member variables
        self.block_table = None
        self.confluence_tree = None
        self.component_combo = None
        self.level_spinner = None
        
        # Keep existing initialization
        self.network = None
        self.block_manager = BlockManager()
        self.network_analyzer = NetworkAnalyzer()
        self.strahler_analyzer = StrahlerAnalyzer()
        self.analysis_steps: List[AnalysisStep] = []
        self.step_widgets: Dict[int, AnalysisStepWidget] = {}
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # File Upload Section (keep existing)
        upload_frame = self._create_upload_section()
        main_layout.addWidget(upload_frame)
        
        # Main Content Splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel - Add manual level assignment
        left_panel = self._create_left_panel()
        content_splitter.addWidget(left_panel)
        
        # Right Panel - Add block management and confluence
        right_panel = self._create_right_panel()
        content_splitter.addWidget(right_panel)
        
        main_layout.addWidget(content_splitter)

    def _create_left_panel(self) -> QWidget:
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Level Assignment Section
        level_group = QGroupBox("Manual Level Assignment")
        level_layout = QVBoxLayout(level_group)
        
        # Component selector
        comp_layout = QHBoxLayout()
        comp_layout.addWidget(QLabel("Component:"))
        self.component_combo = QComboBox()
        comp_layout.addWidget(self.component_combo)
        
        # Level spinner
        level_spin_layout = QHBoxLayout()
        level_spin_layout.addWidget(QLabel("Level:"))
        self.level_spinner = QSpinBox()
        self.level_spinner.setRange(0, 10)
        level_spin_layout.addWidget(self.level_spinner)
        
        # Assign button
        assign_btn = QPushButton("Assign Level")
        assign_btn.clicked.connect(self.assign_level)
        
        level_layout.addLayout(comp_layout)
        level_layout.addLayout(level_spin_layout)
        level_layout.addWidget(assign_btn)
        left_layout.addWidget(level_group)
        
        # Keep existing steps section
        steps_scroll = QScrollArea()
        steps_scroll.setWidgetResizable(True)
        steps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.addStretch()
        steps_scroll.setWidget(self.steps_container)
        
        left_layout.addWidget(steps_scroll)
        
        return left_widget

    def _create_right_panel(self) -> QWidget:
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
        
        # Confluence Analysis Section
        confluence_group = QGroupBox("Confluence Analysis")
        confluence_layout = QVBoxLayout(confluence_group)
        
        self.confluence_tree = QTreeWidget()
        self.confluence_tree.setHeaderLabels([
            "Source", "Confluence Point", "Downstream"])
        confluence_layout.addWidget(self.confluence_tree)
        
        right_layout.addWidget(confluence_group)
        
        return right_widget

    # Add new methods
    def assign_level(self):
        if not self.network or not self.block_manager:
            return
            
        component_id = self.component_combo.currentText()
        new_level = self.level_spinner.value()
        
        if component_id in self.network.components:
            # Update level in network
            self.network.components[component_id].level = new_level
            
            # Update block hierarchy if needed
            if self.block_manager:
                self.block_manager.update_component_level(component_id, new_level)
            
            # Refresh UI
            self.update_block_table()
            self.update_confluence_visualization()

    def update_block_table(self):
        self.block_table.setRowCount(0)
        if not self.block_manager:
            return
            
        for block_id, block in self.block_manager.blocks.items():
            row = self.block_table.rowCount()
            self.block_table.insertRow(row)
            
            self.block_table.setItem(row, 0, QTableWidgetItem(block_id))
            self.block_table.setItem(row, 1, 
                QTableWidgetItem(block.block_type.value))
            self.block_table.setItem(row, 2, 
                QTableWidgetItem(str(block.hierarchy_level)))
            self.block_table.setItem(row, 3, 
                QTableWidgetItem(", ".join(block.components)))

    def update_confluence_visualization(self):
        self.confluence_tree.clear()
        if not self.network:
            return
            
        # Find confluence points (nodes with multiple inputs)
        confluence_points = {
            comp_id: comp for comp_id, comp in self.network.components.items()
            if len(comp.connections_from) > 1
        }
        
        for point_id, point in confluence_points.items():
            item = QTreeWidgetItem(self.confluence_tree)
            item.setText(0, ", ".join(point.connections_from))
            item.setText(1, point_id)
            item.setText(2, ", ".join(point.connections_to))

    # Update existing methods to integrate new functionality
    
    def upload_file(self):
        """Handle network file upload and start analysis"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Network File",
            "",
            "Mermaid Files (*.mermaid);;All Files (*)"
        )
    
        if file_name:
            try:
                # Clear previous analysis
                self.clear_analysis()
                
                # Load and parse file
                with open(file_name, 'r') as file:
                    content = file.read()
                self.file_label.setText(f"Loaded: {file_name}")
                
                # Parse network
                parser = MermaidParser()
                self.network = parser.parse(content)
                
                # Update component selector
                self.component_combo.clear()
                self.component_combo.addItems(sorted(self.network.components.keys()))
                
                # Start analysis
                self.start_analysis()
                
            except Exception as e:
                self.file_label.setText(f"Error loading file: {str(e)}")
                print(f"Error details: {str(e)}")

    def start_analysis(self):
        """Start the network analysis process"""
        if not self.network:
            return
            
        # Initialize analysis components
        self.block_manager = self.network_analyzer.analyze_network(self.network)
        self.analysis_steps = self.create_analysis_steps()
        
        # Update UI components
        self.update_block_table()
        self.update_confluence_visualization()
        
        # Handle analysis steps
        if self.steps_layout.count() > 0:
            self.steps_layout.takeAt(self.steps_layout.count() - 1)
        
        for step in self.analysis_steps:
            step_widget = AnalysisStepWidget(step)
            if step.requires_approval:
                step_widget.approved.connect(self.on_step_approved)
            self.steps_layout.addWidget(step_widget)
            self.step_widgets[step.step_number] = step_widget
        
        self.steps_layout.addStretch()
        self.update_progress()
        
        # Update level assignments
        max_level = max(comp.level for comp in self.network.components.values() 
                    if comp.level is not None)
        self.level_spinner.setRange(0, max_level + 1)
    
    def clear_analysis(self):
        """Clear previous analysis results"""
        self.network = None
        self.analysis_steps = []
        self.step_widgets.clear()
        
        # Clear steps layout
        while self.steps_layout.count():
            child = self.steps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add back the stretch
        self.steps_layout.addStretch()
        
        # Reset progress
        self.progress_bar.setValue(0)
    
    def update_progress(self):
        """Update progress bar based on completed steps"""
        completed = len([step for step in self.analysis_steps 
                        if not step.requires_approval or step.approved])
        self.progress_bar.setValue(completed)
    
    def on_step_approved(self, step_number: int):
        """Handle step approval"""
        print(f"Step {step_number} approved")
        self.progress_bar.setValue(step_number)
        
        # If final step is approved, emit network_processed signal
        if step_number == 6:
            self.network_processed.emit(self.network)
            self.proceed_to_strahler.emit() 
    
    def create_analysis_steps(self):
        """Create analysis steps for the network"""
        steps = []
        
        # Step 1: Component Identification
        components = []
        for comp_id, comp in self.network.components.items():
            components.append({
                'id': comp_id,
                'type': comp.component_type,
                'label': comp.label
            })
        steps.append(AnalysisStep(1, "Component Identification", components, True))
        
        # Step 2: Block Creation
        self.block_manager = self.network_analyzer.analyze_network(self.network)
        blocks = []
        for block_id, block in self.block_manager.blocks.items():
            blocks.append({
                'id': block_id,
                'type': block.block_type,
                'level': block.hierarchy_level,
                'components': list(block.components)
            })
        steps.append(AnalysisStep(2, "Block Structure Creation", blocks, True))
        
        # Step 3: Hierarchy Analysis
        hierarchy = self.block_manager.get_block_hierarchy()
        hierarchy_data = {}
        for level, block_ids in hierarchy.items():
            hierarchy_data[level] = [
                {
                    'id': block_id,
                    'type': self.block_manager.blocks[block_id].block_type,
                    'components': list(self.block_manager.blocks[block_id].components)
                }
                for block_id in block_ids
            ]
        steps.append(AnalysisStep(3, "Network Hierarchy Analysis", hierarchy_data, True))
        
        # Step 4: Relationship Analysis
        relationships = []
        for block_id, block in self.block_manager.blocks.items():
            if block.parent_block or block.child_blocks:
                relationships.append({
                    'id': block_id,
                    'type': block.block_type,
                    'level': block.hierarchy_level,
                    'parent': block.parent_block,
                    'children': list(block.child_blocks)
                })
        steps.append(AnalysisStep(4, "Block Relationships", relationships, True))
        
        # Step 5: Joint Analysis
        self.block_manager.detect_confluence_joints()
        joints = []
        for block in self.block_manager.blocks.values():
            for joint in block.joints.values():
                joints.append({
                    'id': joint.id,
                    'type': joint.joint_type,
                    'level': joint.hierarchy_level,
                    'upstream': joint.upstream_components,
                    'downstream': joint.downstream_components
                })
        steps.append(AnalysisStep(5, "Joint Analysis", joints, True))
        
        # Step 6: Final Structure
        final_structure = []
        for block_id, block in self.block_manager.blocks.items():
            final_structure.append({
                'id': block_id,
                'type': block.block_type,
                'level': block.hierarchy_level,
                'components': list(block.components),
                'joints': [
                    {
                        'id': j.id,
                        'type': j.joint_type,
                        'upstream': j.upstream_components,
                        'downstream': j.downstream_components
                    }
                    for j in block.joints.values()
                ]
            })
        steps.append(AnalysisStep(6, "Final Network Structure", final_structure, False))
        
        return steps