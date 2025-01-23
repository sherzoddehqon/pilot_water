from typing import Dict, List, Set, Tuple, Optional
from core.components import NetworkComponent
from core.blocks import Block, Joint, JointType

class IrrigationNetwork:
    def __init__(self):
        self.components: Dict[str, NetworkComponent] = {}
        self.blocks: Dict[str, IrrigationBlock] = {}
        self.component_to_block: Dict[str, str] = {}
        self._next_block_id: int = 1

    def add_component(self, id: str, label: str) -> NetworkComponent:
        component = NetworkComponent(id=id, label=label)
        self.components[id] = component
        return component

    def add_connection(self, source_id: str, target_id: str) -> None:
        if source_id in self.components and target_id in self.components:
            self.components[source_id].add_connection_to(target_id)
            self.components[target_id].add_connection_from(source_id)

    def create_block(self, order: Optional[int] = None) -> str:
        block_id = f"B{self._next_block_id}"
        self._next_block_id += 1
        
        block = IrrigationBlock(block_id, "standard")
        if order is not None:
            block.set_manual_order(order)
        
        self.blocks[block_id] = block
        return block_id

    def assign_to_block(self, component_id: str, block_id: str) -> bool:
        if component_id not in self.components or block_id not in self.blocks:
            return False

        # Remove from old block if exists
        old_block_id = self.component_to_block.get(component_id)
        if old_block_id:
            self.blocks[old_block_id].components.remove(component_id)

        # Add to new block
        self.blocks[block_id].add_component(component_id)
        self.component_to_block[component_id] = block_id
        return True

    def create_joint(self, block_id: str, upstream_id: str, downstream_id: str, 
                    is_confluence: bool = False) -> Optional[str]:
        if block_id not in self.blocks:
            return None

        joint_type = JointType.CONFLUENCE if is_confluence else JointType.INTERNAL
        joint = Joint(
            id=f"J{len(self.blocks[block_id].all_joints) + 1}",
            joint_type=joint_type,
            upstream_components=[upstream_id],
            downstream_components=[downstream_id]
        )
        
        self.blocks[block_id].add_joint(joint)
        return joint.id

    def set_distribution_canal(self, block_id: str, canal_id: str) -> bool:
        if (block_id not in self.blocks or 
            canal_id not in self.components or 
            not canal_id.startswith('MC')):
            return False

        self.blocks[block_id].set_distribution_canal(canal_id)
        return True

    def set_component_order(self, component_id: str, order: int) -> bool:
        if component_id not in self.components:
            return False

        block_id = self.component_to_block.get(component_id)
        if block_id:
            self.blocks[block_id].set_manual_order(order)
        return True

    def get_block_components(self, block_id: str) -> List[str]:
        if block_id not in self.blocks:
            return []
        return list(self.blocks[block_id].components)

    def get_component_block(self, component_id: str) -> Optional[str]:
        return self.component_to_block.get(component_id)

    def get_blocks_by_order(self) -> Dict[int, List[str]]:
        result: Dict[int, List[str]] = {}
        for block_id, block in self.blocks.items():
            if block.manual_order is not None:
                order = block.manual_order
                if order not in result:
                    result[order] = []
                result[order].append(block_id)
        return result

    def calculate_hierarchy(self) -> None:
        """Calculate hierarchy considering manual orders and confluences"""
        # Reset levels
        for block in self.blocks.values():
            block.hierarchy_level = -1

        # Start from lowest order blocks
        ordered_blocks = sorted(
            self.blocks.values(), 
            key=lambda b: b.manual_order if b.manual_order is not None else float('inf')
        )

        for block in ordered_blocks:
            if block.manual_order is not None:
                block.hierarchy_level = block.manual_order
                self._propagate_levels(block)

    def _propagate_levels(self, block: Block) -> None:
        """Propagate levels through confluences"""
        for confluence in block.confluence_points:
            downstream_component = confluence.downstream_components[0]
            downstream_block_id = self.component_to_block.get(downstream_component)
            
            if downstream_block_id:
                downstream_block = self.blocks[downstream_block_id]
                if downstream_block.manual_order is None:
                    new_level = block.hierarchy_level + 1
                    if new_level > downstream_block.hierarchy_level:
                        downstream_block.hierarchy_level = new_level
                        self._propagate_levels(downstream_block)