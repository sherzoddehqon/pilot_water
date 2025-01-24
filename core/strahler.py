# core/strahler.py
from typing import Dict, Set, List
from models.components import NetworkComponent

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
        
    def get_max_level(self) -> int:
        """
        Get the maximum Strahler number in the network.
        
        Returns:
            Maximum Strahler number, or 0 if network is empty
        """
        return max(self.strahler_numbers.values()) if self.strahler_numbers else 0