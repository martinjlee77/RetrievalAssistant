"""
API Cost Tracker - Accurate OpenAI API cost estimation using token counting
"""

import tiktoken
import logging
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class APITracker:
    """Tracks OpenAI API costs using accurate token counting and current pricing"""
    
    # Current OpenAI pricing (as of September 2024)
    # Prices in USD per 1M tokens
    MODEL_PRICING = {
        # GPT-4o models
        "gpt-4o": {
            "input_per_1m": 5.00,
            "output_per_1m": 15.00
        },
        "gpt-4o-mini": {
            "input_per_1m": 0.15,
            "output_per_1m": 0.60
        },
        # GPT-5 models (estimated pricing)
        "gpt-5": {
            "input_per_1m": 10.00,
            "output_per_1m": 30.00
        },
        "gpt-5-mini": {
            "input_per_1m": 1.00,
            "output_per_1m": 3.00
        }
    }
    
    def __init__(self):
        self.total_cost = 0.0
        self.cost_breakdown = {}
        
    def calculate_tokens(self, text: str, model: str) -> int:
        """Calculate exact token count for given text and model"""
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Failed to get encoding for model {model}, using default: {e}")
            # Fallback to cl100k_base encoding (used by most OpenAI models)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
    
    def calculate_request_cost(self, messages: List[Dict[str, str]], response_text: str, model: str) -> float:
        """Calculate cost for a single API request"""
        
        if model not in self.MODEL_PRICING:
            logger.warning(f"Unknown model {model}, using gpt-4o pricing")
            model = "gpt-4o"
        
        # Calculate input tokens (all messages)
        input_text = ""
        for message in messages:
            input_text += message.get('content', '') + " "
        
        input_tokens = self.calculate_tokens(input_text, model)
        output_tokens = self.calculate_tokens(response_text, model)
        
        # Calculate costs
        pricing = self.MODEL_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
        
        total_cost = input_cost + output_cost
        
        # Log detailed breakdown
        logger.info(f"API Cost - Model: {model}, Input tokens: {input_tokens}, Output tokens: {output_tokens}, Cost: ${total_cost:.4f}")
        
        return total_cost
    
    def track_request(self, messages: List[Dict[str, str]], response_text: str, model: str, request_type: str = "analysis") -> float:
        """Track a single API request and add to running total"""
        
        cost = self.calculate_request_cost(messages, response_text, model)
        self.total_cost += cost
        
        # Track breakdown by request type
        if request_type not in self.cost_breakdown:
            self.cost_breakdown[request_type] = 0.0
        self.cost_breakdown[request_type] += cost
        
        logger.info(f"Tracked {request_type} request: ${cost:.4f} (Total: ${self.total_cost:.4f})")
        
        return cost
    
    def get_total_cost(self) -> float:
        """Get total accumulated cost"""
        return self.total_cost
    
    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get detailed cost breakdown by request type"""
        return self.cost_breakdown.copy()
    
    def reset(self):
        """Reset cost tracking for new analysis"""
        self.total_cost = 0.0
        self.cost_breakdown = {}
        logger.info("API cost tracker reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary"""
        return {
            "total_cost": round(self.total_cost, 4),
            "breakdown": {k: round(v, 4) for k, v in self.cost_breakdown.items()},
            "formatted_total": f"${self.total_cost:.4f}"
        }

def get_session_tracker() -> APITracker:
    """Get session-scoped API tracker to prevent cross-user cost leakage"""
    import streamlit as st
    if "api_cost_tracker" not in st.session_state:
        st.session_state.api_cost_tracker = APITracker()
    return st.session_state.api_cost_tracker

def reset_cost_tracking():
    """Reset cost tracking for current session"""
    tracker = get_session_tracker()
    tracker.reset()

def track_openai_request(messages: List[Dict[str, str]], response_text: str, model: str, request_type: str = "analysis") -> float:
    """
    Track an OpenAI API request and return the estimated cost
    
    Args:
        messages: List of messages sent to API
        response_text: Response text from API
        model: Model name used
        request_type: Type of request (e.g., "entity_extraction", "step_analysis", "memo_generation")
    
    Returns:
        Estimated cost in USD for this request
    """
    tracker = get_session_tracker()
    return tracker.track_request(messages, response_text, model, request_type)

def get_total_estimated_cost() -> float:
    """Get total estimated API cost for current analysis session"""
    tracker = get_session_tracker()
    return tracker.get_total_cost()

def get_cost_summary() -> Dict[str, Any]:
    """Get comprehensive cost summary for current analysis session"""
    tracker = get_session_tracker()
    return tracker.get_summary()