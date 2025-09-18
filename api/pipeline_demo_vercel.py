# pipeline_demo_vercel.py - Vercel-compatible Groq Customer Service Pipeline
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guard_agent import GuardAgent
from tone_agent import ToneAgent
from response_agent import ResponseAgent
from rewrite_agent import RewriteAgent
from utils import PipelineResult, LatencyTracker
from config import config

logger = logging.getLogger(__name__)

class GroqCustomerServiceDemo:
    """Vercel-compatible Groq customer service pipeline demo"""

    def __init__(self, company_name: str = None, domain: str = None):
        self.company_name = company_name or config.company_name
        self.domain = domain or config.company_domain

        # Initialize Groq agents
        self.guard_agent = GuardAgent()
        self.response_agent = ResponseAgent(company_name, domain)
        self.tone_agent = ToneAgent(company_name, domain)
        self.rewrite_agent = RewriteAgent(company_name, domain)

        # Performance tracking
        self.pipeline_tracker = LatencyTracker()
        self.results_history: List[PipelineResult] = []

        logger.info(f"Initialized GroqCustomerServiceDemo for {self.company_name} {self.domain}")

    async def process_single_scenario(
        self,
        customer_input: str,
        scenario_id: str = None,
        context: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Process a single customer service scenario through the complete pipeline"""

        scenario_id = scenario_id or f"scenario_{int(time.time())}"
        pipeline_start = time.perf_counter()

        logger.info(f"Processing scenario {scenario_id}: {customer_input[:50]}...")

        try:
            # Phase 1: Initial Safety Check
            logger.debug("Phase 1: Initial safety check")
            safety_result, guard1_time = await self.guard_agent.check_safety(customer_input)

            if not safety_result.passes:
                logger.warning(f"Initial safety check failed: {safety_result.issues}")
                return self._create_failed_result(
                    scenario_id, customer_input, "Initial safety check failed",
                    safety_issues=safety_result.issues
                )

            # Phase 2: AI Response Generation
            logger.debug("Phase 2: AI response generation")
            ai_response, response_time = await self.response_agent.generate_response(
                customer_input, context
            )

            # Phase 3: Human Review (simplified for Vercel - would use external queue)
            human_time = 0
            final_response = ai_response

            # Skip human review in Vercel version for now
            # In production, this would integrate with external queue/database

            # Phase 4: Final Safety Check
            logger.debug("Phase 4: Final safety check")
            final_safety, guard2_time = await self.guard_agent.check_safety(final_response)

            if not final_safety.passes:
                logger.warning(f"Final safety check failed: {final_safety.issues}")

                return self._create_failed_result(
                    scenario_id, customer_input, "Final safety check failed",
                    safety_issues=final_safety.issues
                )

            # Phase 5: Tone Validation
            logger.debug("Phase 5: Tone validation")
            tone_result, tone_time = await self.tone_agent.validate_tone(final_response)

            # Phase 6: Conditional Rewrite
            rewrite_time = 0
            original_tone_issues = []  # Track original issues that triggered rewrite

            if not tone_result.passes:
                original_tone_issues = tone_result.issues.copy()  # Preserve original issues
                logger.debug("Phase 6: Content rewrite (tone issues detected)")
                final_response, rewrite_time = await self.rewrite_agent.rewrite_professional(
                    final_response, tone_result.issues
                )

                # Final tone check after rewrite
                final_tone_result, final_tone_time = await self.tone_agent.validate_tone(final_response)
                rewrite_time += final_tone_time

                if not final_tone_result.passes:
                    logger.warning(f"Tone issues persist after rewrite: {final_tone_result.issues}")

            # Calculate metrics
            total_time = (time.perf_counter() - pipeline_start) * 1000
            ai_time = guard1_time + response_time + guard2_time + tone_time + rewrite_time

            # Create result
            result = PipelineResult(
                scenario_id=str(scenario_id),
                customer_input=customer_input,
                final_response=final_response,
                ai_time=ai_time,
                total_time=total_time,
                human_time=human_time if human_time > 0 else None,
                safety_issues=safety_result.issues if not safety_result.passes else [],
                tone_issues=original_tone_issues,  # Use original issues that triggered rewrite
                success=True
            )

            # Store result
            self.results_history.append(result)
            self.pipeline_tracker.add_measurement(total_time)

            logger.info(f"Scenario {scenario_id} completed successfully in {total_time:.1f}ms")

            return asdict(result)

        except Exception as e:
            logger.error(f"Scenario {scenario_id} processing failed: {e}")
            return self._create_failed_result(scenario_id, customer_input, str(e))

    async def process_single_scenario_with_tracking(
        self,
        customer_input: str,
        scenario_id: str,
        tracker,  # AppState instance for tracking
        context: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Process a single customer service scenario with detailed pipeline tracking"""

        pipeline_start = time.perf_counter()

        logger.info(f"Processing scenario {scenario_id} with tracking: {customer_input[:50]}...")

        try:
            # Phase 1: Initial Safety Check
            tracker.track_pipeline_step(scenario_id, "safety_check", "Checking customer input for safety violations", config.guard_model)

            safety_result, guard1_time = await self.guard_agent.check_safety(customer_input)

            if not safety_result.passes:
                tracker.complete_pipeline_step(scenario_id, f"Safety check FAILED: {', '.join(safety_result.issues)}", "failed")
                logger.warning(f"Initial safety check failed: {safety_result.issues}")
                return self._create_failed_result(
                    scenario_id, customer_input, "Initial safety check failed",
                    safety_issues=safety_result.issues
                )

            tracker.complete_pipeline_step(scenario_id, f"Safety check PASSED in {guard1_time:.1f}ms")

            # Phase 2: AI Response Generation
            tracker.track_pipeline_step(scenario_id, "response_generation", "Generating professional customer service response", config.response_model)

            ai_response, response_time = await self.response_agent.generate_response(customer_input, context)

            tracker.complete_pipeline_step(scenario_id, f"Response generated ({len(ai_response)} chars) in {response_time:.1f}ms")

            # Phase 3: Human Review (if enabled)
            human_time = 0
            final_response = ai_response

            if config.human_review_timeout > 0:
                tracker.track_pipeline_step(scenario_id, "human_review", "Waiting for human review and approval")

                human_start = time.perf_counter()

                try:
                    # Request human review with timeout using the app state
                    human_result = await self._request_review_via_tracker(tracker, customer_input, ai_response, config.human_review_timeout)

                    human_time = (time.perf_counter() - human_start) * 1000
                    final_response = human_result.edited_response

                    changes_made = len(final_response) != len(ai_response) or final_response != ai_response
                    tracker.complete_pipeline_step(
                        scenario_id,
                        f"Human review completed in {human_time:.1f}ms - {'Changes made' if changes_made else 'No changes'}"
                    )

                    logger.info(f"Human review completed in {human_time:.1f}ms")

                except asyncio.TimeoutError:
                    logger.warning("Human review timed out, using AI response")
                    human_time = config.human_review_timeout * 1000
                    tracker.complete_pipeline_step(scenario_id, f"Human review TIMED OUT after {config.human_review_timeout}s - using original response")
            else:
                # Skip human review
                tracker.track_pipeline_step(scenario_id, "human_review", "Human review disabled - skipping")
                tracker.complete_pipeline_step(scenario_id, "Human review skipped (disabled in config)")

            # Phase 4: Final Safety Check
            tracker.track_pipeline_step(scenario_id, "final_safety", "Final safety check on approved response", config.guard_model)

            final_safety, guard2_time = await self.guard_agent.check_safety(final_response)

            if not final_safety.passes:
                logger.warning(f"Final safety check failed: {final_safety.issues}")
                tracker.complete_pipeline_step(scenario_id, f"Final safety check FAILED: {', '.join(final_safety.issues)}")

                tracker.complete_pipeline_step(scenario_id, "Safety fixes failed - pipeline terminated", "failed")
                return self._create_failed_result(
                    scenario_id, customer_input, "Final safety check failed",
                    safety_issues=final_safety.issues
                )

            else:
                tracker.complete_pipeline_step(scenario_id, f"Final safety check PASSED in {guard2_time:.1f}ms")

            # Phase 5: Tone Validation
            tracker.track_pipeline_step(scenario_id, "tone_validation", "Validating professional tone and language", config.tone_model)

            tone_result, tone_time = await self.tone_agent.validate_tone(final_response)

            # Phase 6: Conditional Rewrite
            rewrite_time = 0
            original_tone_issues = []  # Track original issues that triggered rewrite

            if not tone_result.passes:
                original_tone_issues = tone_result.issues.copy()  # Preserve original issues
                tracker.complete_pipeline_step(scenario_id, f"Tone validation FAILED: {', '.join(tone_result.issues)}")
                tracker.track_pipeline_step(scenario_id, "content_rewrite", "Rewriting content to improve professional tone", config.rewrite_model)

                final_response, rewrite_time = await self.rewrite_agent.rewrite_professional(
                    final_response, tone_result.issues
                )

                # Final tone check after rewrite
                final_tone_result, final_tone_time = await self.tone_agent.validate_tone(final_response)
                rewrite_time += final_tone_time

                if not final_tone_result.passes:
                    logger.warning(f"Tone issues persist after rewrite: {final_tone_result.issues}")
                    tracker.complete_pipeline_step(scenario_id, f"Content rewritten in {rewrite_time:.1f}ms - some tone issues persist")
                else:
                    tracker.complete_pipeline_step(scenario_id, f"Content successfully rewritten in {rewrite_time:.1f}ms")
            else:
                tracker.complete_pipeline_step(scenario_id, f"Tone validation PASSED in {tone_time:.1f}ms")

            # Calculate metrics
            total_time = (time.perf_counter() - pipeline_start) * 1000
            ai_time = guard1_time + response_time + guard2_time + tone_time + rewrite_time

            # Create result
            result = PipelineResult(
                scenario_id=str(scenario_id),
                customer_input=customer_input,
                final_response=final_response,
                ai_time=ai_time,
                total_time=total_time,
                human_time=human_time if human_time > 0 else None,
                safety_issues=safety_result.issues if not safety_result.passes else [],
                tone_issues=original_tone_issues,  # Use original issues that triggered rewrite
                success=True
            )

            # Store result
            self.results_history.append(result)
            self.pipeline_tracker.add_measurement(total_time)

            # Mark pipeline as complete
            tracker.complete_pipeline(scenario_id)

            logger.info(f"Scenario {scenario_id} completed successfully in {total_time:.1f}ms")

            return asdict(result)

        except Exception as e:
            logger.error(f"Scenario {scenario_id} processing failed: {e}")
            if 'tracker' in locals():
                tracker.complete_pipeline_step(scenario_id, f"Pipeline FAILED: {str(e)}", "failed")
                tracker.complete_pipeline(scenario_id)
            return self._create_failed_result(scenario_id, customer_input, str(e))

    async def _request_review_via_tracker(self, tracker, customer_input: str, ai_response: str, timeout: float = 300):
        """Request human review through the tracker's queue system"""
        # Add to review queue
        review_data = {
            'customer_input': customer_input,
            'ai_response': ai_response,
            'timestamp': time.time()
        }
        tracker.review_queue.put(review_data)

        # Wait for result with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = tracker.result_queue.get(timeout=1.0)
                logger.info(f"Human review completed in {result.human_time_ms:.1f}ms")
                return result
            except:
                continue

        # Timeout - return original response
        from dataclasses import dataclass
        @dataclass
        class TimeoutResult:
            original_response: str
            edited_response: str
            human_time_ms: float
            customer_input: str
            review_notes: str = None

        logger.warning(f"Human review timed out after {timeout}s")
        return TimeoutResult(
            original_response=ai_response,
            edited_response=ai_response,
            human_time_ms=timeout * 1000,
            customer_input=customer_input,
            review_notes="Timed out - using original response"
        )

    def _create_failed_result(
        self,
        scenario_id: str,
        customer_input: str,
        error_message: str,
        safety_issues: List[str] = None,
        tone_issues: List[str] = None
    ) -> Dict[str, Any]:
        """Create a failed result structure"""

        failed_result = PipelineResult(
            scenario_id=str(scenario_id),
            customer_input=customer_input,
            final_response=f"Processing failed: {error_message}",
            ai_time=0,
            total_time=0,
            safety_issues=safety_issues or [],
            tone_issues=tone_issues or [],
            success=False
        )

        self.results_history.append(failed_result)

        return asdict(failed_result)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""

        if not self.results_history:
            return {"message": "No data available"}

        successful_results = [r for r in self.results_history if r.success]

        stats = {
            "total_processed": len(self.results_history),
            "successful": len(successful_results),
            "success_rate": len(successful_results) / len(self.results_history) * 100,
            "pipeline_tracker": self.pipeline_tracker.get_stats(),
            "agent_stats": {
                "guard": self.guard_agent.get_performance_stats(),
                "response": self.response_agent.get_performance_stats(),
                "tone": self.tone_agent.get_performance_stats(),
                "rewrite": self.rewrite_agent.get_performance_stats()
            }
        }

        if successful_results:
            ai_times = [r.ai_time for r in successful_results]
            stats["ai_performance"] = {
                "avg_time": sum(ai_times) / len(ai_times),
                "min_time": min(ai_times),
                "max_time": max(ai_times)
            }

        return stats

    def reset_metrics(self):
        """Reset all performance metrics"""
        self.pipeline_tracker.reset()
        self.guard_agent.reset_metrics()
        self.response_agent.reset_metrics()
        self.tone_agent.reset_metrics()
        self.rewrite_agent.reset_metrics()
        self.results_history = []

        logger.info("All metrics reset")

    async def health_check(self) -> Dict[str, bool]:
        """Perform comprehensive health check"""

        logger.info("Performing pipeline health check...")

        checks = {
            "guard_agent": await self.guard_agent.health_check(),
            "response_agent": await self.response_agent.health_check(),
            "tone_agent": await self.tone_agent.health_check(),
            "rewrite_agent": await self.rewrite_agent.health_check(),
        }

        all_healthy = all(checks.values())

        logger.info(f"Health check completed: {'All systems healthy' if all_healthy else 'Issues detected'}")

        return checks