from typing import List, Dict, Set, Optional
import re
from core.network import IrrigationNetwork
from models.components import NetworkComponent


class AnalysisStep:
    """Represents a single step in the network analysis process"""
    
    def __init__(self, step_number: int, description: str, components: List, requires_approval: bool = False):
        self.step_number = step_number
        self.description = description
        self.components = components
        self.requires_approval = requires_approval
        self.approved = False


class NetworkAnalyzer:
    """Analyzes irrigation network structure and relationships"""
    
    def __init__(self):
        self.network: Optional[IrrigationNetwork] = None
        self.strahler_numbers: Dict[str, int] = {}
        self.analysis_steps: List[AnalysisStep] = []
    
    def analyze_network(self, network: IrrigationNetwork) -> List[AnalysisStep]:
        """Perform complete network analysis"""
        print("Starting network analysis...")
        self.network = network
        self.analysis_steps = []
        
        # Step 1: Component type analysis
        type_stats = self._analyze_component_types()
        self.analysis_steps.append(AnalysisStep(1, "Component Type Analysis", type_stats))
        print("Step 1 completed:", type_stats)
        
        # Step 2: Connection analysis
        connection_count = self._analyze_connections()
        self.analysis_steps.append(AnalysisStep(2, "Connection Analysis", [f"Found {connection_count} connections"]))
        print("Step 2 completed:", f"Found {connection_count} connections")
        
        # Step 3: Calculate Strahler numbers
        self.strahler_numbers = self._calculate_strahler_numbers()
        strahler_results = [f"{comp_id}: {order}" for comp_id, order in self.strahler_numbers.items()]
        self.analysis_steps.append(AnalysisStep(3, "Network Hierarchy Analysis", strahler_results))
        print("Step 3 completed: Strahler numbers calculated")
        print("Strahler numbers calculated:", self.strahler_numbers)
        
        # Step 4: Find top level path
        top_path = self._find_top_level_path()
        self.analysis_steps.append(AnalysisStep(
            4,
            "Top Level Path Identification",
            [" -> ".join(top_path)],
            requires_approval=True
        ))
        print("Step 4 completed:", f"Found top level path: {' -> '.join(top_path)}")
        
        # Step 5: Initialize path analysis (updated after Step 4 approval)
        self.analysis_steps.append(AnalysisStep(
            5,
            "Path Analysis",
            ["Waiting for Step 4 approval..."],
            requires_approval=True
        ))
        print("Step 5 skipped: Top level not yet approved")
        
        return self.analysis_steps

    def _preprocess_fields(self) -> Dict[str, Dict]:
        """Read the fields from Fields and Canals table"""
        fields = {}
        for comp_id, component in self.network.components.items():
            # Use regex to match field IDs like F1_1, F2_2, etc.
            if re.match(r'F\d+_\d+$', comp_id):
                fields[comp_id] = {
                    'id': comp_id,
                    'type': 'field',
                    'label': comp_id,
                    'component': component
                }
                print(f"DEBUG: Found field {comp_id}")
        return fields

    def _analyze_component_types(self) -> List[Dict]:
        """Analyze and get detailed component type information"""
        components_by_type = {}
        
        # Pre-define order and display names
        type_order = [
            ('distribution_point', 'Distribution Points'),
            ('canal', 'Canal'),
            ('gate', 'Gate'),
            ('smart_water', 'Smart Water'),
            ('field', 'Field')
        ]
        
        # First get all fields
        fields = self._preprocess_fields()
        print(f"\nDEBUG: Total fields found: {len(fields)}")
        components_by_type['field'] = []
        
        # Process each component
        for comp_id, component in self.network.components.items():
            # If it's a field, handle it specially
            if comp_id in fields:
                if 'field' not in components_by_type:
                    components_by_type['field'] = []
                components_by_type['field'].append({
                    'id': comp_id,
                    'type': 'field',
                    'label': comp_id
                })
                continue
                
            # Handle non-field components
            comp_type = component.component_type
            if comp_type not in components_by_type:
                components_by_type[comp_type] = []
                
            components_by_type[comp_type].append({
                'id': comp_id,
                'type': comp_type,
                'label': component.label
            })
        
        # Debug output
        print("\nDEBUG: Component counts:")
        for comp_type, components in components_by_type.items():
            print(f"{comp_type}: {len(components)} components")
            if comp_type == 'field':
                print("Field IDs:", sorted([comp['id'] for comp in components]))
        
        # Build results in the correct order
        result = []
        for comp_type, display_name in type_order:
            if comp_type in components_by_type:
                components = sorted(components_by_type[comp_type], key=lambda x: x['id'])
                result.extend(components)
        
        return result

    def _analyze_connections(self) -> int:
        """Count and validate network connections"""
        connection_count = 0
        for component in self.network.components.values():
            connection_count += len(component.connections_to)
        return connection_count
    
    def _calculate_strahler_numbers(self) -> Dict[str, int]:
        """Calculate Strahler numbers for network components"""
        strahler_numbers: Dict[str, int] = {}
        
        def calculate_strahler(node_id: str) -> int:
            if node_id in strahler_numbers:
                return strahler_numbers[node_id]
            
            component = self.network.components[node_id]
            
            if not component.connections_to:
                strahler_numbers[node_id] = 1
                print(f"Leaf node {node_id} assigned order 1")
                return 1
            
            child_numbers = [calculate_strahler(child) for child in component.connections_to]
            
            max_child = max(child_numbers)
            if child_numbers.count(max_child) > 1:
                strahler_numbers[node_id] = max_child + 1
                print(f"Node {node_id} has {child_numbers.count(max_child)} children of order {max_child}, assigned order {max_child + 1}")
            else:
                strahler_numbers[node_id] = max_child
                print(f"Node {node_id} has highest child order {max_child}, keeping same order")
            
            return strahler_numbers[node_id]
        
        for comp_id in self.network.components:
            if comp_id not in strahler_numbers:
                calculate_strahler(comp_id)
        
        return strahler_numbers
    
    def _find_top_level_path(self) -> List[str]:
        """Find the main path from root to first major distribution point"""
        if not self.network or not self.network.root_id:
            return []
        
        path = [self.network.root_id]
        current = self.network.root_id
        
        while True:
            component = self.network.components[current]
            next_components = [
                next_id for next_id in component.connections_to
                if next_id in self.strahler_numbers
            ]
            
            if not next_components:
                break
                
            next_id = max(next_components, key=lambda x: self.strahler_numbers[x])
            path.append(next_id)
            current = next_id
            
            if len(component.connections_to) > 1:
                break
        
        return path
    
    def _analyze_paths(self) -> None:
        """Analyze paths from top level through the network hierarchy"""
        if not any(step.step_number == 4 and step.approved for step in self.analysis_steps):
            print("Step 5 skipped: Top level not yet approved")
            return
        
        # Get the approved top-level path
        top_level_step = next((step for step in self.analysis_steps 
                             if step.step_number == 4 and step.approved), None)
        if not top_level_step or not top_level_step.components:
            return
        
        # Extract the root path components
        root_path = top_level_step.components[0].split(" -> ")
        root_id = root_path[0]  # Should be DP0
        print(f"Starting path analysis from: {' -> '.join(root_path)}")
        
        all_paths = []
        visited = set()
        
        def find_paths(start_id: str, current_path: List[str]):
            """Recursively find all paths from the given start point"""
            if start_id in visited:
                return
                
            visited.add(start_id)
            current_path.append(start_id)
            
            component = self.network.components[start_id]
            if not component.connections_to:  # End point reached
                all_paths.append(current_path.copy())
            else:
                for next_id in component.connections_to:
                    if next_id not in visited:
                        find_paths(next_id, current_path.copy())
            
            visited.remove(start_id)
        
        # Find all paths starting from root
        print(f"Finding paths from root: {root_id}")
        find_paths(root_id, [])
        
        # Sort paths by length and format for display
        sorted_paths = sorted(all_paths, key=len)
        formatted_paths = []
        
        # Add main paths section
        formatted_paths.append("=== Main Paths from Top Level ===")
        
        # Add paths that extend beyond the top level
        for path in sorted_paths:
            if len(path) > len(root_path):  # Only show paths longer than root path
                formatted_paths.append(" → ".join(path))
        
        # Update Step 5
        step5_index = next(i for i, step in enumerate(self.analysis_steps) 
                         if step.step_number == 5)
        
        self.analysis_steps[step5_index] = AnalysisStep(
            step_number=5,
            description="Complete Network Path Analysis",
            components=formatted_paths,
            requires_approval=True
        )
        
        print(f"Step 5 completed: Found {len(formatted_paths) - 1} paths")