from typing import List, Tuple, Dict, Set
from core.network import IrrigationNetwork
from core.blocks.components import IrrigationBlock, Joint

class NetworkValidator:
    def __init__(self, network: IrrigationNetwork):
        self.network = network
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validation checks"""
        self.errors.clear()
        self.warnings.clear()

        self._validate_blocks()
        self._validate_hierarchy()
        self._validate_confluences()
        self._validate_connectivity()

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_blocks(self) -> None:
        """Validate irrigation block structure"""
        visited_components = set()

        for block in self.network.blocks.values():
            # Check distribution canal
            if not block.distribution_canal:
                self.errors.append(f"Block {block.id} has no distribution canal")
            elif not block.distribution_canal.startswith('MC'):
                self.errors.append(f"Block {block.id} has invalid distribution canal type: {block.distribution_canal}")

            # Check component assignments
            for comp_id in block.components:
                if comp_id in visited_components:
                    self.errors.append(f"Component {comp_id} assigned to multiple blocks")
                visited_components.add(comp_id)

                # Validate component relationships
                comp = self.network.components.get(comp_id)
                if not comp:
                    self.errors.append(f"Block {block.id} references non-existent component {comp_id}")
                    continue

                if comp_id.startswith('F'):
                    self._validate_field_connections(block, comp_id, comp)
                elif comp_id.startswith(('ZT', 'SW')):
                    self._validate_control_point(block, comp_id, comp)

            # Check block completeness
            if not any(c.startswith('F') for c in block.components):
                self.warnings.append(f"Block {block.id} has no fields")

    def _validate_hierarchy(self) -> None:
        """Validate network hierarchy levels"""
        for block in self.network.blocks.values():
            if block.order < 0:
                self.errors.append(f"Block {block.id} has invalid order: {block.order}")

            # Check level consistency
            upstream_blocks = self._get_upstream_blocks(block)
            for up_block in upstream_blocks:
                if up_block.order >= block.order:
                    self.errors.append(
                        f"Invalid hierarchy: Block {up_block.id} (order {up_block.order}) "
                        f"feeds into Block {block.id} (order {block.order})"
                    )

    def _validate_confluences(self) -> None:
        """Validate confluence points"""
        for block in self.network.blocks.values():
            for confluence in block.confluence_points:
                # Check upstream components
                if not confluence.upstream_components:
                    self.errors.append(f"Confluence in block {block.id} has no upstream components")
                    continue

                for up_comp in confluence.upstream_components:
                    if not self._is_valid_upstream_component(block, up_comp):
                        self.errors.append(
                            f"Invalid upstream component {up_comp} in confluence "
                            f"of block {block.id}"
                        )

                # Check downstream component
                if not confluence.downstream_component:
                    self.errors.append(f"Confluence in block {block.id} has no downstream component")
                elif not self._is_valid_downstream_component(block, confluence.downstream_component):
                    self.errors.append(
                        f"Invalid downstream component {confluence.downstream_component} "
                        f"in confluence of block {block.id}"
                    )

    def _validate_connectivity(self) -> None:
        """Validate network connectivity"""
        # Check for disconnected components
        for comp_id, comp in self.network.components.items():
            if not comp.connections_to and not comp.connections_from:
                self.warnings.append(f"Component {comp_id} is disconnected from network")

        # Validate path to each field
        fields = [comp_id for comp_id in self.network.components if comp_id.startswith('F')]
        for field_id in fields:
            paths = self.network.get_field_feeding_path(field_id)
            if not paths:
                self.errors.append(f"No valid water path to field {field_id}")

    def _validate_field_connections(self, block: IrrigationBlock, field_id: str, field) -> None:
        """Validate field connections within block"""
        if not field.connections_from:
            self.errors.append(f"Field {field_id} in block {block.id} has no water source")
        
        for source_id in field.connections_from:
            if source_id not in block.components:
                self.errors.append(
                    f"Field {field_id} in block {block.id} has connection from "
                    f"external component {source_id}"
                )

    def _validate_control_point(self, block: IrrigationBlock, point_id: str, point) -> None:
        """Validate control point connections"""
        if not point.connections_from:
            self.errors.append(f"Control point {point_id} in block {block.id} has no input")
        if not point.connections_to:
            self.errors.append(f"Control point {point_id} in block {block.id} has no output")

    def _get_upstream_blocks(self, block: IrrigationBlock) -> Set[IrrigationBlock]:
        """Get all blocks that feed into this block"""
        upstream = set()
        for confluence in block.confluence_points:
            for up_comp in confluence.upstream_components:
                up_block_id = self.network.get_component_block(up_comp)
                if up_block_id and up_block_id != block.id:
                    upstream.add(self.network.blocks[up_block_id])
        return upstream

    def _is_valid_upstream_component(self, block: IrrigationBlock, comp_id: str) -> bool:
        """Check if component is valid upstream source"""
        if comp_id not in self.network.components:
            return False
        comp = self.network.components[comp_id]
        return any(out_id == block.distribution_canal for out_id in comp.connections_to)

    def _is_valid_downstream_component(self, block: IrrigationBlock, comp_id: str) -> bool:
        """Check if component is valid downstream target"""
        return comp_id in block.components
