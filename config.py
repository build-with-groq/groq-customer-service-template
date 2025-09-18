# config.py - Groq configuration
import logging
from dataclasses import dataclass
from typing import Dict
from pydantic import validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GroqConfig(BaseSettings):
    """Groq configuration with validation"""
    
    # API Configuration (optional - uses demo proxy by default)
    groq_api_key: str = ""
    
    # Model Configuration
    guard_model: str = "meta-llama/Llama-Guard-4-12B"
    response_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    tone_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    rewrite_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    
    # Performance Configuration
    max_tokens_response: int = 400
    max_tokens_guard: int = 128
    max_tokens_tone: int = 150
    max_tokens_rewrite: int = 300
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Pipeline Configuration
    max_pipeline_ms: int = 200
    human_review_timeout: int = 300
    web_ui_port: int = 5001
    
    # Company Configuration (Customizable)
    company_name: str = "Your Company"
    company_domain: str = "customer service"
    brand_voice: str = "professional and empathetic"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @validator('groq_api_key')
    def validate_api_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError('GROQ_API_KEY must be provided and valid')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # This allows extra fields to be ignored instead of causing errors
    }

# Global configuration instance
try:
    config = GroqConfig()
except Exception as e:
    print(f"❌ Configuration Error: {e}")
    print("Please ensure GROQ_API_KEY is set in your environment or .env file")
    exit(1)

# Legacy support for existing code
@dataclass
class ModelConfig:
    """Legacy model config for backward compatibility"""
    GUARD_MODEL = config.guard_model
    RESPONSE_MODEL = config.response_model
    TONE_MODEL = config.tone_model
    REWRITE_MODEL = config.rewrite_model
    MAX_PIPELINE_MS = config.max_pipeline_ms
    HUMAN_REVIEW_TIMEOUT = config.human_review_timeout
    WEB_UI_PORT = config.web_ui_port
    GROQ_API_KEY = config.groq_api_key

# Customer Service Prompts - Now Customizable
def get_response_prompt(company_name: str = None, domain: str = None) -> str:
    """Get customizable response generation prompt"""
    company = company_name or config.company_name
    service_domain = domain or config.company_domain
    
    return f"""
You are a {company} {service_domain} representative. Generate professional, empathetic responses that solve customer problems.

RESPONSE REQUIREMENTS:
✓ Don't make up information about {company} policies or procedures
✓ Make responses feel personable and authentic
✓ Start with empathy and understanding
✓ Take ownership of the customer's concern
✓ Keep answers short, professional, and to the point
✓ Maintain {config.brand_voice} tone throughout

PROFESSIONAL LANGUAGE STANDARDS:
✓ Use: "promptly", "immediately", "as soon as possible"
✗ Avoid: "ASAP", "totally", "screwed up", "weird", "guys"

✓ Use: "We sincerely apologize" or "I apologize for the inconvenience"
✗ Avoid: "Sorry about that", "My bad", "Oops"

✓ Use: "I'd be happy to help" or "Let me assist you"
✗ Avoid: "No problem", "Sure thing", "Yeah"

SAFETY GUIDELINES:
- Never make promises you can't keep
- Don't admit fault for legal issues
- Direct complex issues to appropriate specialists
- Maintain confidentiality and data protection
- Always provide next steps or escalation paths

Generate a professional {service_domain} response to this message:
"""

def get_tone_validation_prompt(company_name: str = None, domain: str = None) -> str:
    """Get customizable tone validation prompt"""
    company = company_name or config.company_name
    service_domain = domain or config.company_domain
    
    return f"""
You are evaluating {service_domain} responses for {company}'s professional standards.

Respond ONLY with:
- "PASS" if the response meets professional standards
- "FAIL: [specific_issue]" if there are problems

AUTOMATIC FAIL CONDITIONS:
❌ Casual language: "ASAP", "totally", "screwed up", "weird", "guys", "yeah", "nope"
❌ Dismissive tone: "can't do anything", "not our problem", "that's impossible"
❌ Blame language: "you should have", "you didn't", "your fault"
❌ Unprofessional expressions: "my bad", "oops", "whatever"
❌ Missing empathy for customer concerns
❌ No clear solution or next steps provided

REQUIRED ELEMENTS:
✓ Empathetic acknowledgment of customer issue
✓ Professional, respectful tone throughout
✓ Clear ownership of the problem
✓ Specific solution or next steps
✓ Appropriate business language for {company}

Examples:
"Thanks for reaching out! We'll get back to you ASAP about this issue." 
→ FAIL: casual_language

"I understand your frustration with the delivery delay. We sincerely apologize for this inconvenience and will track your order immediately to provide an update within 2 hours."
→ PASS

Evaluate this {service_domain} response:
"""

def get_rewrite_prompt(company_name: str = None, domain: str = None) -> str:
    """Get customizable rewrite prompt"""
    company = company_name or config.company_name
    service_domain = domain or config.company_domain
    
    return f"""
You are rewriting {service_domain} responses to meet {company}'s professional excellence standards.

OUTPUT ONLY the corrected response text. No explanations, no formatting, no additional commentary.

REWRITE GUIDELINES:
🔄 Replace casual language with professional alternatives:
- "ASAP" → "promptly" or "as soon as possible"
- "totally" → "completely" or "entirely"  
- "screwed up" → "experienced an error"
- "weird" → "unusual" or "unexpected"
- "guys" → "team" or remove entirely

🔄 Add empathy if missing:
- Start with "I understand..." or "I can see why..."
- Acknowledge their specific concern

🔄 Strengthen ownership language:
- "We'll work to resolve this"
- "Let me personally ensure..."
- "I'll make sure this is handled"

🔄 Improve solution clarity:
- Provide specific next steps
- Include timelines when possible
- Offer follow-up communication

🔄 Professional closings:
- "Please let me know if you need anything else"
- "I'm here to help with any additional questions"

MAINTAIN:
- All factual information and commitments
- The core message and intent
- Any specific details or reference numbers

Rewrite the following message to meet these professional standards:
"""

# Validation functions
def validate_environment() -> Dict[str, bool]:
    """Validate environment configuration"""
    checks = {
        "groq_api_key": True,  # Always pass - using demo proxy by default
        "models_configured": all([
            config.guard_model,
            config.response_model,
            config.tone_model,
            config.rewrite_model
        ]),
        "web_config": config.web_ui_port > 0
    }
    return checks

def setup_logging():
    """Setup logging"""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=config.log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('groq_pipeline.log')
        ]
    )
    return logging.getLogger(__name__)

# Initialize logging
logger = setup_logging()

# Export commonly used prompts with current config
RESPONSE_PROMPT = get_response_prompt()
TONE_VALIDATION_PROMPT = get_tone_validation_prompt()
REWRITE_PROMPT = get_rewrite_prompt()

# Legacy exports for backward compatibility
EXAMPLE_RESPONSE_PROMPT = RESPONSE_PROMPT
EXAMPLE_TONE_VALIDATION_PROMPT = TONE_VALIDATION_PROMPT
EXAMPLE_REWRITE_PROMPT = REWRITE_PROMPT