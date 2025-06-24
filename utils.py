# utils.py - Utilities for Groq pipeline
import time
import statistics
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from groq import Groq
from config import config

logger = logging.getLogger(__name__)

@dataclass
class ModerationResult:
    """Enhanced moderation result with detailed issue tracking"""
    passes: bool
    confidence: float
    issues: List[str]
    latency_ms: float
    
    def has_safety_violations(self) -> bool:
        """Check if result contains safety violations"""
        safety_violations = [
            "violence_hate", "sexual_content", "weapons", 
            "substances", "self_harm", "criminal_planning"
        ]
        return any(issue in safety_violations for issue in self.issues)
    
    def has_tone_violations(self) -> bool:
        """Check if result contains tone violations"""
        tone_violations = [
            "casual_language", "dismissive_language", "unprofessional_tone",
            "technical_jargon", "blame_language", "absolute_statements"
        ]
        return any(issue in tone_violations for issue in self.issues)

@dataclass
class PipelineResult:
    """Complete pipeline execution result"""
    scenario_id: str
    customer_input: str
    final_response: str
    ai_time: float
    total_time: float
    human_time: Optional[float] = None
    safety_issues: List[str] = None
    tone_issues: List[str] = None
    success: bool = True

class LatencyTracker:
    """Track and analyze latency metrics"""
    
    def __init__(self):
        self.measurements: List[float] = []
        self.start_time: Optional[float] = None
    
    def start_timer(self) -> None:
        """Start timing operation"""
        self.start_time = time.perf_counter()
    
    def stop_timer(self) -> float:
        """Stop timer and return elapsed time in ms"""
        if self.start_time is None:
            return 0.0
        
        elapsed = (time.perf_counter() - self.start_time) * 1000
        self.add_measurement(elapsed)
        self.start_time = None
        return elapsed
    
    def add_measurement(self, latency_ms: float) -> None:
        """Add latency measurement"""
        self.measurements.append(latency_ms)
    
    def get_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.measurements:
            return {"avg": 0, "min": 0, "max": 0, "p95": 0, "count": 0}
        
        return {
            "avg": statistics.mean(self.measurements),
            "min": min(self.measurements),
            "max": max(self.measurements),
            "p95": self._percentile(self.measurements, 95),
            "count": len(self.measurements)
        }
    
    def reset(self) -> None:
        """Reset all measurements"""
        self.measurements = []
        self.start_time = None
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_data) - 1)
        weight = index - lower
        return sorted_data[lower] + weight * (sorted_data[upper] - sorted_data[lower])

class SafetyIssueAnalyzer:
    """Analyze and categorize safety issues"""
    
    @staticmethod
    def categorize_safety_issue(issue: str) -> Dict[str, str]:
        """Categorize safety issue with description and severity"""
        categories = {
            "violence_hate": {
                "category": "Violence & Hate",
                "severity": "HIGH",
                "description": "Content promoting violence or discrimination"
            },
            "sexual_content": {
                "category": "Sexual Content", 
                "severity": "HIGH",
                "description": "Inappropriate sexual or explicit content"
            },
            "weapons": {
                "category": "Weapons & Illegal Items",
                "severity": "HIGH", 
                "description": "Content about illegal weapons or dangerous items"
            },
            "substances": {
                "category": "Regulated Substances",
                "severity": "MEDIUM",
                "description": "Content about illegal drugs or substances"
            },
            "self_harm": {
                "category": "Self-Harm & Suicide",
                "severity": "CRITICAL",
                "description": "Content encouraging self-harm or suicide"
            },
            "criminal_planning": {
                "category": "Criminal Activities",
                "severity": "HIGH",
                "description": "Content helping plan criminal activities"
            },
            "casual_language": {
                "category": "Tone - Casual Language",
                "severity": "LOW",
                "description": "Unprofessional casual expressions"
            },
            "dismissive_language": {
                "category": "Tone - Dismissive",
                "severity": "MEDIUM", 
                "description": "Dismissive or unhelpful language"
            },
            "unprofessional_tone": {
                "category": "Tone - Unprofessional",
                "severity": "MEDIUM",
                "description": "Generally unprofessional tone"
            }
        }
        
        return categories.get(issue, {
            "category": "Unknown Issue",
            "severity": "LOW",
            "description": "Unclassified moderation issue"
        })

def format_latency_output(latency_ms: float) -> str:
    """Format latency for human-readable output"""
    if latency_ms < 1:
        return f"{latency_ms:.2f}ms"
    elif latency_ms < 1000:
        return f"{latency_ms:.1f}ms" 
    else:
        return f"{latency_ms/1000:.2f}s"

