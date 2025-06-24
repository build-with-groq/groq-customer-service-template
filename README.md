# Groq Customer Service Pipeline Template

**AI customer service pipeline powered by Groq's lightning-fast inference**

Transform customer interactions with sub-second response times, intelligent safety moderation, and professional tone validation - all running on Groq's high-performance infrastructure.

## 🚀 Quick Start (5 minutes to running)

### 1. Prerequisites
- **Python 3.8+** (check with `python --version`)
- **Groq API Key** - [Get yours free here](https://console.groq.com/keys)

### 2. Installation
```bash
# Clone and enter the project
git clone https://github.com/benank/groq-customer-service-template
cd groq-customer-service-template

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Set your Groq API key using **one** of these methods:

**Option A: Environment Variable (Recommended)**
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

**Option B: Create .env file**
```bash
# Create .env file in project root
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```

**Option C: Copy from template**
```bash
# Copy the example file and edit it
cp .env.example .env
# Then edit .env with your API key
```

### 4. Run the Demo
```bash
python main.py
```

### 5. Access the Web Interface
Open [http://localhost:5001](http://localhost:5001) in your browser for the human review interface.

**That's it!** The pipeline is now running with:
- ✅ AI-powered customer service responses
- ✅ Real-time safety moderation
- ✅ Professional tone validation
- ✅ Human review workflow
- ✅ Performance monitoring

## Overview

This application demonstrates a complete end-to-end customer service pipeline using Groq API for ultra-fast AI responses. Built as a template that you can fork, customize, and deploy.

**Key Features:**
- **Lightning-Fast Responses**: Fast AI processing with Groq's optimized inference
- **Multi-Stage Safety**: LlamaGuard-powered content moderation at every step
- **Professional Tone Validation**: Automatic detection and correction of unprofessional language
- **Human-in-the-Loop Review**: Web-based interface for quality control and oversight
- **Real-Time Pipeline Monitoring**: Live logging and performance tracking

## Configuration Options

The pipeline is highly customizable through environment variables. Create a `.env` file or set these in your environment:

```bash
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional Customization
COMPANY_NAME="Your Company"
COMPANY_DOMAIN="customer service"
BRAND_VOICE="professional and empathetic"

# Performance Tuning
MAX_PIPELINE_MS=200
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# Web Interface
WEB_UI_PORT=5001

# Logging
LOG_LEVEL=INFO
```

## Architecture

**Tech Stack:**
- **Frontend:** Flask web interface with real-time updates
- **Backend:** Python async pipeline with modular agent architecture
- **AI Infrastructure:** Groq API with Llama models

**Pipeline Stages:**
1. **Initial Safety Check** - LlamaGuard content moderation
2. **Response Generation** - Professional customer service responses
3. **Human Review** - Web-based quality control interface
4. **Final Safety Validation** - Post-review content verification
5. **Tone Analysis** - Professional language standards enforcement
6. **Conditional Rewrite** - Automatic improvement for failed tone validation

**Groq Models Used:**
- **Safety**: [`meta-llama/Llama-Guard-4-12B`](https://console.groq.com/docs/model/meta-llama/llama-guard-4-12b)
- **Response Generation**: [`meta-llama/llama-4-maverick-17b-128e-instruct`](https://console.groq.com/docs/model/meta-llama/llama-4-maverick-17b-128e-instruct)
- **Tone Validation**: [`meta-llama/llama-4-scout-17b-16e-instruct`](https://console.groq.com/docs/model/meta-llama/llama-4-scout-17b-16e-instruct)
- **Content Rewriting**: [`meta-llama/llama-4-maverick-17b-128e-instruct`](https://console.groq.com/docs/model/meta-llama/llama-4-maverick-17b-128e-instruct)

## Project Structure

```
├── main.py                # Demo entry point with test scenarios
├── pipeline_demo.py       # Core pipeline orchestration
├── human_loop.py          # Web interface and human review system
├── config.py              # Model configurations and prompts
├── base.py                # Abstract agent base class
├── guard_agent.py         # LlamaGuard safety moderation
├── response_agent.py      # Customer response generation
├── tone_agent.py          # Professional tone validation
├── rewrite_agent.py       # Content improvement agent
├── utils.py               # Utility classes and functions
├── review.html            # Web interface
├── requirements.txt       # Python dependencies
├── .env.example           # Environment configuration template
└── README.md              # This file
```

## Core Components

### Pipeline Agents

**GuardAgent**: LlamaGuard-4-12B powered safety moderation with comprehensive taxonomy coverage including violence, hate speech, inappropriate content, and professional standards.

**ResponseAgent**: Llama-4-Maverick-17B generates empathetic, professional customer service responses following best practices for acknowledgment, ownership, and solution-oriented communication.

**ToneAgent**: Llama-4-Scout-17B validates professional language standards, detecting casual expressions, unprofessional terminology, and ensuring appropriate business tone.

**RewriteAgent**: Llama-4-Maverick-17B automatically improves responses that fail tone validation, maintaining factual accuracy while enhancing professionalism.

### Human Review Interface
- Real-time pipeline step logging
- Interactive response editing and approval
- Performance metrics and timing data
- Thread-safe review workflow
- Customer context preservation

## Demo Features

### Test Scenarios
Includes challenging customer service scenarios:
- Standard delivery inquiries
- Escalated complaints requiring careful handling
- Hostile customer interactions testing safety systems
- Complex multi-issue requests

### Real-Time Monitoring
- Step-by-step pipeline progress tracking
- AI processing latency measurement
- Human review time monitoring
- Performance optimization insights

### Safety & Compliance
- LlamaGuard taxonomy enforcement (O1-O6 categories)
- Professional language detection and correction
- Content moderation at multiple pipeline stages
- Audit trail for all interactions

## API Usage

### Basic Pipeline Execution
```python
from pipeline_demo import GroqCustomerServiceDemo

# Initialize and start the pipeline
demo = GroqCustomerServiceDemo()
demo.start_web_interface()

# Process individual customer inquiries
customer_input = "My order was supposed to arrive yesterday but I haven't received anything."
result = await demo.process_single_scenario(customer_input)
```

### Individual Agent Usage
```python
from guard_agent import GuardAgent
from response_agent import ResponseAgent

# Initialize Groq agents
guard = GuardAgent()
response_gen = ResponseAgent()

# Process customer input
safety_result, latency = await guard.check_safety(customer_input)
if safety_result.passes:
    response, response_time = await response_gen.generate_response(customer_input)
```

## Customization

This template is designed as a foundation for your customer service needs:

### Model Configuration
- **Update Groq models**: Modify model selections in `config.py`
- **Adjust performance targets**: Set latency and quality thresholds
- **Customize safety taxonomy**: Extend LlamaGuard categories for your domain

### Professional Standards
- **Industry-specific language**: Update tone validation rules in `config.py`
- **Brand voice alignment**: Customize response generation prompts
- **Escalation triggers**: Configure when to route to human agents

### Web Interface
- **Styling and branding**: Customize `template.html`
- **Workflow integration**: Extend human review process
- **Analytics and reporting**: Add custom metrics and dashboards

## Performance Optimization

### Groq Advantages
- **Ultra-low latency**: 10-50ms response times vs 200-2000ms with other providers
- **High throughput**: Handle concurrent requests efficiently
- **Cost effective**: Optimized pricing for large workloads
- **Consistent performance**: Predictable response times under load

## Troubleshooting

### Common Issues

**"Configuration Error: GROQ_API_KEY must be provided"**
- Solution: Set your API key using one of the methods in step 3 above
- Verify: `echo $GROQ_API_KEY` should show your key

**"Cannot connect to Groq API"**
- Check your internet connection
- Verify your API key is valid at [Groq Console](https://console.groq.com/keys)
- Ensure no firewall is blocking the connection

**"ModuleNotFoundError"**
- Run: `pip install -r requirements.txt`
- Use Python 3.8+ (`python --version`)

**Web interface not loading**
- Check if port 5001 is available
- Try a different port: `WEB_UI_PORT=5002 python main.py`

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Verify all requirements are installed
3. Ensure your Groq API key is valid
4. Check the [Groq Community Forum](https://community.groq.com) for support

## Next Steps

### For Developers
- **Create your free GroqCloud account**: Access official API docs, the playground for experimentation, and more resources via [Groq Console](https://console.groq.com)
- **Build and customize**: Fork this repo and start customizing to build out your own application
- **Dive deep**: by learning more about Groq capabilities in [our documentation](https://console.groq.com/docs/overview).
- **Get support**: Connect with other developers building on Groq, chat with our team, and submit feature requests on our [Groq Developer Forum](https://community.groq.com)

### For Founders and Business Leaders
- **See enterprise capabilities**: This template showcases AI that can handle realtime business workloads
- **Discuss your needs**: [Contact our team](https://groq.com/enterprise-access/) to explore how Groq can accelerate your AI initiatives

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Credits
Created by Jordan Hagan. 