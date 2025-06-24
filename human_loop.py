# human_loop.py - Groq human review interface
import time
import asyncio
import logging
import os
from flask import Flask, request, jsonify
from threading import Thread
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import queue
import uuid
import threading

logger = logging.getLogger(__name__)

@dataclass
class PipelineStep:
    """Individual pipeline step with timing"""
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # running, completed, failed
    details: str = ""
    model_used: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

@dataclass
class PipelineProgress:
    """Complete pipeline progress tracking"""
    scenario_id: str
    customer_input: str
    steps: List[PipelineStep]
    current_step: int = 0
    total_steps: int = 6
    start_time: float = None
    end_time: Optional[float] = None
    
    def add_step(self, step_name: str, details: str = "", model_used: str = None):
        step = PipelineStep(
            step_name=step_name,
            start_time=time.time(),
            details=details,
            model_used=model_used
        )
        self.steps.append(step)
        self.current_step = len(self.steps)
        return step
    
    def complete_current_step(self, details: str = "", status: str = "completed"):
        if self.steps:
            current = self.steps[-1]
            current.end_time = time.time()
            current.status = status
            if details:
                current.details = details

@dataclass
class HumanReviewResult:
    """Result from human review process"""
    original_response: str
    edited_response: str
    human_time_ms: float
    customer_input: str
    review_notes: Optional[str] = None

