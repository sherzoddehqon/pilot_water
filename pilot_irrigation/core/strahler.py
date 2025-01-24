from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog,
                            QTreeWidget, QTreeWidgetItem, QFrame)
from PyQt6.QtCore import Qt
from parsers.mermaid_parser import NetworkParser
from core.strahler import StrahlerAnalyzer
import json
from PyQt6.QtWebEngineWidgets import QWebEngineView

class StrahlerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.parser = NetworkParser()
        self.network = None
        self.analyzer = StrahlerAnalyzer()
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.addWidget(self._create_left_panel())
        layout.addWidget(self._create_right_panel())
        
    def _create_left_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        layout = QVBoxLayout(panel)
        
        self.upload_btn = QPushButton("Upload Network File")
        self.upload_btn.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_btn)
        
        self.file_label = QLabel("No file selected")
        layout.addWidget(self.file_label)
        
        self.network_tree = QTreeWidget()
        self.network_tree.setHeaderLabels(["Component", "Strahler Number"])
        layout.addWidget(self.network_tree)
        
        return panel
        
    def _create_right_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        layout = QVBoxLayout(panel)
        
        self.viz_container = QWidget()
        self._setup_visualization()
        layout.addWidget(self.viz_container)

        export_btn = QPushButton("Export Analysis")
        export_btn.clicked.connect(self.export_analysis)
        layout.addWidget(export_btn)
        
        return panel

    def export_analysis(self):
        if not self.network:
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Analysis", "", "JSON Files (*.json)"
        )
    
        if file_name:
            analysis_data = {
                'levels': self.analyzer.get_level_components(self.network.components),
                'sources': list(self.analyzer.source_nodes),
                'sinks': list(self.analyzer.sink_nodes),
                'paths': self.analyzer.find_critical_paths(self.network.components),
                'metrics': {
                    'totalComponents': len(self.network.components),
                    'maxStrahler': self.analyzer.get_max_level(),
                    'edgeCount': sum(len(comp.connections_to) for comp in self.network.components.values()),
                    'sourceCount': len(self.analyzer.source_nodes),
                    'sinkCount': len(self.analyzer.sink_nodes)
                }
            }
        
            with open(file_name, 'w') as f:
                json.dump(analysis_data, f, indent=2)

    def _setup_visualization(self):
        viz_layout = QVBoxLayout(self.viz_container)
        web_view = QWebEngineView()
        viz_layout.addWidget(web_view)
        self.web_view = web_view
        
    def update_network_tree(self):
        self.network_tree.clear()
        if not self.network:
            return
            
        levels = self.analyzer.get_level_components(self.network.components)
        edge_count = sum(len(comp.connections_to) for comp in self.network.components.values())
        n = len(self.network.components)
        density = edge_count / (n * (n-1)) if n > 1 else 0
        
        metrics = {
            'totalComponents': n,
            'edgeCount': edge_count,
            'density': density,
            'maxStrahler': self.analyzer.get_max_level(),
            'sourceCount': len(self.analyzer.source_nodes),
            'sinkCount': len(self.analyzer.sink_nodes),
            'typeDistribution': self.analyzer.analyze_component_types(self.network.components)
        }

        viz_data = {
            'strahlerData': levels,
            'sourceNodes': list(self.analyzer.source_nodes),
            'sinkNodes': list(self.analyzer.sink_nodes),
            'metrics': metrics,
            'paths': self.analyzer.find_critical_paths(self.network.components)
        }
    
        self._update_tree_view(levels)
        self.web_view.page().runJavaScript(
        f"window.updateVisualization({json.dumps(viz_data)})"
        )

    def _update_tree_view(self, levels):
        for level, components in sorted(levels.items()):
            level_item = QTreeWidgetItem(self.network_tree)
            level_item.setText(0, f"Level {level}")
            level_item.setText(1, str(level))
        
            for comp_id in sorted(components):
                comp_item = QTreeWidgetItem(level_item)
                comp_item.setText(0, comp_id)
                comp_item.setText(1, str(level))

        if self.network:
           viz_data = {
                'strahlerData': levels,
                'sourceNodes': list(self.analyzer.source_nodes),
                'sinkNodes': list(self.analyzer.sink_nodes)
            }
           self.web_view.page().runJavaScript(
                f"window.updateVisualization({json.dumps(viz_data)})"
            )

    def upload_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Network File", "", "Mermaid Files (*.mermaid);;All Files (*)")
        
        if file_name:
            try:
                with open(file_name, 'r') as file:
                    content = file.read()
                self.file_label.setText(f"Loaded: {file_name}")
                
                self.network = self.parser.parse_mermaid(content)
                self.analyzer.analyze_network(self.network.components)
                self.update_network_tree()
                
            except Exception as e:
                self.file_label.setText(f"Error loading file: {str(e)}")
                

    def calculate_strahler_numbers(network):
        """Calculate Strahler numbers for network components"""
        strahler_numbers = {}
    
        def calculate_node(node_id):
            if node_id in strahler_numbers:
                return strahler_numbers[node_id]
            
            component = network.components[node_id]
        
           # Leaf nodes have Strahler number 1
            if not component.connections_to:
                strahler_numbers[node_id] = 1
                return 1
            
            # Calculate Strahler numbers of children
            child_numbers = [calculate_node(child) for child in component.connections_to]

            if not child_numbers:
                strahler_numbers[node_id] = 1
            elif len(child_numbers) == 1:
                strahler_numbers[node_id] = child_numbers[0]
            else:
                max_number = max(child_numbers)
                if child_numbers.count(max_number) > 1:
                    strahler_numbers[node_id] = max_number + 1
                else:
                    strahler_numbers[node_id] = max_number

            return strahler_numbers[node_id]
    
        # Calculate for all root nodes
        root_nodes = [comp_id for comp_id, comp in network.components.items() 
                     if not comp.connections_from]
                 
        for root in root_nodes:
            calculate_node(root)
        
        return strahler_numbers

