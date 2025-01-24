from enum import Enum
from typing import Dict, List, Set, Optional

class JointType(Enum):
    """Types of joints in the irrigation network."""
    INTERNAL = "internal"   # Connection within same hierarchy
    CONFLUENCE = "confluence"  # Connection between different hierarchies
    
    def __str__(self) -> str:
        return self.value

class BlockType(Enum):
    """Types of blocks in the irrigation network.
    
    A block represents a logical grouping of components in the network.
    The hierarchy level is determined dynamically based on network topology,
    not by the block type.
    
    Attributes:
        MAIN: Main canal system block
            Contains primary canals and major distribution points
            Example: Main canal system feeding multiple zones
            
        DISTRIBUTION: Distribution block
            Contains secondary/tertiary canals and distribution points
            Example: Distribution zone feeding other zones or fields
            
        TERMINAL: Terminal block directly feeding fields
            Contains final distribution points and field connections
            Example: Group of fields fed by same terminal canal
    """
    MAIN = "main"              # Main canal system block
    DISTRIBUTION = "distribution"  # Distribution block
    TERMINAL = "terminal"      # Terminal block (fields)
    
    def __str__(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        """Get detailed description of the block type."""
        descriptions = {
            BlockType.MAIN: "Main canal system block",
            BlockType.DISTRIBUTION: "Distribution zone block",
            BlockType.TERMINAL: "Field group terminal block"
        }
        return descriptions[self]
    
    @classmethod
    def get_parent_type(cls, block_type: 'BlockType') -> Optional['BlockType']:
        """Get the possible parent block type.
        
        Note: This is a guide, not a strict rule as levels are dynamic.
        
        Args:
            block_type: Current block type
            
        Returns:
            Possible parent block type or None if at highest level
        """
        if block_type == cls.TERMINAL:
            return cls.DISTRIBUTION
        elif block_type == cls.DISTRIBUTION:
            return cls.DISTRIBUTION  # Can connect to another distribution block
        return None
    
    @classmethod
    def get_child_type(cls, block_type: 'BlockType') -> Optional['BlockType']:
        """Get the possible child block type.
        
        Note: This is a guide, not a strict rule as levels are dynamic.
        
        Args:
            block_type: Current block type
            
        Returns:
            Possible child block type or None if at lowest level
        """
        if block_type == cls.MAIN:
            return cls.DISTRIBUTION
        elif block_type == cls.DISTRIBUTION:
            return cls.TERMINAL
        return None