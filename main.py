# main.py - Groq Customer Service Pipeline Demo
import asyncio
import sys

from pipeline_demo import GroqCustomerServiceDemo
from config import config, validate_environment, logger
from utils import print_banner, validate_groq_connection

# Test scenarios including challenging customers
DEMO_TEST_SCENARIOS = [
    "My order was supposed to arrive yesterday but I haven't received anything. Can you check the status?",
    
    "This is the third time I'm contacting you about my damaged dining table. When will this be resolved?",
    
    "This is absolutely ridiculous! Your delivery team are complete idiots who damaged my wall and now you're ignoring me. Fix this NOW or I'm never shopping here again!",
    
    "What the heck is wrong with your company?! This whole experience has been a complete disaster and I'm sick of being redirected by your useless customer service!",
    
    "I don't care about your policies. I want a full refund immediately and I expect you to pay for my time wasted dealing with this garbage. Make it happen or I'll blast you on social media."
]

async def main():
    """Groq customer service pipeline demo"""
    
    # Print banner and validate environment
    print_banner()
    
    logger.info("Starting Groq Customer Service Pipeline Demo")
    
    # Validate environment configuration
    validation_results = validate_environment()
    if not all(validation_results.values()):
        logger.error("Environment validation failed:")
        for check, passed in validation_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check}: {status}")
        
        if not validation_results.get("groq_api_key"):
            print("\n💡 To fix this:")
            print("   1. Get your Groq API key from https://console.groq.com/keys")
            print("   2. Set it as an environment variable: export GROQ_API_KEY='your-key-here'")
            print("   3. Or create a .env file with GROQ_API_KEY=your-key-here")
        
        sys.exit(1)
    
    # Test Groq connection
    logger.info("Testing Groq API connection...")
    if not await validate_groq_connection():
        logger.error("Failed to connect to Groq API")
        print("❌ Cannot connect to Groq API. Please check your API key and internet connection.")
        sys.exit(1)
    
    print("✅ Environment validation passed")
    print("✅ Groq API connection successful")
    
    # Initialize demo
    try:
        demo = GroqCustomerServiceDemo(
            company_name=config.company_name,
            domain=config.company_domain
        )
        
        # Start web interface and set demo instance
        demo.start_web_interface()
        demo.human_loop.set_demo_instance(demo, DEMO_TEST_SCENARIOS)
        
        print(f"\n🌐 Customer Service Pipeline Demo: http://localhost:{config.web_ui_port}")
        print("📋 Demo Features:")
        print("   ✅ Real-time pipeline monitoring")
        print("   ✅ Human-in-the-loop review process")
        print("   ✅ Safety and tone validation")
        print("   ✅ Automatic response improvement")
        print("   ✅ Performance metrics tracking")
        print("   ✅ Interactive web-based demo modes")
        
        print(f"\n🚀 Available Demo Modes (via web interface):")
        print("   1. Interactive Demo - Step through scenarios manually with buttons")
        print(f"\nOpen your browser to http://localhost:{config.web_ui_port} to start!")
        
        # Keep the server running
        print("\n⏳ Server is running. Press Ctrl+C to exit...")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Demo interrupted by user")
                
    except Exception as e:
        logger.error(f"Demo initialization failed: {e}")
        print(f"❌ Demo failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting Groq Customer Service Pipeline Demo...")
    print("⚠️  Ensure GROQ_API_KEY is set in your environment or .env file")
    print("📋 Requirements: pip install -r requirements.txt")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("Make sure you have all required packages installed:")
        print("   pip install -r requirements.txt")
        print("And that your GROQ_API_KEY is properly configured.")
        sys.exit(1)