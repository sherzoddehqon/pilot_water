from typing import Dict, List, Set, Tuple, Optional
from models.components import NetworkComponent
from core.strahler import StrahlerAnalyzer

class IrrigationNetwork:
    """Main class for managing irrigation network structure"""
    def __init__(self):
        self.components: Dict[str, NetworkComponent] = {}
        self._strahler_analyzer = StrahlerAnalyzer()

    def add_component(self, id: str, label: str) -> NetworkComponent:
        """Add a new component to the network"""
        print(f"Adding component: {id} ({label})")  # Debug print
        component = NetworkComponent(id=id, label=label)
        self.components[id] = component
        return component

    def add_connection(self, source_id: str, target_id: str):
        """Add a connection between components"""
        print(f"Adding connection: {source_id} -> {target_id}")  # Debug print
        if source_id in self.components and target_id in self.components:
            self.components[source_id].add_connection_to(target_id)
            self.components[target_id].add_connection_from(source_id)
            print(f"Connection added between {source_id} and {target_id}")  # Debug print

    def calculate_hierarchy_levels(self):
        """Calculate hierarchy levels using Strahler numbers"""
        print("\nCalculating hierarchy levels...")  # Debug print
        
        # Calculate Strahler numbers and use them as levels
        strahler_numbers = self._strahler_analyzer.analyze_network(self.components)
        
        # Update component levels based on Strahler numbers
        for comp_id, strahler in strahler_numbers.items():
            print(f"Setting {comp_id} to level {strahler}")  # Debug print
            self.components[comp_id].set_level(strahler)

        # Print final hierarchy
        print("\nFinal hierarchy:")
        for comp_id, comp in self.components.items():
            print(f"{comp_id}: Level {comp.level}")

    def get_components_by_level(self) -> Dict[int, List[str]]:
        """Get components organized by hierarchy level"""
        return self._strahler_analyzer.get_level_components(self.components)

    def get_component_children(self, component_id: str) -> List[str]:
        """Get all immediate children of a component"""
        if component_id in self.components:
            return self.components[component_id].connections_to
        return []

    def get_component_parents(self, component_id: str) -> List[str]:
        """Get all immediate parents of a component"""
        if component_id in self.components:
            return self.components[component_id].connections_from
        return []

    def get_all_paths(self, start_id: str, end_id: str = None) -> List[List[str]]:
        """Get all possible paths from start to end (or all paths from start if end is None)"""
        paths = []
        visited = set()

        def dfs(current: str, path: List[str]):
            if current in visited:
                return
            visited.add(current)
            path.append(current)
            
            if end_id is None and not self.components[current].connections_to:
                # End reached (leaf node)
                paths.append(path.copy())
            elif current == end_id:
                # End reached (specific target)
                paths.append(path.copy())
            else:
                for next_id in self.components[current].connections_to:
                    dfs(next_id, path.copy())
            
            visited.remove(current)

        if start_id in self.components:
            dfs(start_id, [])
        
        return paths

    def validate_network(self) -> Tuple[bool, List[str]]:
        """Validate the network structure"""
        errors = []
        
        # Check for disconnected components
        for comp_id, component in self.components.items():
            if not component.connections_to and not component.connections_from:
                errors.append(f"Component {comp_id} is disconnected from the network")
        
        # Validate distribution points (without root assumptions)
        for comp_id, component in self.components.items():
            if comp_id.startswith('DP'):
                # Check if this DP is not a source node
                if not component.connections_from and component.connections_to:
                    errors.append(f"Distribution point {comp_id} has no input connection")

        return len(errors) == 0, errors
        
    def get_strahler_order(self) -> Dict[str, int]:
        """Calculate Strahler numbers for each component"""
        return self._strahler_analyzer.analyze_network(self.components)

    def get_source_nodes(self) -> List[str]:
        """Get all source nodes (nodes with no incoming connections)"""
        return [comp_id for comp_id, comp in self.components.items() 
                if not comp.connections_from]
                
    def get_sink_nodes(self) -> List[str]:
        """Get all sink nodes (nodes with no outgoing connections)"""
        return [comp_id for comp_id, comp in self.components.items() 
                if not comp.connections_to]

    def get_max_level(self) -> int:
        """Get the maximum hierarchy level in the network"""
        return self._strahler_analyzer.get_max_level()