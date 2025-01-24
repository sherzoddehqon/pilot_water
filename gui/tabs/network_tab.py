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
    approved = pyqtSignal(int)  # Signal emitted when step is approved
    
    def __init__(self, step: AnalysisStep, parent=None):
        super().__init__(parent)
        self.step = step
        print(f"\nInitializing Step {step.step_number} widget")  # Debug print
        self.initUI()
        
    def initUI(self):
        self.setTitle(f"Step {self.step.step_number}: {self.step.description}")
        layout = QVBoxLayout(self)
        
        # For steps 2 and 3, show simplified view
        if self.step.step_number in [2, 3]:
            result_label = QLabel()
            if self.step.step_number == 2:
                result_label.setText(f"Found {len(self.step.components)} connections")
            else:  # Step 3
                result_label.setText("Strahler numbers calculated")
            layout.addWidget(result_label)
        else:
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
            
            # Update button state
            self.approve_btn.setEnabled(not self.step.approved)
            if self.step.approved:
                self.approve_btn.setText("Approved ✓")
    
    def populate_tree(self):
        """Populate tree with step components"""
        self.tree.clear()
        
        try:
            if self.step.step_number == 1:
                # Group components by type
                components_by_type = {}
                for comp in self.step.components:
                    comp_type = comp.get('type', 'unknown')
                    if comp_type not in components_by_type:
                        components_by_type[comp_type] = []
                    components_by_type[comp_type].append(comp)
                
                # Add components grouped by type
                for comp_type, components in sorted(components_by_type.items()):
                    type_item = QTreeWidgetItem(self.tree)
                    type_item.setText(0, f"{comp_type.replace('_', ' ').title()} ({len(components)})")
                    type_item.setExpanded(True)
                    
                    for comp in sorted(components, key=lambda x: x['id']):
                        comp_item = QTreeWidgetItem(type_item)
                        comp_item.setText(0, comp['id'])
                        comp_item.setText(1, comp['type'])
                        comp_item.setText(2, comp.get('label', ''))
            
            elif self.step.step_number == 4:  # Strahler analysis
                self._populate_strahler_results()
                
            else:
                self._populate_regular_components()
                
        except Exception as e:
            error_item = QTreeWidgetItem(self.tree)
            error_item.setText(0, "Error displaying components")
            error_item.setText(1, str(e))
            print(f"Error in populate_tree: {str(e)}")  # Debug print
    
    def _populate_strahler_results(self):
        """Populate Strahler analysis results"""
        # Group by Strahler number
        by_level = {}
        for comp_id, level in self.step.components.items():
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(comp_id)
        
        # Add to tree
        for level in sorted(by_level.keys()):
            level_item = QTreeWidgetItem(self.tree)
            level_item.setText(0, f"Level {level}")
            level_item.setText(1, f"{len(by_level[level])} components")
            level_item.setExpanded(True)
            
            for comp_id in sorted(by_level[level]):
                comp_item = QTreeWidgetItem(level_item)
                comp_item.setText(0, comp_id)
                comp_item.setText(1, "Component")
                comp_item.setText(2, f"Strahler: {level}")
    
    def _populate_regular_components(self):
        """Handle regular components"""
        for component in self.step.components:
            item = QTreeWidgetItem(self.tree)
            if isinstance(component, str):
                item.setText(0, str(component))
            elif isinstance(component, dict):
                for key, value in component.items():
                    child = QTreeWidgetItem(item)
                    child.setText(0, str(key))
                    child.setText(1, str(value))
            else:
                item.setText(0, str(component))
    
    def on_approve(self):
        """Handle step approval"""
        self.step.approved = True
        self.approve_btn.setText("Approved ✓")
        self.approve_btn.setEnabled(False)
        self.approved.emit(self.step.step_number)

