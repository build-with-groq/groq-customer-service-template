# response_agent.py - Groq response generation
import time
import logging
from typing import Tuple
from base import BaseAgent
from config import config, get_response_prompt

logger = logging.getLogger(__name__)

class ResponseAgent(BaseAgent):
    """Professional customer service response generation using Groq"""
    
    def __init__(self, company_name: str = None, domain: str = None):
        super().__init__()
        self.model = config.response_model
        self.response_prompt = get_response_prompt(company_name, domain)
        self.company_name = company_name or config.company_name
        self.domain = domain or config.company_domain
        
        logger.info(f"Initialized ResponseAgent for {self.company_name} {self.domain}")
    
    async def generate_response(self, customer_input: str, context: dict = None) -> Tuple[str, float]:
        """Generate professional customer service response"""
        start = time.perf_counter()
        
        try:
            logger.debug(f"Generating response for: {customer_input[:50]}...")
            
            # Prepare messages with optional context
            messages = [
                {"role": "system", "content": self.response_prompt}
            ]
            
            # Add context if provided
            if context:
                context_str = self._format_context(context)
                messages.append({"role": "system", "content": f"Additional context: {context_str}"})
            
            messages.append({"role": "user", "content": f"Customer message: {customer_input}"})
            
            response = await self._make_groq_request(
                model=self.model,
                messages=messages,
                max_tokens=config.max_tokens_response,
                temperature=0.1  # Low temperature for consistent, professional responses
            )
            
            latency = self._track_latency(start)
            
            # Clean and validate response
            cleaned_response = self._clean_response(response)
            
            logger.info(f"Response generated successfully in {latency:.1f}ms ({len(cleaned_response)} chars)")
            
            return cleaned_response, latency
            
        except Exception as e:
            latency = self._track_latency(start)
            logger.error(f"Response generation failed: {e}")
            
            # Return fallback response
            fallback = self._get_fallback_response(customer_input)
            return fallback, latency
    
    def _format_context(self, context: dict) -> str:
        """Format additional context for the AI"""
        context_parts = []
        
        if context.get('customer_id'):
            context_parts.append(f"Customer ID: {context['customer_id']}")
        
        if context.get('order_id'):
            context_parts.append(f"Order ID: {context['order_id']}")
        
        if context.get('previous_interactions'):
            context_parts.append(f"Previous interactions: {context['previous_interactions']}")
        
        if context.get('urgency'):
            context_parts.append(f"Urgency level: {context['urgency']}")
        
        return " | ".join(context_parts)
    
    def _clean_response(self, response: str) -> str:
        """Clean and validate the generated response"""
        cleaned = response.strip()
        
        # Remove any system artifacts
        if cleaned.startswith("Response:"):
            cleaned = cleaned[9:].strip()
        
        if cleaned.startswith("Customer service response:"):
            cleaned = cleaned[26:].strip()
        
        # Ensure response isn't too short
        if len(cleaned) < 20:
            logger.warning(f"Response too short: {cleaned}")
            return self._get_fallback_response("")
        
        return cleaned
    
    def _get_fallback_response(self, customer_input: str) -> str:
        """Generate fallback response when AI fails"""
        return f"""Thank you for contacting {self.company_name}. I understand you need assistance, and I want to help resolve your concern.

I'm currently experiencing a technical issue that prevents me from providing a detailed response right now. However, I want to ensure you receive the support you need.

Please reach out to our support team directly, and they will be able to assist you immediately with your inquiry.

I apologize for any inconvenience, and thank you for your patience."""
    
    async def generate_multiple_responses(
        self, 
        customer_inputs: list[str], 
        contexts: list[dict] = None
    ) -> list[Tuple[str, float]]:
        """Generate responses for multiple customer inputs"""
        logger.info(f"Generating {len(customer_inputs)} responses")
        
        results = []
        contexts = contexts or [None] * len(customer_inputs)
        
        for i, (customer_input, context) in enumerate(zip(customer_inputs, contexts)):
            logger.debug(f"Processing input {i+1}/{len(customer_inputs)}")
            result = await self.generate_response(customer_input, context)
            results.append(result)
        
        return results
    
    def update_prompt(self, company_name: str = None, domain: str = None):
        """Update the response generation prompt"""
        if company_name:
            self.company_name = company_name
        if domain:
            self.domain = domain
        
        self.response_prompt = get_response_prompt(self.company_name, self.domain)
        logger.info(f"Updated prompt for {self.company_name} {self.domain}")
    
    def get_response_stats(self, responses: list[str]) -> dict:
        """Get statistics about generated responses"""
        if not responses:
            return {}
        
        lengths = [len(r) for r in responses]
        word_counts = [len(r.split()) for r in responses]
        
        return {
            "total_responses": len(responses),
            "avg_length": sum(lengths) / len(lengths),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "min_length": min(lengths),
            "max_length": max(lengths)
        }