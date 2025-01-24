from datetime import datetime, timedelta
import psutil
import asyncio
from typing import Dict


class HealthMonitor:
    def __init__(self, bob_instance):
        self.bob = bob_instance
        self.last_processed = {}
        self.health_metrics = {}
        
    async def monitor_streams(self):
        """Monitor health of all cognitive streams"""
        while True:
            try:
                metrics = {
                    "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,
                    "cpu_usage": psutil.Process().cpu_percent(),
                    "queue_sizes": {
                        "thought": self.bob.cognitive_streams.thought_queue.qsize(),
                        "speech": self.bob.cognitive_streams.speech_queue.qsize()
                    },
                    "stream_health": self._check_stream_health()
                }
                
                self.health_metrics = metrics
                
                # Alert if any metrics are concerning
                await self._check_alerts(metrics)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    def _check_stream_health(self) -> Dict:
        """Check health of each stream"""
        return {
            "listening": self._is_stream_healthy("listening"),
            "thinking": self._is_stream_healthy("thinking"),
            "speaking": self._is_stream_healthy("speaking"),
            "memory": self._is_stream_healthy("memory")
        } 