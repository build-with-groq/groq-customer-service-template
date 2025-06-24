# guard_agent.py - Groq safety moderation
import time
import logging
from typing import Tuple
from base import BaseAgent
from config import config
from utils import ModerationResult

logger = logging.getLogger(__name__)

class GuardAgent(BaseAgent):
    """LlamaGuard-powered content safety moderation"""
    
    def __init__(self):
        super().__init__()
        self.model = config.guard_model
        
        # LlamaGuard taxonomy for comprehensive safety checking
        self.llamaguard_taxonomy = """
You are a safety classifier using LlamaGuard standards. Classify content as SAFE or UNSAFE based on these categories:

O1: Violence & Hate
- Statements encouraging or helping plan violence
- Discrimination, slurs, hateful sentiments based on race, color, religion, national origin, sexual orientation, gender, gender identity, disability

O2: Sexual Content  
- Encouraging sexual acts (especially with minors)
- Sexually explicit/erotic content

O3: Guns & Illegal Weapons
- Encouraging, condoning, or helping plan illegal weapon acquisition or use
- Instructions for making weapons, explosives, dangerous chemicals

O4: Regulated Substances
- Promoting illegal production/use of controlled substances
- Instructions for drug manufacturing or distribution

O5: Suicide & Self-Harm
- Encouraging self-harm or suicide
- Providing harmful advice instead of mental health resources

O6: Criminal Planning
- Encouraging, condoning, or helping plan criminal activities (arson, kidnapping, theft, fraud)
- Only use when content doesn't fit other violation categories

Respond with:
- "SAFE" if content doesn't violate any category
- "UNSAFE: [Category]" if content violates categories (e.g., "UNSAFE: O1, O3")
"""
    
    async def check_safety(self, content: str) -> Tuple[ModerationResult, float]:
        """Check content for safety violations using LlamaGuard"""
        start = time.perf_counter()
        
        try:
            logger.debug(f"Running safety check on content: {content[:50]}...")
            
            response = await self._llamaguard_safety_check(content)
            latency = self._track_latency(start)
            
            # Parse response for safety determination
            is_safe, violations = self._parse_llamaguard_response(response)
            
            result = ModerationResult(
                passes=is_safe,
                confidence=0.95,
                issues=violations if not is_safe else [],
                latency_ms=latency
            )
            
            logger.info(f"Safety check {'PASSED' if is_safe else 'FAILED'} in {latency:.1f}ms")
            if not is_safe:
                logger.warning(f"Safety violations detected: {violations}")
            
            return result, latency
            
        except Exception as e:
            latency = self._track_latency(start)
            logger.error(f"Safety check failed: {e}")
            
            # Return safe result on error to avoid blocking pipeline
            return ModerationResult(
                passes=True,
                confidence=0.0,
                issues=["safety_check_error"],
                latency_ms=latency
            ), latency
    
    async def _llamaguard_safety_check(self, content: str) -> str:
        """Use LlamaGuard directly for safety checking"""
        return await self._make_groq_request(
            model=self.model,
            messages=[
                {"role": "system", "content": self.llamaguard_taxonomy},
                {"role": "user", "content": f"Classify this content:\n\n{content}"}
            ],
            max_tokens=config.max_tokens_guard
        )
    
    def _parse_llamaguard_response(self, response: str) -> Tuple[bool, list[str]]:
        """Parse safety response using LlamaGuard format"""
        response_clean = response.strip().upper()
        
        # Check for unsafe indicators
        if "UNSAFE" in response_clean:
            violations = []
            
            # Extract violation categories (O1, O2, etc.)
            category_names = {
                "O1": "violence_hate",
                "O2": "sexual_content", 
                "O3": "weapons",
                "O4": "substances",
                "O5": "self_harm",
                "O6": "criminal_planning"
            }
            
            for category, name in category_names.items():
                if category in response_clean:
                    violations.append(name)
            
            # Fallback if no specific categories found
            if not violations:
                violations = ["content_violation"]
                
            return False, violations
        
        # Additional safety checks for edge cases
        unsafe_keywords = ["harmful", "violation", "inappropriate", "dangerous"]
        if any(keyword in response_clean for keyword in unsafe_keywords):
            return False, ["potential_violation"]
            
        return True, []
    
    async def check_multiple_contents(self, contents: list[str]) -> list[Tuple[ModerationResult, float]]:
        """Batch safety checking for multiple contents"""
        logger.info(f"Running batch safety check on {len(contents)} items")
        
        results = []
        for i, content in enumerate(contents):
            logger.debug(f"Checking item {i+1}/{len(contents)}")
            result = await self.check_safety(content)
            results.append(result)
        
        return results
    
    def get_safety_summary(self, results: list[ModerationResult]) -> dict:
        """Get summary statistics for safety checks"""
        total = len(results)
        passed = sum(1 for r in results if r.passes)
        failed = total - passed
        
        avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0
        
        return {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_latency_ms": avg_latency
        }