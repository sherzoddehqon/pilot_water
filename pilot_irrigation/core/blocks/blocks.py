from typing import Dict, List, Set, Optional, Union, Any
from .types import BlockType, JointType
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Joint:
    """Represents a connection between components"""
    id: str
    joint_type: JointType
    upstream_components: List[str]
    downstream_components: List[str]
    level: int = -1
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_confluence(self) -> bool:
        return self.joint_type == JointType.CONFLUENCE

@dataclass
class Block:
    """Represents a network sub-basin or block"""
    id: str
    block_type: BlockType
    components: Set[str] = field(default_factory=set)
    joints: Dict[str, Joint] = field(default_factory=dict)
    level: int = -1
    manual_order: Optional[int] = None
    parent_id: Optional[str] = None
    child_ids: Set[str] = field(default_factory=set)
    distribution_canal: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def add_component(self, component_id: str) -> None:
        """Add a component to the block"""
        self.components.add(component_id)
        if component_id.startswith('MC') and not self.distribution_canal:
            self.set_distribution_canal(component_id)

    def remove_component(self, component_id: str) -> bool:
        """Remove a component from the block"""
        if component_id in self.components:
            self.components.remove(component_id)
            if component_id == self.distribution_canal:
                self.distribution_canal = None
            return True
        return False

    def set_distribution_canal(self, canal_id: str) -> None:
        """Set the main distribution canal for the block"""
        if canal_id in self.components and canal_id.startswith('MC'):
            self.distribution_canal = canal_id
            self.attributes['distribution_canal'] = canal_id

    def add_joint(self, joint: Joint) -> None:
        """Add a joint to the block"""
        self.joints[joint.id] = joint

    def remove_joint(self, joint_id: str) -> Optional[Joint]:
        """Remove a joint from the block"""
        return self.joints.pop(joint_id, None)

    def set_level(self, level: int) -> None:
        """Set the hierarchy level of the block"""
        self.level = level

    def set_manual_order(self, order: int) -> None:
        """Set manual ordering for the block"""
        self.manual_order = order
        self.attributes['manual_order'] = order

    @property
    def confluence_joints(self) -> List[Joint]:
        """Get all confluence joints in the block"""
        return [j for j in self.joints.values() if j.is_confluence]

    @property
    def internal_joints(self) -> List[Joint]:
        """Get all internal joints in the block"""
        return [j for j in self.joints.values() if not j.is_confluence]

