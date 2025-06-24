# tone_agent.py - Groq tone validation
import time
import logging
from typing import List, Tuple
from base import BaseAgent
from config import config, get_tone_validation_prompt
from utils import ModerationResult

logger = logging.getLogger(__name__)

class ToneAgent(BaseAgent):
    """Professional tone validation for customer service responses using Groq"""
    
    def __init__(self, company_name: str = None, domain: str = None):
        super().__init__()
        self.model = config.tone_model
        self.company_name = company_name or config.company_name
        self.domain = domain or config.company_domain
        self.tone_prompt = get_tone_validation_prompt(company_name, domain)
        
        logger.info(f"Initialized ToneAgent for {self.company_name} {self.domain}")
        
        # Enhanced customer service tone standards
        self.tone_standards = f"""
You are validating customer service responses for {self.company_name}'s professional tone compliance.

CRITICAL REQUIREMENTS - Response must be:
✓ Empathetic and understanding
✓ Professional but warm
✓ Solution-focused
✓ Clear and helpful

AUTOMATIC FAILURES - Flag as FAIL if response contains:
❌ Casual expressions: "ASAP", "totally", "screwed up", "weird", "guys", "yeah", "nope"
❌ Dismissive language: "can't do anything", "not our problem", "that's impossible"
❌ Unprofessional urgency: "immediately", "right now", "hurry up"
❌ Inappropriate emotions: "frustrated", "annoyed", "angry"
❌ Technical jargon without explanation
❌ Blame language: "you should have", "you didn't", "your fault"
❌ Absolute statements: "never", "always", "impossible" (without solution)

CUSTOMER SERVICE EXCELLENCE:
✓ Use "I understand" or "I can see why" for empathy
✓ Offer specific next steps or solutions
✓ Use "we'll work to resolve this" for ownership
✓ Provide timelines when possible
✓ Thank customers for their patience/business

RESPONSE FORMAT:
- PASS: if tone meets all professional standards
- FAIL: [specific_issue] if tone has problems

Examples:
"Thanks for reaching out, we'll get back to you ASAP!" → FAIL: casual_language
"I understand your concern about the delay." → PASS
"That's totally screwed up, sorry!" → FAIL: unprofessional_tone, casual_language
"We sincerely apologize and will resolve this promptly." → PASS
"""
    
    async def validate_tone(self, content: str) -> Tuple[ModerationResult, float]:
        """Validate customer service tone and professionalism"""
        start = time.perf_counter()
        
        try:
            logger.debug(f"Validating tone for: {content[:50]}...")
            
            response = await self._groq_tone_validation(content)
            latency = self._track_latency(start)
            
            # Parse tone validation response
            passes, issues = self._parse_tone_response(response)
            
            result = ModerationResult(
                passes=passes,
                confidence=0.90,
                issues=issues,
                latency_ms=latency
            )
            
            logger.info(f"Tone validation {'PASSED' if passes else 'FAILED'} in {latency:.1f}ms")
            if not passes:
                logger.warning(f"Tone issues detected: {issues}")
            
            return result, latency
            
        except Exception as e:
            latency = self._track_latency(start)
            logger.error(f"Tone validation failed: {e}")
            
            # Return pass on error to avoid blocking pipeline
            return ModerationResult(
                passes=True,
                confidence=0.0,
                issues=["tone_validation_error"],
                latency_ms=latency
            ), latency
    
    async def _groq_tone_validation(self, content: str) -> str:
        """Use Scout for tone validation"""
        return await self._make_groq_request(
            model=self.model,
            messages=[
                {"role": "system", "content": self.tone_standards},
                {"role": "user", "content": f"Validate this customer service response:\n\n{content}"}
            ],
            max_tokens=config.max_tokens_tone
        )
    
    def _parse_tone_response(self, response: str) -> Tuple[bool, List[str]]:
        """Parse tone validation response"""
        response_clean = response.strip().upper()
        
        if "FAIL" in response_clean:
            issues = []
            
            # Map specific tone issues
            issue_patterns = {
                "CASUAL": "casual_language",
                "DISMISSIVE": "dismissive_language", 
                "UNPROFESSIONAL": "unprofessional_tone",
                "JARGON": "technical_jargon",
                "BLAME": "blame_language",
                "ABSOLUTE": "absolute_statements",
                "INAPPROPRIATE": "inappropriate_language",
                "URGENCY": "inappropriate_urgency",
                "EMOTION": "inappropriate_emotions"
            }
            
            # Extract specific issues from response
            for pattern, issue_code in issue_patterns.items():
                if pattern in response_clean:
                    issues.append(issue_code)
            
            # Fallback generic issue
            if not issues:
                issues = ["tone_violation"]
                
            return False, issues
        
        return True, []
    
    def get_improvement_suggestions(self, issues: List[str]) -> List[str]:
        """Get specific improvement suggestions based on identified issues"""
        suggestions = {
            "casual_language": "Replace casual expressions with professional alternatives",
            "dismissive_language": "Use more empathetic and solution-focused language",
            "unprofessional_tone": "Adopt a more professional and respectful tone",
            "technical_jargon": "Explain technical terms in customer-friendly language",
            "blame_language": "Focus on solutions rather than blame",
            "absolute_statements": "Provide alternative solutions or workarounds",
            "inappropriate_language": "Use appropriate business communication language",
            "inappropriate_urgency": "Use professional urgency language",
            "inappropriate_emotions": "Maintain professional emotional tone"
        }
        
        return [suggestions.get(issue, "Improve overall professionalism") for issue in issues]
    
    async def validate_multiple_responses(self, contents: List[str]) -> List[Tuple[ModerationResult, float]]:
        """Validate tone for multiple responses"""
        logger.info(f"Validating tone for {len(contents)} responses")
        
        results = []
        for i, content in enumerate(contents):
            logger.debug(f"Validating response {i+1}/{len(contents)}")
            result = await self.validate_tone(content)
            results.append(result)
        
        return results
    
    def get_tone_summary(self, results: List[ModerationResult]) -> dict:
        """Get summary statistics for tone validation"""
        total = len(results)
        passed = sum(1 for r in results if r.passes)
        failed = total - passed
        
        avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0
        
        # Count issue types
        issue_counts = {}
        for result in results:
            for issue in result.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_latency_ms": avg_latency,
            "common_issues": dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def update_standards(self, company_name: str = None, domain: str = None):
        """Update tone validation standards"""
        if company_name:
            self.company_name = company_name
        if domain:
            self.domain = domain
        
        self.tone_prompt = get_tone_validation_prompt(self.company_name, self.domain)
        logger.info(f"Updated tone standards for {self.company_name} {self.domain}")
    
    def analyze_tone_patterns(self, contents: List[str], results: List[ModerationResult]) -> dict:
        """Analyze patterns in tone validation results"""
        if len(contents) != len(results):
            logger.error("Mismatched contents and results for pattern analysis")
            return {}
        
        patterns = {
            "avg_response_length": sum(len(c) for c in contents) / len(contents),
            "failure_rate_by_length": {},
            "common_fail_phrases": []
        }
        
        # Analyze failure rate by response length
        short_responses = [(c, r) for c, r in zip(contents, results) if len(c) < 100]
        medium_responses = [(c, r) for c, r in zip(contents, results) if 100 <= len(c) < 300]
        long_responses = [(c, r) for c, r in zip(contents, results) if len(c) >= 300]
        
        for category, responses in [("short", short_responses), ("medium", medium_responses), ("long", long_responses)]:
            if responses:
                failed = sum(1 for _, r in responses if not r.passes)
                patterns["failure_rate_by_length"][category] = failed / len(responses)
        
        return patterns