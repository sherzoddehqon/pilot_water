from typing import Dict, List, Set, Optional, Any
from enum import Enum
from dataclasses import dataclass

class JointType(Enum):
    INTERNAL = "internal"
    CONFLUENCE = "confluence"

@dataclass
class Joint:
    id: str
    joint_type: JointType
    upstream_components: List[str]
    downstream_components: List[str]
    hierarchy_level: int = -1
    attributes: Dict[str, Any] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}

    @property
    def is_confluence(self) -> bool:
        return self.joint_type == JointType.CONFLUENCE

class IrrigationBlock:
    def __init__(self, block_id: str, block_type: str):
        self.id: str = block_id
        self.block_type: str = block_type
        self.manual_order: Optional[int] = None
        self.components: Set[str] = set()
        self.joints: Dict[str, Joint] = {}
        self.confluences: Dict[str, Joint] = {}
        self.parent_block: Optional[str] = None
        self.child_blocks: Set[str] = set()
        self.distribution_canal: Optional[str] = None
        self.hierarchy_level: int = -1
        self.attributes: Dict[str, Any] = {}

    def set_manual_order(self, order: int) -> None:
        """Set manual order for the block"""
        self.manual_order = order
        self.attributes['manual_order'] = order

    def add_component(self, component_id: str) -> None:
        """Add component to block"""
        self.components.add(component_id)
        if component_id.startswith('MC') and not self.distribution_canal:
            self.set_distribution_canal(component_id)

    def set_distribution_canal(self, canal_id: str) -> None:
        """Set main distribution canal"""
        if canal_id in self.components:
            self.distribution_canal = canal_id
            self.attributes['distribution_canal'] = canal_id

    def add_joint(self, joint: Joint) -> None:
        """Add joint or confluence based on type"""
        if joint.is_confluence:
            self.confluences[joint.id] = joint
        else:
            self.joints[joint.id] = joint

    def remove_joint(self, joint_id: str) -> Optional[Joint]:
        """Remove joint from appropriate collection"""
        if joint_id in self.joints:
            return self.joints.pop(joint_id)
        return self.confluences.pop(joint_id, None)

    def get_component_joints(self, component_id: str) -> List[Joint]:
        """Get all joints connected to component"""
        return [j for j in self.all_joints if 
                component_id in j.upstream_components or 
                component_id in j.downstream_components]

    @property
    def all_joints(self) -> List[Joint]:
        """Get all joints including confluences"""
        return list(self.joints.values()) + list(self.confluences.values())

    @property
    def internal_joints(self) -> List[Joint]:
        """Get only internal joints"""
        return list(self.joints.values())

    @property
    def confluence_points(self) -> List[Joint]:
        """Get only confluence points"""
        return list(self.confluences.values())

    def set_parent(self, parent_id: str) -> None:
        """Set parent block"""
        self.parent_block = parent_id

    def add_child(self, child_id: str) -> None:
        """Add child block"""
        self.child_blocks.add(child_id)

    def remove_child(self, child_id: str) -> bool:
        """Remove child block"""
        if child_id in self.child_blocks:
            self.child_blocks.remove(child_id)
            return True
        return False

    def calculate_level(self, block_manager: 'BlockManager') -> int:
        """Calculate hierarchy level based on order and confluences"""
        if self.manual_order is not None:
            self.hierarchy_level = self.manual_order
            return self.manual_order

        # Use existing logic as fallback
        max_child_level = 0
        for child_id in self.child_blocks:
            child_block = block_manager.blocks.get(child_id)
            if child_block:
                child_level = child_block.calculate_level(block_manager)
                max_child_level = max(max_child_level, child_level)

        self.hierarchy_level = max_child_level + 1
        return self.hierarchy_level