class BlockManager:
    """Manages blocks and their relationships in the irrigation network"""

    def __init__(self):
        self.blocks: Dict[str, Block] = {}
        self.component_to_block: Dict[str, str] = {}
        self._next_block_id: int = 1
        self._next_joint_id: int = 1

    def create_block(self, block_type: BlockType, manual_order: Optional[int] = None) -> str:
        """Create a new block and return its ID"""
        block_id = f"B{self._next_block_id}"
        self._next_block_id += 1
        
        block = Block(id=block_id, block_type=block_type)
        if manual_order is not None:
            block.set_manual_order(manual_order)
            
        self.blocks[block_id] = block
        logger.info(f"Created block: {block_id} ({block_type.value})")
        return block_id

    def delete_block(self, block_id: str) -> bool:
        """Delete a block and clean up its relationships"""
        if block_id not in self.blocks:
            return False

        block = self.blocks[block_id]

        # Remove parent reference
        if block.parent_id and block.parent_id in self.blocks:
            self.blocks[block.parent_id].child_ids.remove(block_id)

        # Remove child references
        for child_id in block.child_ids:
            if child_id in self.blocks:
                self.blocks[child_id].parent_id = None

        # Remove component mappings
        for comp_id in block.components:
            self.component_to_block.pop(comp_id, None)

        # Remove block
        del self.blocks[block_id]
        logger.info(f"Deleted block: {block_id}")
        return True

    def assign_component(self, component_id: str, block_id: str) -> bool:
        """Assign a component to a block"""
        if block_id not in self.blocks:
            return False

        # Remove from old block if necessary
        old_block_id = self.component_to_block.get(component_id)
        if old_block_id:
            self.blocks[old_block_id].remove_component(component_id)

        # Add to new block
        self.blocks[block_id].add_component(component_id)
        self.component_to_block[component_id] = block_id
        return True

    def create_joint(self, block_id: str, upstream: List[str], 
                    downstream: List[str], is_confluence: bool = False) -> Optional[str]:
        """Create a new joint in a block"""
        if block_id not in self.blocks:
            return None

        joint_id = f"J{self._next_joint_id}"
        self._next_joint_id += 1

        joint_type = JointType.CONFLUENCE if is_confluence else JointType.INTERNAL
        joint = Joint(
            id=joint_id,
            joint_type=joint_type,
            upstream_components=upstream,
            downstream_components=downstream
        )

        self.blocks[block_id].add_joint(joint)
        return joint_id

    def set_block_relationship(self, parent_id: str, child_id: str) -> bool:
        """Establish parent-child relationship between blocks"""
        if parent_id not in self.blocks or child_id not in self.blocks:
            return False

        parent = self.blocks[parent_id]
        child = self.blocks[child_id]

        # Remove old parent if exists
        if child.parent_id and child.parent_id != parent_id:
            old_parent = self.blocks[child.parent_id]
            old_parent.child_ids.remove(child_id)

        # Set new relationship
        parent.child_ids.add(child_id)
        child.parent_id = parent_id

        # Update levels
        self._update_block_levels()
        return True

    def _update_block_levels(self) -> None:
        """Update hierarchy levels for all blocks"""
        # Reset levels
        for block in self.blocks.values():
            block.level = -1

        # Find root blocks (no parent)
        roots = [block_id for block_id, block in self.blocks.items() 
                if not block.parent_id]

        # Calculate levels from roots
        for root_id in roots:
            self._calculate_block_level(root_id, 0)

    def _calculate_block_level(self, block_id: str, level: int) -> None:
        """Recursively calculate levels for a block and its children"""
        block = self.blocks[block_id]
        block.level = level

        for child_id in block.child_ids:
            self._calculate_block_level(child_id, level + 1)

    def get_block_hierarchy(self) -> Dict[int, List[str]]:
        """Get blocks organized by hierarchy level"""
        hierarchy: Dict[int, List[str]] = {}
        for block in self.blocks.values():
            if block.level >= 0:
                if block.level not in hierarchy:
                    hierarchy[block.level] = []
                hierarchy[block.level].append(block.id)
        return hierarchy

    def detect_confluences(self) -> None:
        """Identify and mark confluence points between blocks"""
        for block in self.blocks.values():
            for joint in block.joints.values():
                # Check if components are from different blocks
                upstream_blocks = {self.component_to_block.get(comp) 
                                for comp in joint.upstream_components}
                downstream_blocks = {self.component_to_block.get(comp) 
                                  for comp in joint.downstream_components}

                # Remove None values (components not in blocks)
                upstream_blocks.discard(None)
                downstream_blocks.discard(None)

                # If components span multiple blocks, mark as confluence
                if len(upstream_blocks.union(downstream_blocks)) > 1:
                    joint.joint_type = JointType.CONFLUENCE
                    logger.info(f"Detected confluence joint: {joint.id}")

    def validate(self) -> List[str]:
        """Validate the block structure"""
        errors = []

        # Check block hierarchy
        for block in self.blocks.values():
            if block.parent_id:
                parent = self.blocks.get(block.parent_id)
                if not parent:
                    errors.append(
                        f"Block {block.id} references non-existent parent {block.parent_id}")
                elif block.id not in parent.child_ids:
                    errors.append(
                        f"Inconsistent parent-child relationship between {parent.id} and {block.id}")

            # Check block type constraints
            if block.block_type == BlockType.TERMINAL and block.child_ids:
                errors.append(f"Terminal block {block.id} should not have children")

            # Check distribution canal
            if not block.distribution_canal:
                errors.append(f"Block {block.id} has no distribution canal")

        # Check component assignments
        assigned_components = set()
        for comp_id, block_id in self.component_to_block.items():
            if block_id not in self.blocks:
                errors.append(f"Component {comp_id} assigned to non-existent block {block_id}")
            elif comp_id not in self.blocks[block_id].components:
                errors.append(f"Inconsistent component assignment for {comp_id}")
            if comp_id in assigned_components:
                errors.append(f"Component {comp_id} assigned to multiple blocks")
            assigned_components.add(comp_id)

        return errors