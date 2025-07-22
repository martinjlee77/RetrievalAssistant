"""
LLM Utilities - Following Streamlit Best Practices
Handles OpenAI API calls, error handling, and caching
"""
import os
import streamlit as st
from openai import OpenAI
from typing import Dict, List, Any, Optional, Union
import json
import time

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    """Initialize and cache OpenAI client"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please check your secrets configuration.")
        st.stop()
    return OpenAI(api_key=api_key)

def make_llm_call(
    messages: List[Dict[str, str]], 
    model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
    temperature: float = 0.3,
    response_format: Optional[Dict] = None,
    max_tokens: Optional[int] = None
) -> Optional[str]:
    """
    Make LLM API call with error handling and rate limiting
    Following Streamlit best practices for API management
    """
    client = get_openai_client()
    
    try:
        with st.spinner("Analyzing with AI..."):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format=response_format if response_format else {"type": "text"},
                max_tokens=max_tokens
            )
        return response.choices[0].message.content
    
    except Exception as e:
        handle_llm_error(e)
        return None

def handle_llm_error(error: Exception):
    """Handle LLM API errors with user-friendly messages"""
    error_message = str(error).lower()
    
    if "rate limit" in error_message:
        st.error("⏱️ API rate limit reached. Please wait a moment and try again.")
    elif "quota" in error_message or "billing" in error_message:
        st.error("💳 API quota exceeded. Please check your OpenAI billing settings.")
    elif "invalid api key" in error_message or "unauthorized" in error_message:
        st.error("🔑 Invalid API key. Please check your OpenAI API key configuration.")
    elif "context length" in error_message or "token" in error_message:
        st.error("📄 Content too long. Please try with a shorter document or input.")
    else:
        st.error(f"🚫 AI service error: {str(error)}")
    
    # Log error for debugging (in production, send to logging service)
    if st.session_state.get("debug_mode", False):
        st.write(f"Debug info: {error}")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_llm_call(
    prompt: str, 
    system_message: str = None,
    model: str = "gpt-4o",
    temperature: float = 0.3
) -> Optional[str]:
    """
    Cached LLM call for frequently requested analysis
    Follows Streamlit best practices for caching expensive operations
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    
    return make_llm_call(messages, model, temperature)

def stream_llm_response(
    messages: List[Dict[str, str]], 
    model: str = "gpt-4o",
    temperature: float = 0.3
):
    """
    Stream LLM response for real-time display
    Uses st.write_stream for token-by-token display
    """
    client = get_openai_client()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        
        def response_generator():
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        
        return st.write_stream(response_generator())
    
    except Exception as e:
        handle_llm_error(e)
        return None

def get_model_options() -> Dict[str, str]:
    """Get available model options for debugging UI"""
    return {
        "GPT-4o (Latest)": "gpt-4o",
        "GPT-4o Mini": "gpt-4o-mini",
        "GPT-4 Turbo": "gpt-4-turbo-preview"
    }

def create_debug_sidebar():
    """
    Create debugging sidebar for prompt engineering
    Following Streamlit best practices for experimentation
    """
    with st.sidebar:
        st.subheader("🔧 AI Debug Controls")
        
        model_options = get_model_options()
        selected_model = st.selectbox(
            "Model",
            options=list(model_options.keys()),
            index=0
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.3,
            step=0.1,
            help="Higher values make output more creative but less focused"
        )
        
        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100,
            help="Maximum response length"
        )
        
        return {
            "model": model_options[selected_model],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

def validate_api_key() -> bool:
    """Validate OpenAI API key is properly configured"""
    try:
        client = get_openai_client()
        # Test with minimal API call
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        return True
    except Exception:
        return False