class HumanLoopManager:
    """Human review interface for Groq pipeline"""
    
    def __init__(self):
        self.app = Flask(__name__)
        
        # Suppress HTTP request logs
        self.app.logger.setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        # Review management
        self.review_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.active_reviews = {}  # {review_id: review_data}
        self.review_lock = threading.Lock()
        
        # Pipeline progress tracking
        self.pipeline_progress = {}  # {scenario_id: PipelineProgress}
        self.progress_lock = threading.Lock()
        
        # Demo management
        self.demo_instance = None
        self.demo_scenarios = []
        self.current_scenario_index = 0
        self.demo_results = []
        self.current_scenario_result = None  # Track current scenario result separately
        self.demo_state = "idle"  # idle, running, paused, completed
        self.current_scenario_id = None
        
        # Server state
        self.server_thread = None
        self.is_running = False
        
        self.setup_routes()
        logger.info("HumanLoopManager initialized with enhanced pipeline tracking")
    
    def setup_routes(self):
        """Setup Flask routes for the web interface"""
        
        @self.app.route('/')
        def index():
            """Main demo interface"""
            try:
                # Read template from file
                template_path = os.path.join(os.path.dirname(__file__), 'template.html')
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                return template_content
            except FileNotFoundError:
                return "Template file not found", 404
            except Exception as e:
                logger.error(f"Error reading template: {e}")
                return "Error loading template", 500
        
        @self.app.route('/api/get_review')
        def get_review():
            """Get next review item"""
            try:
                review_data = self.review_queue.get_nowait()
                review_id = str(uuid.uuid4())
                
                with self.review_lock:
                    self.active_reviews[review_id] = {
                        **review_data,
                        'review_id': review_id,
                        'start_time': time.time()
                    }
                
                logger.debug(f"Serving review {review_id}")
                return jsonify({
                    'review_id': review_id,
                    'customer_input': review_data['customer_input'],
                    'ai_response': review_data['ai_response'],
                    'status': 'success'
                })
                
            except queue.Empty:
                return jsonify({'status': 'no_reviews'})
        
        @self.app.route('/api/submit_review', methods=['POST'])
        def submit_review():
            """Submit review result"""
            try:
                data = request.json
                review_id = data.get('review_id')
                
                if not review_id or review_id not in self.active_reviews:
                    return jsonify({'status': 'error', 'message': 'Invalid review ID'})
                
                with self.review_lock:
                    review_data = self.active_reviews.pop(review_id)
                
                # Calculate review time
                review_time = (time.time() - review_data['start_time']) * 1000
                
                # Create result
                result = HumanReviewResult(
                    original_response=review_data['ai_response'],
                    edited_response=data.get('edited_response', review_data['ai_response']),
                    human_time_ms=review_time,
                    customer_input=review_data['customer_input'],
                    review_notes=data.get('notes')
                )
                
                # Send result back to pipeline
                self.result_queue.put(result)
                
                logger.info(f"Review {review_id} completed in {review_time:.1f}ms")
                return jsonify({'status': 'success'})
                
            except Exception as e:
                logger.error(f"Review submission failed: {e}")
                return jsonify({'status': 'error', 'message': str(e)})
        
        @self.app.route('/api/start_interactive_demo', methods=['POST'])
        def start_interactive_demo():
            """Start interactive demo mode"""
            if not self.demo_instance:
                return jsonify({'status': 'error', 'message': 'Demo not initialized'})
            
            self.demo_state = "running"
            self.current_scenario_index = 0
            self.demo_results = []
            self.pipeline_progress = {}
            
            return jsonify({
                'status': 'success',
                'total_scenarios': len(self.demo_scenarios),
                'current_scenario': self.current_scenario_index + 1 if self.demo_scenarios else 0
            })
        
        @self.app.route('/api/get_current_scenario')
        def get_current_scenario():
            """Get current scenario for interactive demo"""
            if self.demo_state != "running" or self.current_scenario_index >= len(self.demo_scenarios):
                return jsonify({'status': 'no_scenario'})
            
            scenario = self.demo_scenarios[self.current_scenario_index]
            return jsonify({
                'status': 'success',
                'scenario': scenario,
                'scenario_number': self.current_scenario_index + 1,
                'total_scenarios': len(self.demo_scenarios),
                'can_process': True
            })
        
        @self.app.route('/api/process_current_scenario', methods=['POST'])
        def process_current_scenario():
            """Process current scenario in interactive mode"""
            if self.demo_state != "running" or self.current_scenario_index >= len(self.demo_scenarios):
                return jsonify({'status': 'error', 'message': 'No scenario available'})
            
            scenario = self.demo_scenarios[self.current_scenario_index]
            scenario_id = f"interactive_{self.current_scenario_index + 1}"
            self.current_scenario_id = scenario_id
            
            # Initialize pipeline progress
            with self.progress_lock:
                self.pipeline_progress[scenario_id] = PipelineProgress(
                    scenario_id=scenario_id,
                    customer_input=scenario,
                    steps=[],
                    start_time=time.time()
                )
            
            self._start_scenario_processing(scenario, self.current_scenario_index + 1, scenario_id)
            
            return jsonify({'status': 'processing', 'scenario_id': scenario_id})
        
        @self.app.route('/api/get_pipeline_progress')
        def get_pipeline_progress():
            """Get current pipeline progress"""
            if not self.current_scenario_id:
                return jsonify({'status': 'no_progress'})
            
            with self.progress_lock:
                progress = self.pipeline_progress.get(self.current_scenario_id)
                if not progress:
                    return jsonify({'status': 'no_progress'})
                
                steps_data = []
                for step in progress.steps:
                    steps_data.append({
                        'step_name': step.step_name,
                        'status': step.status,
                        'details': step.details,
                        'duration_ms': step.duration_ms,
                        'model_used': step.model_used
                    })
                
                total_duration = 0
                if progress.end_time:
                    total_duration = (progress.end_time - progress.start_time) * 1000
                elif progress.start_time:
                    total_duration = (time.time() - progress.start_time) * 1000
                
                return jsonify({
                    'status': 'success',
                    'scenario_id': progress.scenario_id,
                    'customer_input': progress.customer_input,
                    'current_step': progress.current_step,
                    'total_steps': progress.total_steps,
                    'steps': steps_data,
                    'total_duration_ms': total_duration,
                    'completed': progress.end_time is not None
                })
        
        @self.app.route('/api/next_scenario', methods=['POST'])
        def next_scenario():
            """Move to next scenario in interactive mode"""
            if self.demo_state != "running":
                return jsonify({'status': 'error', 'message': 'Demo not running'})
            
            self.current_scenario_index += 1
            self.current_scenario_id = None
            self.current_scenario_result = None  # Clear current scenario result
            
            if self.current_scenario_index >= len(self.demo_scenarios):
                self.demo_state = "completed"
                return jsonify({'status': 'completed', 'message': 'All scenarios completed'})
            
            return jsonify({
                'status': 'success',
                'scenario_number': self.current_scenario_index + 1,
                'total_scenarios': len(self.demo_scenarios)
            })
        
        @self.app.route('/api/process_custom_input', methods=['POST'])
        def process_custom_input():
            """Process custom customer input"""
            if not self.demo_instance:
                return jsonify({'status': 'error', 'message': 'Demo not initialized'})
            
            data = request.json
            custom_input = data.get('input', '').strip()
            
            if not custom_input:
                return jsonify({'status': 'error', 'message': 'No input provided'})
            
            scenario_id = f"custom_{int(time.time())}"
            self.current_scenario_id = scenario_id
            
            # Initialize pipeline progress
            with self.progress_lock:
                self.pipeline_progress[scenario_id] = PipelineProgress(
                    scenario_id=scenario_id,
                    customer_input=custom_input,
                    steps=[],
                    start_time=time.time()
                )
            
            self._start_custom_processing(custom_input, scenario_id)
            
            return jsonify({'status': 'processing', 'scenario_id': scenario_id})
        
        @self.app.route('/api/get_demo_status')
        def get_demo_status():
            """Get current demo status"""
            return jsonify({
                'state': self.demo_state,
                'current_scenario': self.current_scenario_index + 1 if self.demo_scenarios else 0,
                'total_scenarios': len(self.demo_scenarios),
                'results_count': len(self.demo_results),
                'current_scenario_id': self.current_scenario_id,
                'results': self.current_scenario_result
            })
        
        @self.app.route('/api/reset_demo', methods=['POST'])
        def reset_demo():
            """Reset demo to initial state"""
            # Clear demo state
            self.demo_state = "idle"
            self.current_scenario_index = 0
            self.demo_results = []
            self.current_scenario_result = None
            self.current_scenario_id = None
            
            # Clear pipeline progress tracking
            with self.progress_lock:
                self.pipeline_progress = {}
            
            # Clear review system state
            with self.review_lock:
                self.active_reviews = {}
                # Clear any pending reviews in queues
                while not self.review_queue.empty():
                    try:
                        self.review_queue.get_nowait()
                    except queue.Empty:
                        break
                while not self.result_queue.empty():
                    try:
                        self.result_queue.get_nowait()
                    except queue.Empty:
                        break
            
            logger.info("Demo reset - all state cleared")
            return jsonify({'status': 'success'})
        
        @self.app.route('/api/health')
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'demo_state': self.demo_state,
                'active_reviews': len(self.active_reviews),
                'pipeline_progress_count': len(self.pipeline_progress)
            })
    
    def track_pipeline_step(self, scenario_id: str, step_name: str, details: str = "", model_used: str = None):
        """Track a new pipeline step"""
        with self.progress_lock:
            if scenario_id in self.pipeline_progress:
                self.pipeline_progress[scenario_id].add_step(step_name, details, model_used)
    
    def complete_pipeline_step(self, scenario_id: str, details: str = "", status: str = "completed"):
        """Complete the current pipeline step"""
        with self.progress_lock:
            if scenario_id in self.pipeline_progress:
                self.pipeline_progress[scenario_id].complete_current_step(details, status)
    
    def complete_pipeline(self, scenario_id: str):
        """Mark pipeline as completed"""
        with self.progress_lock:
            if scenario_id in self.pipeline_progress:
                self.pipeline_progress[scenario_id].end_time = time.time()
    
    def _start_scenario_processing(self, scenario: str, scenario_id: int, scenario_id_str: str):
        """Start scenario processing in a background thread"""
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._process_scenario_async(scenario, scenario_id, scenario_id_str))
            finally:
                loop.close()
        
        thread = Thread(target=run_async, daemon=True)
        thread.start()
    
    def _start_custom_processing(self, custom_input: str, scenario_id: str):
        """Start custom processing in a background thread"""
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._process_custom_async(custom_input, scenario_id))
            finally:
                loop.close()
        
        thread = Thread(target=run_async, daemon=True)
        thread.start()
    
    async def _process_scenario_async(self, scenario: str, scenario_id: int, scenario_id_str: str):
        """Process scenario asynchronously with detailed pipeline tracking"""
        try:
            # Track pipeline start
            self.track_pipeline_step(scenario_id_str, "pipeline_start", f"Starting pipeline for scenario {scenario_id}")
            self.complete_pipeline_step(scenario_id_str, f"Pipeline initialized for: {scenario[:50]}...")
            
            # Process through demo instance with tracking
            if hasattr(self.demo_instance, 'process_single_scenario_with_tracking'):
                result = await self.demo_instance.process_single_scenario_with_tracking(
                    scenario, scenario_id_str, self
                )
            else:
                # Fallback to regular processing
                result = await self.demo_instance.process_single_scenario(scenario)
            
            self.demo_results.append(result)
            self.current_scenario_result = result  # Set current scenario result
            self.complete_pipeline(scenario_id_str)
            logger.info(f"Scenario {scenario_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Scenario {scenario_id} processing failed: {e}")
            self.complete_pipeline_step(scenario_id_str, f"Pipeline failed: {str(e)}", "failed")
            self.demo_state = "error"
    
    async def _process_custom_async(self, custom_input: str, scenario_id: str):
        """Process custom input asynchronously with detailed pipeline tracking"""
        try:
            # Track pipeline start
            self.track_pipeline_step(scenario_id, "pipeline_start", "Starting pipeline for custom input")
            self.complete_pipeline_step(scenario_id, f"Processing: {custom_input[:50]}...")
            
            # Process through demo instance with tracking
            if hasattr(self.demo_instance, 'process_single_scenario_with_tracking'):
                result = await self.demo_instance.process_single_scenario_with_tracking(
                    custom_input, scenario_id, self
                )
            else:
                # Fallback to regular processing
                result = await self.demo_instance.process_single_scenario(custom_input)
            
            self.demo_results.append(result)
            self.current_scenario_result = result  # Set current scenario result
            self.complete_pipeline(scenario_id)
            logger.info(f"Custom input processed successfully")
            
        except Exception as e:
            logger.error(f"Custom input processing failed: {e}")
            self.complete_pipeline_step(scenario_id, f"Pipeline failed: {str(e)}", "failed")
    
    def set_demo_instance(self, demo_instance, scenarios):
        """Set the demo instance and scenarios"""
        self.demo_instance = demo_instance
        self.demo_scenarios = scenarios
        logger.info(f"Demo instance set with {len(scenarios)} scenarios")
    
    def start_server(self, port: int = 5001, debug: bool = False):
        """Start the Flask server"""
        if self.is_running:
            logger.warning("Server already running")
            return
        
        def run_server():
            try:
                self.app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
            except Exception as e:
                logger.error(f"Server failed to start: {e}")
        
        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        
        logger.info(f"Human review interface started on http://localhost:{port}")
        logger.info("Keep this server running to handle human reviews")
    
    async def request_review(
        self, 
        customer_input: str, 
        ai_response: str,
        timeout: float = 300
    ) -> HumanReviewResult:
        """Request human review with timeout"""
        logger.info("Requesting human review")
        
        # Add to review queue
        review_data = {
            'customer_input': customer_input,
            'ai_response': ai_response,
            'timestamp': time.time()
        }
        self.review_queue.put(review_data)
        
        # Wait for result with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = self.result_queue.get(timeout=1.0)
                logger.info(f"Human review completed in {result.human_time_ms:.1f}ms")
                return result
            except queue.Empty:
                continue
        
        # Timeout - return original response
        logger.warning(f"Human review timed out after {timeout}s")
        return HumanReviewResult(
            original_response=ai_response,
            edited_response=ai_response,
            human_time_ms=timeout * 1000,
            customer_input=customer_input,
            review_notes="Timed out - using original response"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get human loop statistics"""
        return {
            'total_reviews_completed': len(self.demo_results),
            'active_reviews': len(self.active_reviews),
            'pending_reviews': self.review_queue.qsize(),
            'demo_state': self.demo_state,
            'current_scenario': self.current_scenario_index + 1,
            'total_scenarios': len(self.demo_scenarios),
            'pipeline_progress_count': len(self.pipeline_progress)
        }