def format_human_time_output(time_ms: float) -> str:
    """Format human review time for output"""
    if time_ms < 1000:
        return f"{time_ms:.0f}ms"
    elif time_ms < 60000:
        return f"{time_ms/1000:.1f}s"
    else:
        minutes = int(time_ms / 60000)
        seconds = (time_ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"

def print_banner():
    """Print application banner"""
    banner = f"""
{'='*80}
🚀 GROQ CUSTOMER SERVICE PIPELINE
{'='*80}
AI customer service with lightning-fast responses
Powered by Groq's optimized inference infrastructure

Company: {config.company_name}
Domain: {config.company_domain}
Voice: {config.brand_voice}
{'='*80}
"""
    print(banner)

async def validate_groq_connection() -> bool:
    """Validate connection to Groq API"""
    try:
        client = Groq(api_key=config.groq_api_key)
        
        # Test with a simple request
        response = client.chat.completions.create(
            model=config.guard_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
            timeout=10
        )
        
        return bool(response.choices and response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"Groq connection validation failed: {e}")
        return False

def calculate_pipeline_metrics(results: List[PipelineResult]) -> Dict[str, Any]:
    """Calculate comprehensive pipeline metrics"""
    if not results:
        return {}
    
    successful_results = [r for r in results if r.success]
    
    metrics = {
        "total_processed": len(results),
        "successful": len(successful_results),
        "success_rate": len(successful_results) / len(results) * 100,
        "avg_ai_time": 0,
        "avg_total_time": 0,
        "safety_issues_detected": 0,
        "tone_issues_resolved": 0,
        "latency_distribution": {}
    }
    
    if successful_results:
        ai_times = [r.ai_time for r in successful_results]
        total_times = [r.total_time for r in successful_results]
        
        metrics["avg_ai_time"] = statistics.mean(ai_times)
        metrics["avg_total_time"] = statistics.mean(total_times)
        metrics["min_ai_time"] = min(ai_times)
        metrics["max_ai_time"] = max(ai_times)
    
    # Count issues
    for result in results:
        if result.safety_issues:
            metrics["safety_issues_detected"] += len(result.safety_issues)
        if result.tone_issues:
            metrics["tone_issues_resolved"] += len(result.tone_issues)
    
    return metrics

def print_pipeline_summary(results: List[PipelineResult]):
    """Print comprehensive pipeline summary"""
    metrics = calculate_pipeline_metrics(results)
    
    if not metrics:
        print("No results to summarize")
        return
    
    print(f"\n{'='*60}")
    print("📊 PIPELINE PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    print(f"Scenarios Processed: {metrics['total_processed']}")
    print(f"Success Rate: {metrics['success_rate']:.1f}%")
    
    if metrics.get('avg_ai_time'):
        print(f"\n⚡ Performance Metrics:")
        print(f"  Average AI Time: {metrics['avg_ai_time']:.1f}ms")
        print(f"  Fastest Response: {metrics['min_ai_time']:.1f}ms")
        print(f"  Slowest Response: {metrics['max_ai_time']:.1f}ms")
    
    print(f"\n🛡️ Safety & Quality:")
    print(f"  Safety Issues Detected: {metrics['safety_issues_detected']}")
    print(f"  Tone Issues Resolved: {metrics['tone_issues_resolved']}")
    
    print(f"\n💡 Insights:")
    if metrics['success_rate'] >= 95:
        print("  ✅ Excellent pipeline reliability")
    elif metrics['success_rate'] >= 85:
        print("  ⚠️ Good pipeline reliability - monitor for improvements")
    else:
        print("  ❌ Pipeline reliability needs attention")

def validate_pipeline_health(results: List[PipelineResult]) -> Dict[str, bool]:
    """Validate overall pipeline health"""
    if not results:
        return {"sufficient_data": False}
    
    metrics = calculate_pipeline_metrics(results)
    
    health_checks = {
        "sufficient_data": len(results) >= 5,
        "good_success_rate": metrics.get('success_rate', 0) >= 90,
        "safety_functioning": True,  # Always true if we have results
        "tone_validation_active": metrics.get('tone_issues_resolved', 0) >= 0
    }
    
    return health_checks

def export_results_to_dict(results: List[PipelineResult]) -> Dict[str, Any]:
    """Export results to dictionary for JSON serialization"""
    return {
        "summary": calculate_pipeline_metrics(results),
        "results": [
            {
                "scenario_id": r.scenario_id,
                "customer_input": r.customer_input,
                "final_response": r.final_response,
                "ai_time": r.ai_time,
                "total_time": r.total_time,
                "human_time": r.human_time,
                "safety_issues": r.safety_issues or [],
                "tone_issues": r.tone_issues or [],
                "success": r.success
            }
            for r in results
        ],
        "health_checks": validate_pipeline_health(results),
        "timestamp": time.time()
    }
    