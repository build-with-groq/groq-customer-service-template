# rewrite_agent.py - Groq content rewriting
import time
import logging
from typing import List, Tuple
from base import BaseAgent
from config import config, get_rewrite_prompt

logger = logging.getLogger(__name__)

class RewriteAgent(BaseAgent):
    """Professional content rewriting using Groq"""
    
    def __init__(self, company_name: str = None, domain: str = None):
        super().__init__()
        self.model = config.rewrite_model
        self.company_name = company_name or config.company_name
        self.domain = domain or config.company_domain
        self.rewrite_prompt = get_rewrite_prompt(company_name, domain)
        
        logger.info(f"Initialized RewriteAgent for {self.company_name} {self.domain}")
    
    async def rewrite_professional(self, content: str, issues: List[str] = None) -> Tuple[str, float]:
        """Rewrite content to match professional standards"""
        start = time.perf_counter()
        
        try:
            logger.debug(f"Rewriting content: {content[:50]}... (issues: {issues})")
            
            # Prepare enhanced prompt with specific issues
            enhanced_prompt = self.rewrite_prompt
            if issues:
                issue_context = self._format_issue_context(issues)
                enhanced_prompt += issue_context
            
            response = await self._make_groq_request(
                model=self.model,
                messages=[
                    {"role": "system", "content": enhanced_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=config.max_tokens_rewrite,
                temperature=0.2  # Slightly higher for creative rewriting
            )
            
            latency = self._track_latency(start)
            
            # Clean and validate rewritten content
            rewritten = self._clean_rewrite(response, content)
            
            logger.info(f"Content rewritten successfully in {latency:.1f}ms")
            logger.debug(f"Original: {len(content)} chars -> Rewritten: {len(rewritten)} chars")
            
            return rewritten, latency
            
        except Exception as e:
            latency = self._track_latency(start)
            logger.error(f"Content rewriting failed: {e}")
            
            # Return original content on error - let the AI model handle improvements
            return content, latency
    
    def _format_issue_context(self, issues: List[str]) -> str:
        """Format issues into actionable context for rewriting"""
        if not issues:
            return ""
        
        issue_descriptions = {
            "casual_language": "Replace casual expressions with professional language",
            "unprofessional_tone": "Use more empathetic and professional tone", 
            "inappropriate_urgency": "Replace urgent slang with professional alternatives",
            "inappropriate_language": "Remove colloquial or inappropriate expressions",
            "dismissive_language": "Make language more helpful and solution-focused",
            "blame_language": "Remove blame and focus on solutions",
            "technical_jargon": "Simplify technical terms for customer understanding",
            "absolute_statements": "Soften absolute statements and provide alternatives",
            "inappropriate_emotions": "Maintain professional emotional tone"
        }
        
        formatted_issues = []
        for issue in issues:
            if issue in issue_descriptions:
                formatted_issues.append(issue_descriptions[issue])
        
        if formatted_issues:
            context = f"\n\nSPECIFIC IMPROVEMENTS NEEDED:\n" + "\n".join(f"- {issue}" for issue in formatted_issues)
            return context
        
        return ""
    
    def _clean_rewrite(self, rewritten: str, original: str) -> str:
        """Clean and validate the rewritten content"""
        cleaned = rewritten.strip()
        
        # Ensure rewrite isn't too short
        if len(cleaned) < 20:
            logger.warning("Rewrite too short, returning original")
            return original
        
        # Check if rewrite is identical to original (no improvement attempted)
        if cleaned.strip() == original.strip():
            logger.info("Rewrite identical to original - AI determined no changes needed")
            return original
        
        return cleaned
    
    async def rewrite_multiple_contents(
        self, 
        contents: List[str], 
        issues_list: List[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """Rewrite multiple contents"""
        logger.info(f"Rewriting {len(contents)} contents")
        
        results = []
        issues_list = issues_list or [None] * len(contents)
        
        for i, (content, issues) in enumerate(zip(contents, issues_list)):
            logger.debug(f"Rewriting content {i+1}/{len(contents)}")
            result = await self.rewrite_professional(content, issues)
            results.append(result)
        
        return results
    
    def analyze_rewrite_quality(self, originals: List[str], rewrites: List[str]) -> dict:
        """Analyze the quality of rewrites"""
        if len(originals) != len(rewrites):
            logger.error("Mismatched original and rewrite lists")
            return {}
        
        analysis = {
            "total_rewrites": len(rewrites),
            "avg_length_change": 0,
            "improvement_rate": 0,
            "changes_made": 0
        }
        
        length_changes = []
        changes_made = 0
        
        for orig, rewrite in zip(originals, rewrites):
            # Calculate length change
            length_change = len(rewrite) - len(orig)
            length_changes.append(length_change)
            
            # Count actual changes made
            if orig.strip() != rewrite.strip():
                changes_made += 1
        
        analysis["avg_length_change"] = sum(length_changes) / len(length_changes)
        analysis["changes_made"] = changes_made
        analysis["change_rate"] = changes_made / len(rewrites)
        
        return analysis
    
    def get_rewrite_stats(self, rewrites: List[str], latencies: List[float]) -> dict:
        """Get statistics about rewrite operations"""
        if not rewrites:
            return {}
        
        lengths = [len(r) for r in rewrites]
        word_counts = [len(r.split()) for r in rewrites]
        
        return {
            "total_rewrites": len(rewrites),
            "avg_length": sum(lengths) / len(lengths),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_length": min(lengths),
            "max_length": max(lengths)
        }
    
    def update_prompt(self, company_name: str = None, domain: str = None):
        """Update the rewrite prompt"""
        if company_name:
            self.company_name = company_name
        if domain:
            self.domain = domain
        
        self.rewrite_prompt = get_rewrite_prompt(self.company_name, self.domain)
        logger.info(f"Updated rewrite prompt for {self.company_name} {self.domain}")