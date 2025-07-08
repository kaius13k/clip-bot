"""
LLM Interface for AI Agent
Supports multiple AI providers for reasoning and text generation
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import openai
import anthropic


class LLMInterface:
    """
    Interface for interacting with Large Language Models
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('LLMInterface')
        
        # Model configuration
        self.model = config.get('agent', {}).get('model', 'gpt-4')
        self.max_tokens = config.get('agent', {}).get('max_tokens', 4000)
        self.temperature = config.get('agent', {}).get('temperature', 0.7)
        
        # API clients
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize clients based on available API keys
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AI API clients"""
        api_keys = self.config.get('api_keys', {})
        
        # OpenAI client
        if api_keys.get('openai'):
            try:
                openai.api_key = api_keys['openai']
                self.openai_client = openai
                self.logger.info("OpenAI client initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Anthropic client
        if api_keys.get('anthropic'):
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=api_keys['anthropic'])
                self.logger.info("Anthropic client initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Anthropic client: {e}")
    
    async def generate(self, prompt: str, model: str = None, max_tokens: int = None, 
                      temperature: float = None) -> str:
        """Generate text using the configured LLM"""
        
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        try:
            if model.startswith('gpt-') and self.openai_client:
                return await self._generate_openai(prompt, model, max_tokens, temperature)
            elif model.startswith('claude-') and self.anthropic_client:
                return await self._generate_anthropic(prompt, model, max_tokens, temperature)
            else:
                # Fallback to mock response if no API available
                return await self._generate_fallback(prompt)
                
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return f"Error generating response: {str(e)}"
    
    async def _generate_openai(self, prompt: str, model: str, max_tokens: int, 
                              temperature: float) -> str:
        """Generate using OpenAI API"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _generate_anthropic(self, prompt: str, model: str, max_tokens: int, 
                                 temperature: float) -> str:
        """Generate using Anthropic API"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return response.content[0].text.strip()
            
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise
    
    async def _generate_fallback(self, prompt: str) -> str:
        """Fallback response when no API is available"""
        self.logger.warning("Using fallback LLM response - no API keys configured")
        
        # Simple rule-based responses for common patterns
        prompt_lower = prompt.lower()
        
        if "analyze" in prompt_lower:
            return "Analysis: This appears to be a task requiring careful examination and breakdown into components."
        elif "plan" in prompt_lower:
            return "Plan: Step 1: Understand requirements. Step 2: Break down into subtasks. Step 3: Execute systematically."
        elif "search" in prompt_lower:
            return "Search strategy: Use relevant keywords and examine multiple sources for comprehensive information."
        elif "code" in prompt_lower:
            return "Code approach: Write clean, modular code with proper error handling and documentation."
        else:
            return f"I understand you're asking about: {prompt[:100]}... I'll approach this systematically and provide a thorough response."
    
    async def analyze_text(self, text: str, analysis_type: str = "general") -> Dict[str, Any]:
        """Analyze text for various purposes"""
        
        analysis_prompt = f"""
        Analyze the following text for {analysis_type} analysis:
        
        Text: {text}
        
        Please provide a structured analysis including:
        1. Main themes or topics
        2. Sentiment or tone
        3. Key entities or concepts
        4. Complexity level (1-10)
        5. Summary in one sentence
        
        Format your response as JSON.
        """
        
        try:
            response = await self.generate(analysis_prompt)
            # Try to parse as JSON, fallback to structured text
            import json
            return json.loads(response)
        except:
            return {
                "analysis_type": analysis_type,
                "raw_response": response,
                "complexity": 5
            }
    
    async def classify_intent(self, text: str, categories: List[str] = None) -> Dict[str, Any]:
        """Classify the intent of a given text"""
        
        categories = categories or [
            "question", "request", "command", "information", 
            "analysis", "creation", "modification", "deletion"
        ]
        
        intent_prompt = f"""
        Classify the intent of this text into one of these categories: {', '.join(categories)}
        
        Text: {text}
        
        Respond with JSON containing:
        - "intent": the most likely category
        - "confidence": confidence score 0-1
        - "reasoning": brief explanation
        """
        
        try:
            response = await self.generate(intent_prompt)
            import json
            return json.loads(response)
        except:
            return {
                "intent": "general",
                "confidence": 0.5,
                "reasoning": "Unable to parse classification"
            }
    
    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate a summary of the given text"""
        
        summary_prompt = f"""
        Summarize the following text in no more than {max_length} characters:
        
        {text}
        
        Summary:
        """
        
        summary = await self.generate(summary_prompt, max_tokens=100)
        return summary[:max_length] if summary else "Unable to generate summary"
    
    async def validate_json(self, json_text: str) -> Dict[str, Any]:
        """Validate and potentially fix JSON text"""
        
        try:
            import json
            return {"valid": True, "data": json.loads(json_text)}
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            validation_prompt = f"""
            Fix this JSON text to make it valid:
            
            {json_text}
            
            Return only the corrected JSON, nothing else.
            """
            
            try:
                fixed_json = await self.generate(validation_prompt, max_tokens=2000)
                return {"valid": True, "data": json.loads(fixed_json), "fixed": True}
            except:
                return {"valid": False, "error": str(e), "original": json_text}
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        models = []
        
        if self.openai_client:
            models.extend(['gpt-4', 'gpt-3.5-turbo'])
        
        if self.anthropic_client:
            models.extend(['claude-3-opus-20240229', 'claude-3-sonnet-20240229'])
        
        return models
    
    def is_available(self) -> bool:
        """Check if any LLM is available"""
        return self.openai_client is not None or self.anthropic_client is not None