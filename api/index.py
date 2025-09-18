# api/index.py - Minimal Vercel Flask entry point for Groq Customer Service Pipeline
import time
import os
import sys
import json
import queue
import uuid
import threading
from threading import Thread

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask
from flask import Flask, request, jsonify

# Minimal classes without dataclass decorators
class PipelineStep:
    def __init__(self, step_name, start_time, end_time=None, status="running", details="", model_used=None):
        self.step_name = step_name
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.details = details
        self.model_used = model_used

    def duration_ms(self):
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

class PipelineProgress:
    def __init__(self, scenario_id, customer_input):
        self.scenario_id = scenario_id
        self.customer_input = customer_input
        self.steps = []
        self.current_step = 0
        self.total_steps = 6
        self.start_time = time.time()
        self.end_time = None

    def add_step(self, step_name, details="", model_used=None):
        step = PipelineStep(
            step_name=step_name,
            start_time=time.time(),
            details=details,
            model_used=model_used
        )
        self.steps.append(step)
        self.current_step = len(self.steps)
        return step

    def complete_current_step(self, details="", status="completed"):
        if self.steps:
            current = self.steps[-1]
            current.end_time = time.time()
            current.status = status
            if details:
                current.details = details

# Global state management
class AppState:
    def __init__(self):
        self.review_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.active_reviews = {}
        self.review_lock = threading.Lock()
        self.pipeline_progress = {}
        self.progress_lock = threading.Lock()
        self.demo_state = "idle"
        self.current_scenario_index = 0
        self.demo_results = []
        self.current_scenario_result = None
        self.current_scenario_id = None
        self.demo_scenarios = [
            "My order was supposed to arrive yesterday but I haven't received anything. Can you check the status?",
            "This is the third time I'm contacting you about my damaged dining table. When will this be resolved?",
            "This is absolutely ridiculous! Your delivery team are complete idiots who damaged my wall and now you're ignoring me. Fix this NOW or I'm never shopping here again!"
        ]

# Initialize Flask app
app = Flask(__name__)
app_state = AppState()

