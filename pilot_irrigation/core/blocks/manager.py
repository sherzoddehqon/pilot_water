from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import logging
from .types import BlockType, JointType
from .components import IrrigationBlock, Joint

logger = logging.getLogger(__name__)

class BlockManager:
    """Manages blocks and their relationships in the irrigation network."""
    
    def __init__(self):
        """Initialize the block manager."""
        self.blocks: Dict[str, IrrigationBlock] = {}
        self.component_to_block: Dict[str, str] = {}
        self.joint_to_block: Dict[str, str] = {}
        self._next_joint_id: int = 1
    
    def create_block(self, block_id: str, block_type: BlockType) -> IrrigationBlock:
        """Create a new block."""
        if block_id in self.blocks:
            raise ValueError(f"Block {block_id} already exists")
            
        block = IrrigationBlock(block_id, block_type)
        self.blocks[block_id] = block
        logger.info(f"Created block: {block_id} ({block_type.value})")
        return block
    
    def get_block(self, block_id: str) -> Optional[IrrigationBlock]:
        """Get a block by ID."""
        return self.blocks.get(block_id)
    
    def delete_block(self, block_id: str) -> bool:
        """Delete a block and its relationships."""
        if block_id not in self.blocks:
            return False
            
        block = self.blocks[block_id]
        
        # Remove parent reference
        if block.parent_block and block.parent_block in self.blocks:
            self.blocks[block.parent_block].remove_child(block_id)
            self._recalculate_levels(self.blocks[block.parent_block])
        
        # Remove child references
        for child_id in block.child_blocks:
            if child_id in self.blocks:
                self.blocks[child_id].parent_block = None
                self._recalculate_levels(self.blocks[child_id])
        
        # Remove component mappings
        for comp_id in block.components:
            self.component_to_block.pop(comp_id, None)
        
        # Remove joint mappings
        for joint_id in block.joints:
            self.joint_to_block.pop(joint_id, None)
        
        # Remove block
        del self.blocks[block_id]
        logger.info(f"Deleted block: {block_id}")
        return True
    
    def assign_component(self, component_id: str, block_id: str) -> bool:
        """Assign a component to a block."""
        if block_id not in self.blocks:
            raise ValueError(f"Block {block_id} does not exist")
            
        # Remove from old block if necessary
        old_block_id = self.component_to_block.get(component_id)
        if old_block_id:
            self.blocks[old_block_id].remove_component(component_id)
            
        # Add to new block
        self.blocks[block_id].add_component(component_id)
        self.component_to_block[component_id] = block_id
        logger.info(f"Assigned component {component_id} to block {block_id}")
        return True
    
    def create_joint(self, upstream: List[str], downstream: List[str], 
                    joint_type: JointType = JointType.INTERNAL) -> Joint:
        """Create a new joint."""
        joint_id = f"J{self._next_joint_id}"
        self._next_joint_id += 1
        
        joint = Joint(joint_id, joint_type, upstream, downstream)
        logger.info(f"Created joint: {joint_id} ({joint_type.value})")
        return joint
    
    def assign_joint(self, joint: Joint, block_id: str) -> bool:
        """Assign a joint to a block."""
        if block_id not in self.blocks:
            raise ValueError(f"Block {block_id} does not exist")
            
        self.blocks[block_id].add_joint(joint)
        self.joint_to_block[joint.id] = block_id
        logger.info(f"Assigned joint {joint.id} to block {block_id}")
        return True
    
    def set_block_relationship(self, parent_id: str, child_id: str) -> bool:
        """Establish parent-child relationship between blocks."""
        if parent_id not in self.blocks or child_id not in self.blocks:
            raise ValueError("Invalid block ID")
            
        parent_block = self.blocks[parent_id]
        child_block = self.blocks[child_id]
        
        # Set relationship
        parent_block.add_child(child_id)
        child_block.set_parent(parent_id)
        
        # Recalculate levels starting from the root
        self._recalculate_hierarchy()
        
        logger.info(f"Set relationship: {parent_id} -> {child_id}")
        return True
    
    def _recalculate_hierarchy(self) -> None:
        """Recalculate hierarchy levels for all blocks."""
        # Reset all levels
        for block in self.blocks.values():
            block.hierarchy_level = -1
        
        # Find root blocks (no parent)
        root_blocks = [block_id for block_id, block in self.blocks.items()
                      if not block.parent_block]
        
        # Calculate levels starting from roots
        for root_id in root_blocks:
            self.blocks[root_id].calculate_level(self)
        
        logger.info("Recalculated hierarchy levels")
    
    def _recalculate_levels(self, block: IrrigationBlock) -> None:
        """Recalculate levels for a block and its subtree."""
        block.hierarchy_level = -1  # Reset level
        block.calculate_level(self)  # Recalculate
        
        # Recalculate parent levels if needed
        current = block
        while current.parent_block:
            parent = self.blocks[current.parent_block]
            parent.hierarchy_level = -1  # Reset
            parent.calculate_level(self)  # Recalculate
            current = parent
    
    def get_block_hierarchy(self) -> Dict[int, List[str]]:
        """Get blocks organized by hierarchy level."""
        hierarchy: Dict[int, List[str]] = defaultdict(list)
        for block in self.blocks.values():
            if block.hierarchy_level >= 0:
                hierarchy[block.hierarchy_level].append(block.id)
        return dict(hierarchy)
    
    def get_component_block(self, component_id: str) -> Optional[IrrigationBlock]:
        """Get the block containing a component."""
        block_id = self.component_to_block.get(component_id)
        if block_id:
            return self.blocks.get(block_id)
        return None
    
    def get_joint_block(self, joint_id: str) -> Optional[IrrigationBlock]:
        """Get the block containing a joint."""
        block_id = self.joint_to_block.get(joint_id)
        if block_id:
            return self.blocks.get(block_id)
        return None
    
    def detect_confluence_joints(self) -> None:
        """Identify confluence points in the network."""
        for block in self.blocks.values():
            for joint in block.joints.values():
                # Check if components are from different hierarchy levels
                upstream_levels = set()
                downstream_levels = set()
                
                for comp_id in joint.upstream_components:
                    comp_block = self.get_component_block(comp_id)
                    if comp_block:
                        upstream_levels.add(comp_block.hierarchy_level)
                        
                for comp_id in joint.downstream_components:
                    comp_block = self.get_component_block(comp_id)
                    if comp_block:
                        downstream_levels.add(comp_block.hierarchy_level)
                
                # If levels differ, mark as confluence
                if upstream_levels.union(downstream_levels):
                    min_level = min(upstream_levels.union(downstream_levels))
                    max_level = max(upstream_levels.union(downstream_levels))
                    if min_level != max_level:
                        joint.joint_type = JointType.CONFLUENCE
                        joint.hierarchy_level = min_level
                        logger.info(f"Detected confluence joint: {joint.id}")
    
    def validate_network(self) -> Tuple[bool, List[str]]:
        """Validate the network structure."""
        errors = []
        
        # Check block hierarchy
        for block in self.blocks.values():
            # Check parent relationship
            if block.parent_block:
                parent = self.blocks.get(block.parent_block)
                if not parent:
                    errors.append(f"Block {block.id} references non-existent parent {block.parent_block}")
                elif parent.hierarchy_level <= block.hierarchy_level:
                    errors.append(f"Block {block.id} has invalid hierarchy relationship with parent")
            
            # Check child relationships
            for child_id in block.child_blocks:
                child = self.blocks.get(child_id)
                if not child:
                    errors.append(f"Block {block.id} references non-existent child {child_id}")
        
        # Check component assignments
        for comp_id, block_id in self.component_to_block.items():
            if block_id not in self.blocks:
                errors.append(f"Component {comp_id} assigned to non-existent block {block_id}")
            elif comp_id not in self.blocks[block_id].components:
                errors.append(f"Component {comp_id} has inconsistent block assignment")
        
        # Check joint assignments
        for joint_id, block_id in self.joint_to_block.items():
            if block_id not in self.blocks:
                errors.append(f"Joint {joint_id} assigned to non-existent block {block_id}")
            elif joint_id not in self.blocks[block_id].joints:
                errors.append(f"Joint {joint_id} has inconsistent block assignment")
        
        return len(errors) == 0, errors