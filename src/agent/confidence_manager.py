from typing import Dict
import numpy as np

class ConfidenceManager:
    def __init__(self):
        self.SPEAK_THRESHOLD = 0.7
        self.confidence_score = 0.0
        self.context_understanding = 0.0
        self.topic_relevance = 0.0
        
    def update_confidence(self, space_data: Dict, thoughts: str) -> float:
        """
        Update confidence based on space context and thoughts
        Returns current confidence level
        """
        # Update understanding of context
        self.context_understanding = min(
            self.context_understanding + 0.1,
            1.0
        )
        
        # Assess topic relevance
        topic_keywords = self._extract_keywords(space_data)
        self.topic_relevance = self._calculate_topic_relevance(topic_keywords)
        
        # Calculate overall confidence
        self.confidence_score = np.mean([
            self.context_understanding,
            self.topic_relevance
        ])
        
        return self.confidence_score 