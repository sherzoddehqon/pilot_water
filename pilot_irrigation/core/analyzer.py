from typing import Dict, List, Set, Optional, Tuple
from core.network import IrrigationNetwork
from dataclasses import dataclass
from core.blocks.components import IrrigationBlock, Joint, JointType

@dataclass
class AnalysisStep:
    step_number: int
    description: str
    components: List
    requires_approval: bool = False
    approved: bool = False

class NetworkAnalyzer:
    def __init__(self):
        self.network = None
        self.analysis_steps = []

    def analyze_network(self, network: IrrigationNetwork) -> List[AnalysisStep]:
        """Perform stepped analysis of network"""
        self.network = network
        self.analysis_steps = []
        
        # Step 1: Component Detection
        components = [
            f"{comp_id} ({comp.component_type})"
            for comp_id, comp in network.components.items()
        ]
        self.analysis_steps.append(AnalysisStep(
            1,
            "Network Component Detection",
            components
        ))

        # Step 2: Block Detection
        self._detect_blocks()
        blocks = []
        for block_id, block in network.blocks.items():
            blocks.append({
                'id': block_id,
                'components': list(block.components),
                'distribution_canal': block.distribution_canal
            })
        self.analysis_steps.append(AnalysisStep(
            2,
            "Irrigation Block Detection",
            blocks
        ))

        # Step 3: Confluence Detection
        self._detect_confluences()
        confluences = []
        for block in network.blocks.values():
            for confluence in block.confluence_points:
                confluences.append({
                    'block': block.id,
                    'upstream': confluence.upstream_components,
                    'downstream': confluence.downstream_component
                })
        self.analysis_steps.append(AnalysisStep(
            3,
            "Confluence Point Detection",
            confluences
        ))

        # Step 4: Hierarchy Calculation
        self._calculate_hierarchy()
        hierarchy = []
        for block_id, block in network.blocks.items():
            hierarchy.append({
                'block': block_id,
                'order': block.order,
                'manual_order': block.manual_order
            })
        self.analysis_steps.append(AnalysisStep(
            4,
            "Network Hierarchy Analysis",
            hierarchy,
            requires_approval=True
        ))

        # Step 5 placeholder - paths will be analyzed after hierarchy approval
        self.analysis_steps.append(AnalysisStep(
            5,
            "Path Analysis",
            [],
            requires_approval=False
        ))

        return self.analysis_steps

    def _analyze_paths(self) -> None:
        """Analyze water distribution paths after hierarchy approval"""
        if not self.network or len(self.analysis_steps) < 5:
            return

        paths = []
        
        # Find field components
        fields = [comp_id for comp_id, comp in self.network.components.items()
                 if comp_id.startswith('F')]
                 
        # Calculate paths for each field
        for field_id in fields:
            field_paths = self.network.get_field_feeding_path(field_id)
            for path in field_paths:
                paths.append(path)

        # Update path analysis step
        path_step = self.analysis_steps[4]  # Index 4 is step 5
        path_step.components = paths

    # Original methods remain unchanged
    def _detect_blocks(self) -> None:
        """Detect network blocks based on distribution canals"""
        visited_canals = set()
        
        # Find main canals
        main_canals = [comp_id for comp_id, comp in self.network.components.items()
                      if comp_id.startswith('MC') and not comp.connections_from]
                      
        for canal_id in main_canals:
            if canal_id in visited_canals:
                continue
                
            block_id = self.network.create_block()
            self._process_canal_group(canal_id, block_id, visited_canals)

    def _process_canal_group(self, canal_id: str, block_id: str, 
                           visited: Set[str]) -> None:
        """Process canal and its connected components"""
        if canal_id in visited:
            return
            
        visited.add(canal_id)
        self.network.assign_to_block(canal_id, block_id)
        self.network.set_distribution_canal(block_id, canal_id)
        
        component = self.network.components[canal_id]
        for target_id in component.connections_to:
            target = self.network.components[target_id]
            
            # Add control components to block
            if any(target_id.startswith(prefix) for prefix in ['ZT', 'SW']):
                self.network.assign_to_block(target_id, block_id)
                self._create_internal_joint(block_id, canal_id, target_id)
                
            # Process connected fields
            elif target_id.startswith('F'):
                self.network.assign_to_block(target_id, block_id)
                self._create_internal_joint(block_id, canal_id, target_id)

    def _detect_confluences(self) -> None:
        """Detect confluence points in network"""
        for comp_id, component in self.network.components.items():
            if len(component.connections_from) > 1:
                block_id = self.network.get_component_block(comp_id)
                if not block_id:
                    continue
                    
                # Create confluence for multiple inputs
                for source_id in component.connections_from:
                    source_block = self.network.get_component_block(source_id)
                    if source_block and source_block != block_id:
                        self._create_confluence(source_block, block_id, 
                                             source_id, comp_id)

    def _calculate_hierarchy(self) -> None:
        """Calculate network hierarchy"""
        # First pass: Set initial orders based on field connections
        for block_id, block in self.network.blocks.items():
            if any(comp_id.startswith('F') for comp_id in block.components):
                block.set_manual_order(1)
                
        # Second pass: Process confluences
        self._process_confluence_hierarchy()
        
        # Final pass: Calculate full hierarchy
        self.network.calculate_hierarchy()

    def _process_confluence_hierarchy(self) -> None:
        """Process hierarchy based on confluences"""
        confluence_blocks = set()
        
        # Find blocks with confluences
        for block in self.network.blocks.values():
            if block.confluence_points:
                confluence_blocks.add(block.id)
                
        # Process each confluence block
        for block_id in confluence_blocks:
            block = self.network.blocks[block_id]
            
            # Find maximum order of input blocks
            max_input_order = 0
            for confluence in block.confluence_points:
                for upstream_id in confluence.upstream_components:
                    upstream_block = self.network.get_component_block(upstream_id)
                    if upstream_block:
                        upstream = self.network.blocks[upstream_block]
                        if upstream.manual_order:
                            max_input_order = max(max_input_order, 
                                               upstream.manual_order)
            
            # Set order one higher than max input
            if max_input_order > 0:
                block.set_manual_order(max_input_order + 1)

    def _create_internal_joint(self, block_id: str, upstream_id: str, 
                             downstream_id: str) -> None:
        """Create internal joint within block"""
        self.network.create_joint(block_id, upstream_id, downstream_id, False)

    def _create_confluence(self, source_block: str, target_block: str,
                         source_id: str, target_id: str) -> None:
        """Create confluence between blocks"""
        self.network.create_joint(target_block, source_id, target_id, True)