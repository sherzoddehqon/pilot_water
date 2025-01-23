from typing import Dict, List, Set, Tuple, Optional
import re
from core.components import NetworkComponent
from core.network import IrrigationNetwork

class MermaidParser:
    """Parser for Mermaid diagram files that represent irrigation networks"""
    
    def __init__(self):
        """Initialize parser with component type mappings"""
        self.component_types = {
            'DP': 'distribution_point',
            'MC': 'canal',
            'ZT': 'gate',
            'SW': 'smart_water',
            'F': 'field'
        }

    def parse(self, content: str) -> IrrigationNetwork:
        """Parse Mermaid content into network structure"""
        network = IrrigationNetwork()
        print("\nParsing Mermaid network diagram...")
        
        # Clean and split content
        lines = self._clean_content(content)
        
        # First pass: Extract field definitions and class assignments
        field_ids = self._extract_field_ids(lines)
        print(f"\nFound field IDs: {sorted(field_ids)}")
        
        # Second pass: Extract all node IDs
        node_ids = self._extract_all_node_ids(lines)
        node_ids.update(field_ids)
        print(f"\nTotal unique nodes: {len(node_ids)}")
        
        # Create components
        self._create_components(lines, network, node_ids)
        self._print_component_stats(network)
        
        # Add connections
        connection_count = self._add_connections(lines, network)
        print(f"\nAdded {connection_count} connections")
        
        return network

    def _clean_content(self, content: str) -> List[str]:
        """Clean and prepare Mermaid content"""
        return [line.strip() for line in content.split('\n')
                if line.strip() and not line.strip().startswith('%%')]

    def _extract_field_ids(self, lines: List[str]) -> Set[str]:
        """Extract field IDs from class assignments"""
        field_ids = set()
        field_pattern = re.compile(r'\s*(F\d+_\d+):::field')
        
        for line in lines:
            match = field_pattern.match(line)
            if match:
                field_ids.add(match.group(1))
                
        return field_ids

    def _extract_all_node_ids(self, lines: List[str]) -> Set[str]:
        """Extract all node IDs from the diagram"""
        node_ids = set()
        
        for line in lines:
            # Skip style definitions
            if ':::' in line or 'classDef' in line:
                continue
                
            if '["' in line:
                node_id = self._extract_node_id(line)
                if node_id:
                    node_ids.add(node_id)
            elif '-->' in line:
                source, targets = self._parse_connection_line(line)
                if source:
                    node_ids.add(source)
                    node_ids.update(targets)
        
        return node_ids

    def _extract_node_id(self, line: str) -> Optional[str]:
        """Extract node ID from a line"""
        match = re.match(r'\s*(\w+)\s*\[', line)
        if match:
            return match.group(1)
        
        match = re.match(r'\s*(\w+)\s*$', line)
        if match:
            return match.group(1)
        
        return None

    def _parse_node_definition(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse node definition into ID and label"""
        match = re.match(r'\s*(\w+)\s*\["([^"]+)"\]', line)
        if match:
            return match.group(1), match.group(2)
        
        match = re.match(r'\s*(\w+)\s*$', line)
        if match:
            return match.group(1), match.group(1)
        
        return None, None

    def _parse_connection_line(self, line: str) -> Tuple[Optional[str], List[str]]:
        """Parse connection line into source and targets"""
        clean_line = re.sub(r'\["[^"]+"\]', '', line).strip()
        parts = re.split(r'-+>', clean_line)
        
        if len(parts) != 2:
            return None, []
        
        source = parts[0].strip()
        targets = [t.strip() for t in parts[1].split('&') if t.strip()]
        
        return source, targets

    def _create_components(self, lines: List[str], network: IrrigationNetwork, node_ids: Set[str]):
        """Create components in the network"""
        # Process explicit definitions first
        defined_nodes = set()
        for line in lines:
            if '["' in line:
                node_id, label = self._parse_node_definition(line)
                if node_id and node_id in node_ids:
                    network.add_component(node_id, self._process_label(label))
                    defined_nodes.add(node_id)
        
        # Add remaining nodes
        for node_id in node_ids - defined_nodes:
            network.add_component(node_id, node_id)

    def _process_label(self, label: str) -> str:
        """Process and clean component label"""
        if not label:
            return ""
        return " ".join(part.strip() for part in label.split() if part.strip())

    def _print_component_stats(self, network: IrrigationNetwork):
        """Print component statistics"""
        type_counts = {}
        for comp_id, comp in network.components.items():
            comp_type = comp.component_type
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        
        print("\nComponents by type:", type_counts)

    def _add_connections(self, lines: List[str], network: IrrigationNetwork) -> int:
        """Add connections between components"""
        connection_count = 0
        
        for line in lines:
            if '-->' in line and ':::' not in line:
                source, targets = self._parse_connection_line(line)
                if source and targets:
                    for target in targets:
                        if (source in network.components and 
                            target in network.components):
                            network.add_connection(source, target)
                            connection_count += 1
        
        return connection_count

    def validate_network(self, network: IrrigationNetwork) -> Tuple[bool, List[str]]:
        """
        Validate the network structure
        
        Args:
            network (IrrigationNetwork): Network to validate
            
        Returns:
            Tuple[bool, List[str]]: Validation status and list of errors
        """
        errors = []
        
        # Check for disconnected components
        self._validate_connectivity(network, errors)
        
        # Check distribution points
        self._validate_distribution_points(network, errors)
        
        # Check smart water meters
        self._validate_smart_water_meters(network, errors)
        
        return len(errors) == 0, errors

    def _validate_connectivity(self, network: IrrigationNetwork, errors: List[str]):
        """Validate component connectivity"""
        for comp_id, component in network.components.items():
            if not component.connections_to and not component.connections_from:
                errors.append(f"Component {comp_id} is disconnected")

    def _validate_distribution_points(self, network: IrrigationNetwork, errors: List[str]):
        """Validate distribution point configurations"""
        for comp_id, component in network.components.items():
            if comp_id.startswith('DP'):
                if comp_id != 'DP0' and not component.connections_from:
                    errors.append(f"Distribution point {comp_id} has no input")
                if not component.connections_to and not any(c.startswith('F') for c in component.connections_to):
                    errors.append(f"Distribution point {comp_id} has no output")

    def _validate_smart_water_meters(self, network: IrrigationNetwork, errors: List[str]):
        """Validate smart water meter configurations"""
        for comp_id, component in network.components.items():
            if comp_id.startswith('SW'):
                if len(component.connections_from) != 1:
                    errors.append(f"Smart water meter {comp_id} should have exactly one input")
                if len(component.connections_to) != 1:
                    errors.append(f"Smart water meter {comp_id} should have exactly one output")