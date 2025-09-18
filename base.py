# base.py - Groq base agent
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from groq import Groq
from config import config
from utils import LatencyTracker

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all Groq agents"""
    
    def __init__(self):
        self.client = Groq(
            api_key="",
            base_url="https://demo-proxy.groqcloud.dev",
            default_headers={"Origin": f"https://groq-customer-service-template.vercel.groqcloud.net"}
        )
        self.metrics = LatencyTracker()
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        self.request_timeout = config.request_timeout
    
    async def _make_groq_request(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        max_tokens: int = 200,
        temperature: float = 0.1
    ) -> str:
        """Make robust request to Groq API with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making Groq request to {model} (attempt {attempt + 1})")
                
                # Make the API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=self.request_timeout
                )
                
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty response from Groq API")
                
                content = response.choices[0].message.content.strip()
                logger.debug(f"Groq request successful: {len(content)} characters")
                return content
                
            except Exception as e:
                logger.warning(f"Groq request attempt {attempt + 1} failed: {e}")
                
                if attempt == self.max_retries - 1:
                    logger.error(f"All {self.max_retries} attempts failed for model {model}")
                    raise Exception(f"Groq API request failed after {self.max_retries} attempts: {e}")
                
                # Wait before retry with exponential backoff
                wait_time = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    
    def _track_latency(self, start_time: float) -> float:
        """Calculate and track latency with logging"""
        latency = (time.perf_counter() - start_time) * 1000
        self.metrics.add_measurement(latency)
        
        return latency
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics for this agent"""
        return self.metrics.get_stats()
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.metrics = LatencyTracker()
        logger.info(f"Metrics reset for {self.__class__.__name__}")
    
    async def health_check(self) -> bool:
        """Perform health check on the Groq connection"""
        try:
            test_response = await self._make_groq_request(
                model=config.guard_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            logger.info("Groq health check passed")
            return True
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False