class NetworkAnalysisTab(QWidget):  # Changed class name from NetworkTab to NetworkAnalysisTab
    """Main network analysis tab"""
    network_processed = pyqtSignal(IrrigationNetwork)
    proceed_to_strahler = pyqtSignal()  # Signal for tab switching
    
    def __init__(self):
        super().__init__()
        self.network = None
        self.strahler_analyzer = StrahlerAnalyzer()
        self.analysis_steps: List[AnalysisStep] = []
        self.step_widgets: Dict[int, AnalysisStepWidget] = {}
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # File Upload Section
        upload_frame = QFrame()
        upload_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        upload_layout = QHBoxLayout(upload_frame)
        
        self.upload_btn = QPushButton("Upload Network File")
        self.upload_btn.clicked.connect(self.upload_file)
        upload_layout.addWidget(self.upload_btn)
        
        self.file_label = QLabel("No file selected")
        upload_layout.addWidget(self.file_label)
        
        main_layout.addWidget(upload_frame)
        
        # Progress Section
        progress_frame = QFrame()
        progress_layout = QHBoxLayout(progress_frame)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximum(3)  # Number of analysis steps
        progress_layout.addWidget(QLabel("Analysis Progress:"))
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_frame)
        
        # Analysis Steps Section
        steps_scroll = QScrollArea()
        steps_scroll.setWidgetResizable(True)
        steps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.addStretch()
        steps_scroll.setWidget(self.steps_container)
        
        main_layout.addWidget(steps_scroll)
        
        # Initial state
        self.progress_bar.setValue(0)
    
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
                self.clear_analysis()
                
                with open(file_name, 'r') as file:
                    content = file.read()
                self.file_label.setText(f"Loaded: {file_name}")
                
                # Parse network
                parser = MermaidParser()
                self.network = parser.parse(content)
                
                # Start analysis
                self.start_analysis()
                
            except Exception as e:
                self.file_label.setText(f"Error loading file: {str(e)}")
                print(f"Error details: {str(e)}")
    
    def clear_analysis(self):
        """Clear previous analysis results"""
        self.network = None
        self.analysis_steps = []
        self.step_widgets.clear()
        
        while self.steps_layout.count():
            child = self.steps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.steps_layout.addStretch()
        self.progress_bar.setValue(0)
    
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
        
        # Step 2: Connection Analysis
        connections = []
        for comp_id, comp in self.network.components.items():
            for target_id in comp.connections_to:
                connections.append((comp_id, target_id))
        steps.append(AnalysisStep(2, "Connection Analysis", connections, True))
        
        # Step 3: Strahler Analysis
        strahler_numbers = self.strahler_analyzer.analyze_network(self.network.components)
        steps.append(AnalysisStep(3, "Strahler Analysis", strahler_numbers, True))
        
        return steps
    
    def start_analysis(self):
        """Start the network analysis process"""
        if not self.network:
            return
        
        # Create analysis steps
        self.analysis_steps = self.create_analysis_steps()
        
        # Remove stretch
        if self.steps_layout.count() > 0:
            self.steps_layout.takeAt(self.steps_layout.count() - 1)
        
        # Create step widgets
        for step in self.analysis_steps:
            step_widget = AnalysisStepWidget(step)
            if step.requires_approval:
                step_widget.approved.connect(self.on_step_approved)
            self.steps_layout.addWidget(step_widget)
            self.step_widgets[step.step_number] = step_widget
        
        # Add stretch back
        self.steps_layout.addStretch()
        
        # Update progress
        self.update_progress()
    
    def on_step_approved(self, step_number: int):
        """Handle step approval"""
        print(f"Step {step_number} approved")
        self.progress_bar.setValue(step_number)
        self.update_progress()
        
        # Emit signal when network is fully processed
        if step_number == 3:
            self.network_processed.emit(self.network)
            self.proceed_to_strahler.emit()
    
    def update_progress(self):
        """Update progress bar based on completed steps"""
        completed = len([step for step in self.analysis_steps 
                        if not step.requires_approval or step.approved])
        self.progress_bar.setValue(completed)