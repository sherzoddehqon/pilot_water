from typing import List, Tuple, Dict, Set
from core.network import IrrigationNetwork
from core.strahler import StrahlerAnalyzer

class NetworkValidator:
    """Validator for irrigation network structures"""
    
    def __init__(self, network: IrrigationNetwork):
        self.network = network
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.strahler_analyzer = StrahlerAnalyzer()
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Perform full network validation
        
        Returns:
            Tuple containing:
            - Boolean indicating if network is valid
            - List of error messages
            - List of warning messages
        """
        self.errors = []
        self.warnings = []
        
        # Run all validation checks
        self._validate_topology()
        self._validate_strahler_ordering()
        self._validate_component_connections()
        self._validate_component_types()
        self._validate_field_paths()
        self._validate_irrigation_rules()
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_topology(self):
        """Validate basic network topology"""
        # Check for disconnected components
        for comp_id, comp in self.network.components.items():
            if not comp.connections_from and not comp.connections_to:
                self.errors.append(f"Component {comp_id} is disconnected")
        
        # Must have at least one source and one sink
        sources = [comp_id for comp_id, comp in self.network.components.items() 
                  if not comp.connections_from]
        sinks = [comp_id for comp_id, comp in self.network.components.items() 
                if not comp.connections_to]
        
        if not sources:
            self.errors.append("Network has no source nodes")
        if not sinks:
            self.errors.append("Network has no sink nodes")
        
        # Check for cycles
        self._check_for_cycles()
    
    def _validate_strahler_ordering(self):
        """Validate Strahler number assignments and hierarchy"""
        # Calculate Strahler numbers
        strahler_numbers = self.strahler_analyzer.analyze_network(self.network.components)
        
        # Validate component levels match Strahler numbers
        for comp_id, comp in self.network.components.items():
            strahler = strahler_numbers.get(comp_id, -1)
            if comp.level != strahler:
                self.errors.append(
                    f"Component {comp_id} level ({comp.level}) does not match "
                    f"its Strahler number ({strahler})")
        
        # Validate level relationships
        for comp_id, comp in self.network.components.items():
            for child_id in comp.connections_to:
                child = self.network.components[child_id]
                if child.level <= comp.level and child_id != comp_id:
                    self.errors.append(
                        f"Invalid hierarchy: {comp_id} (level {comp.level}) connects to "
                        f"{child_id} (level {child.level})")
    
    def _validate_component_connections(self):
        """Validate connections between components"""
        # Define valid connection patterns
        valid_connections = {
            'canal': {'distribution_point', 'smart_water', 'gate'},
            'distribution_point': {'canal', 'smart_water', 'gate', 'field'},
            'smart_water': {'field'},
            'gate': {'field'},
            'field': set()  # Fields should not have outgoing connections
        }
        
        for comp_id, comp in self.network.components.items():
            comp_type = comp.component_type
            
            # Validate outgoing connections
            if comp_type in valid_connections:
                allowed_targets = valid_connections[comp_type]
                for target_id in comp.connections_to:
                    target_type = self.network.components[target_id].component_type
                    if target_type not in allowed_targets:
                        self.errors.append(
                            f"Invalid connection: {comp_id} ({comp_type}) to "
                            f"{target_id} ({target_type})")
            
            # Component-specific validations
            self._validate_component_specific_rules(comp_id, comp)
    
    def _validate_component_specific_rules(self, comp_id: str, comp):
        """Validate rules specific to each component type"""
        if comp.component_type == 'smart_water':
            # Smart water meters should have exactly one input and one output
            if len(comp.connections_from) != 1:
                self.errors.append(
                    f"Smart water meter {comp_id} should have exactly one input")
            if len(comp.connections_to) != 1:
                self.errors.append(
                    f"Smart water meter {comp_id} should have exactly one output")
                
        elif comp.component_type == 'gate':
            # Gates should have exactly one input
            if len(comp.connections_from) != 1:
                self.errors.append(f"Gate {comp_id} should have exactly one input")
                
        elif comp.component_type == 'field':
            # Fields should have exactly one input and no outputs
            if len(comp.connections_from) != 1:
                self.errors.append(f"Field {comp_id} should have exactly one input")
            if comp.connections_to:
                self.errors.append(f"Field {comp_id} should not have any outputs")
    
    def _validate_component_types(self):
        """Validate component type assignments"""
        valid_prefixes = {
            'MC': 'canal',
            'DP': 'distribution_point',
            'SW': 'smart_water',
            'ZT': 'gate',
            'F': 'field'
        }
        
        for comp_id, comp in self.network.components.items():
            prefix = ''.join(c for c in comp_id if c.isalpha())
            if prefix in valid_prefixes:
                expected_type = valid_prefixes[prefix]
                if comp.component_type != expected_type:
                    self.errors.append(
                        f"Component {comp_id} has incorrect type {comp.component_type}, "
                        f"expected {expected_type}")
    
    def _validate_field_paths(self):
        """Validate paths to fields"""
        fields = [comp_id for comp_id in self.network.components 
                 if comp_id.startswith('F')]
                 
        for field_id in fields:
            # Find paths from all sources to this field
            sources = [comp_id for comp_id, comp in self.network.components.items() 
                      if not comp.connections_from]
            
            valid_path_found = False
            for source_id in sources:
                paths = self.network.get_all_paths(source_id, field_id)
                if any(self._is_valid_field_path(path) for path in paths):
                    valid_path_found = True
                    break
            
            if not valid_path_found:
                self.errors.append(f"No valid irrigation path to field {field_id}")
    
    def _validate_irrigation_rules(self):
        """Validate irrigation-specific business rules"""
        # Fields should have control points in their paths
        fields = [comp_id for comp_id in self.network.components 
                 if comp_id.startswith('F')]
                 
        for field_id in fields:
            if not self._has_control_point_in_path(field_id):
                self.warnings.append(
                    f"Field {field_id} has no control point (smart water or gate) "
                    "in its irrigation path")
    
    def _check_for_cycles(self):
        """Check for cycles in the network"""
        visited = set()
        path = set()
        
        def detect_cycle(node_id: str) -> bool:
            if node_id in path:
                self.errors.append(f"Cycle detected involving component {node_id}")
                return True
                
            if node_id in visited:
                return False
                
            visited.add(node_id)
            path.add(node_id)
            
            component = self.network.components[node_id]
            for next_id in component.connections_to:
                if detect_cycle(next_id):
                    return True
                    
            path.remove(node_id)
            return False
        
        # Start from source nodes
        sources = [comp_id for comp_id, comp in self.network.components.items() 
                  if not comp.connections_from]
                  
        for source_id in sources:
            detect_cycle(source_id)
    
    def _is_valid_field_path(self, path: List[str]) -> bool:
        """Check if a path to a field contains necessary components"""
        if not path:
            return False
            
        # Must end with a field
        if not path[-1].startswith('F'):
            return False
            
        # Must have at least one control point
        has_control = any(
            self.network.components[node_id].component_type in ['smart_water', 'gate']
            for node_id in path
        )
        
        return has_control
    
    def _has_control_point_in_path(self, field_id: str) -> bool:
        """Check if any path to a field contains a control point"""
        # Get all paths to the field
        sources = [comp_id for comp_id, comp in self.network.components.items() 
                  if not comp.connections_from]
                  
        for source_id in sources:
            paths = self.network.get_all_paths(source_id, field_id)
            if any(self._is_valid_field_path(path) for path in paths):
                return True
                
        return False