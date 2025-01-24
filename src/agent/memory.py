from typing import Dict, List
import json
from datetime import datetime

class Memory:
    def __init__(self):
        self.short_term = []
        self.long_term = {}
        self.MAX_SHORT_TERM = 100
        
    def add_interaction(self, interaction: Dict):
        """Add new interaction to memory"""
        self.short_term.append({
            'timestamp': datetime.now().isoformat(),
            'interaction': interaction
        })
        
        if len(self.short_term) > self.MAX_SHORT_TERM:
            self._consolidate_memory()
            
    def _consolidate_memory(self):
        """Move short term memories to long term storage"""
        # Process short term memories and create summaries
        # Store in long term memory
        pass 