class StrahlerAnalyzer:
    """
    Implements Strahler number calculation for irrigation networks.
    Strahler numbers are calculated based on network topology without assumptions
    about specific component types or predefined hierarchies.
    """
    
    def __init__(self):
        self.strahler_numbers: Dict[str, int] = {}
        self.source_nodes: Set[str] = set()
        self.sink_nodes: Set[str] = set()
        
    def analyze_network(self, components: Dict[str, NetworkComponent]) -> Dict[str, int]:
        """
        Calculate Strahler numbers for all components in the network.
        
        Args:
            components: Dictionary mapping component IDs to NetworkComponent objects
            
        Returns:
            Dictionary mapping component IDs to their Strahler numbers
        """
        self.strahler_numbers.clear()
        self._identify_sources_and_sinks(components)
        
        # Calculate Strahler numbers starting from each source
        for source_id in self.source_nodes:
            self._calculate_strahler(source_id, components, set())
            
        return self.strahler_numbers
        
    def _identify_sources_and_sinks(self, components: Dict[str, NetworkComponent]):
        """
        Identify source nodes (no incoming connections) and sink nodes (no outgoing connections).
        Updates source_nodes and sink_nodes sets.
        """
        self.source_nodes.clear()
        self.sink_nodes.clear()
        
        for comp_id, component in components.items():
            if not component.connections_from:
                self.source_nodes.add(comp_id)
            if not component.connections_to:
                self.sink_nodes.add(comp_id)
    
    def _calculate_strahler(self, node_id: str, components: Dict[str, NetworkComponent], 
                          visited: Set[str]) -> int:
        """
        Calculate Strahler number for a single node using DFS.
        
        Args:
            node_id: ID of current node
            components: Network components dictionary
            visited: Set of visited node IDs to prevent cycles
            
        Returns:
            Strahler number for the current node
        """
        # Return memoized result if available
        if node_id in self.strahler_numbers:
            return self.strahler_numbers[node_id]
            
        # Detect cycles
        if node_id in visited:
            return 0
            
        visited.add(node_id)
        component = components[node_id]
        
        # Base case: sink nodes (no outgoing edges) have Strahler number 1
        if not component.connections_to:
            self.strahler_numbers[node_id] = 1
            visited.remove(node_id)
            return 1
            
        # Calculate Strahler numbers of all children
        child_numbers = []
        for child_id in component.connections_to:
            child_number = self._calculate_strahler(child_id, components, visited)
            child_numbers.append(child_number)
            
        # Calculate Strahler number based on children
        strahler = self._compute_strahler_from_children(child_numbers)
        self.strahler_numbers[node_id] = strahler
        
        visited.remove(node_id)
        return strahler
    
    def _compute_strahler_from_children(self, child_numbers: List[int]) -> int:
        """
        Compute Strahler number based on child Strahler numbers.
        
        Args:
            child_numbers: List of child Strahler numbers
            
        Returns:
            Strahler number computed from children
        """
        if not child_numbers:
            return 1
        
        # Sort in descending order for efficient max finding
        sorted_numbers = sorted(child_numbers, reverse=True)
        max_number = sorted_numbers[0]
        
        # If multiple children have the max Strahler number, increment by 1
        if len(sorted_numbers) > 1 and sorted_numbers[1] == max_number:
            return max_number + 1
            
        # Otherwise, use the maximum number
        return max_number
        
    def get_level_components(self, components: Dict[str, NetworkComponent]) -> Dict[int, List[str]]:
        """
        Group components by their Strahler numbers.
        
        Args:
            components: Network components dictionary
            
        Returns:
            Dictionary mapping Strahler numbers to lists of component IDs
        """
        levels: Dict[int, List[str]] = {}
        
        for comp_id, strahler in self.strahler_numbers.items():
            if strahler not in levels:
                levels[strahler] = []
            levels[strahler].append(comp_id)
            
        return levels

    def find_critical_paths(self, components):
        paths = []
        for source in self.source_nodes:
            for sink in self.sink_nodes:
                path = self._find_path(source, sink, components)
                if path:
                    paths.append(path)
        return paths

    def _find_path(self, start, end, components, visited=None):
        if visited is None:
            visited = set()
        if start == end:
            return [start]
        if start in visited:
            return None
            
        visited.add(start)
        for next_id in components[start].connections_to:
            if next_id not in visited:
                path = self._find_path(next_id, end, components, visited)
                if path:
                    return [start] + path
        visited.remove(start)
        return None

    def get_max_level(self) -> int:
        return max(self.strahler_numbers.values()) if self.strahler_numbers else 0
    
    def analyze_component_types(self, components):
        type_counts = {}
        for comp in components.values():
            comp_type = comp.component_type
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        return type_counts