@app.route('/')
def index():
    """Main demo interface"""
    try:
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'public', 'index.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return """
        <!DOCTYPE html>
        <html><head><title>Groq Demo</title></head>
        <body>
            <h1>🚀 Groq Customer Service Pipeline Demo</h1>
            <p>Minimal demo version running on Vercel</p>
            <p>API endpoints available:</p>
            <ul>
                <li><a href="/api/health">/api/health</a> - Health check</li>
                <li>/api/start_interactive_demo - Start demo (POST)</li>
                <li>/api/get_demo_status - Get current status</li>
            </ul>
            <script>
                fetch('/api/start_interactive_demo', {method: 'POST'})
                .then(r => r.json())
                .then(d => console.log('Demo started:', d))
                .catch(e => console.error('Demo start failed:', e));
            </script>
        </body></html>
        """

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'environment': 'vercel-minimal',
        'python_version': sys.version,
        'demo_state': app_state.demo_state,
        'scenarios': len(app_state.demo_scenarios)
    })

@app.route('/api/start_interactive_demo', methods=['POST'])
def start_interactive_demo():
    """Start interactive demo mode"""
    app_state.demo_state = "running"
    app_state.current_scenario_index = 0
    app_state.demo_results = []
    app_state.pipeline_progress = {}

    return jsonify({
        'status': 'success',
        'total_scenarios': len(app_state.demo_scenarios),
        'current_scenario': 1
    })

@app.route('/api/get_current_scenario')
def get_current_scenario():
    """Get current scenario for interactive demo"""
    if app_state.demo_state != "running" or app_state.current_scenario_index >= len(app_state.demo_scenarios):
        return jsonify({'status': 'no_scenario'})

    scenario = app_state.demo_scenarios[app_state.current_scenario_index]
    return jsonify({
        'status': 'success',
        'scenario': scenario,
        'scenario_number': app_state.current_scenario_index + 1,
        'total_scenarios': len(app_state.demo_scenarios),
        'can_process': True
    })

@app.route('/api/process_current_scenario', methods=['POST'])
def process_current_scenario():
    """Process current scenario"""
    if app_state.demo_state != "running":
        return jsonify({'status': 'error', 'message': 'Demo not running'})

    if app_state.current_scenario_index >= len(app_state.demo_scenarios):
        return jsonify({'status': 'error', 'message': 'No scenario available'})

    scenario = app_state.demo_scenarios[app_state.current_scenario_index]
    scenario_id = f"demo_{app_state.current_scenario_index + 1}_{int(time.time())}"
    app_state.current_scenario_id = scenario_id

    # Create pipeline progress
    with app_state.progress_lock:
        progress = PipelineProgress(scenario_id, scenario)
        app_state.pipeline_progress[scenario_id] = progress

    # Simulate processing in background
    def simulate_processing():
        time.sleep(0.5)  # Simulate processing time

        # Create mock result
        result = {
            'scenario_id': scenario_id,
            'customer_input': scenario,
            'final_response': "Thank you for contacting us. We sincerely apologize for the inconvenience and will resolve this matter immediately.",
            'ai_time': 150.0,
            'total_time': 200.0,
            'success': True,
            'safety_issues': [],
            'tone_issues': []
        }

        app_state.demo_results.append(result)
        app_state.current_scenario_result = result

        # Mark progress complete
        with app_state.progress_lock:
            if scenario_id in app_state.pipeline_progress:
                app_state.pipeline_progress[scenario_id].end_time = time.time()

    thread = Thread(target=simulate_processing, daemon=True)
    thread.start()

    return jsonify({'status': 'processing', 'scenario_id': scenario_id})

@app.route('/api/get_pipeline_progress')
def get_pipeline_progress():
    """Get pipeline progress"""
    if not app_state.current_scenario_id:
        return jsonify({'status': 'no_progress'})

    with app_state.progress_lock:
        progress = app_state.pipeline_progress.get(app_state.current_scenario_id)
        if not progress:
            return jsonify({'status': 'no_progress'})

        # Simulate some steps
        steps_data = [
            {'step_name': 'safety_check', 'status': 'completed', 'details': 'Safety check passed', 'duration_ms': 50.0},
            {'step_name': 'response_generation', 'status': 'completed', 'details': 'Response generated', 'duration_ms': 100.0}
        ]

        return jsonify({
            'status': 'success',
            'scenario_id': progress.scenario_id,
            'customer_input': progress.customer_input,
            'current_step': 2,
            'total_steps': 6,
            'steps': steps_data,
            'total_duration_ms': 200.0,
            'completed': progress.end_time is not None
        })

@app.route('/api/next_scenario', methods=['POST'])
def next_scenario():
    """Move to next scenario"""
    if app_state.demo_state != "running":
        return jsonify({'status': 'error', 'message': 'Demo not running'})

    app_state.current_scenario_index += 1
    app_state.current_scenario_id = None
    app_state.current_scenario_result = None

    if app_state.current_scenario_index >= len(app_state.demo_scenarios):
        app_state.demo_state = "completed"
        return jsonify({'status': 'completed', 'message': 'All scenarios completed'})

    return jsonify({
        'status': 'success',
        'scenario_number': app_state.current_scenario_index + 1,
        'total_scenarios': len(app_state.demo_scenarios)
    })

@app.route('/api/get_demo_status')
def get_demo_status():
    """Get demo status"""
    return jsonify({
        'state': app_state.demo_state,
        'current_scenario': app_state.current_scenario_index + 1 if app_state.demo_scenarios else 0,
        'total_scenarios': len(app_state.demo_scenarios),
        'results_count': len(app_state.demo_results),
        'current_scenario_id': app_state.current_scenario_id,
        'results': app_state.current_scenario_result
    })

@app.route('/api/reset_demo', methods=['POST'])
def reset_demo():
    """Reset demo"""
    app_state.demo_state = "idle"
    app_state.current_scenario_index = 0
    app_state.demo_results = []
    app_state.current_scenario_result = None
    app_state.current_scenario_id = None

    with app_state.progress_lock:
        app_state.pipeline_progress = {}

    return jsonify({'status': 'success'})

# This is the WSGI application entry point for Vercel