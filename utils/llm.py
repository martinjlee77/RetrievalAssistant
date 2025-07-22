"""
LLM Utilities - Following Streamlit Best Practices
Handles OpenAI API calls, error handling, and caching
"""
import os
import streamlit as st
from openai import OpenAI
from typing import Dict, List, Any, Optional, Union, cast
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
    response_format: Optional[Dict[str, Any]] = None,
    max_tokens: Optional[int] = None
) -> Optional[str]:
    """
    Make LLM API call with error handling and rate limiting
    Following Streamlit best practices for API management
    """
    client = get_openai_client()
    
    try:
        with st.spinner("Analyzing with AI..."):
            # Cast messages to proper type for OpenAI
            openai_messages = cast(List[Any], messages)
            response = client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
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
    
    result = make_llm_call(messages, model, temperature)
    return result if result else ""

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
        # Cast messages to proper type for OpenAI
        openai_messages = cast(List[Any], messages)
        response = client.chat.completions.create(
            model=model,
            messages=openai_messages,
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
        openai_messages = cast(List[Any], [{"role": "user", "content": "test"}])
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=openai_messages,
            max_tokens=5
        )
        return True
    except Exception:
        return False

def get_knowledge_base():
    """Get or initialize the ASC 606 knowledge base (consolidated from legacy file)"""
    # Import here to avoid circular imports
    import chromadb
    from chromadb.config import Settings
    import os
    
    persist_directory = "asc606_knowledge_base"
    
    try:
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        collection = client.get_or_create_collection(
            name="asc606_paragraphs",
            metadata={"description": "ASC 606 paragraphs with metadata filtering"},
            embedding_function=chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
        )
        return collection
    except Exception as e:
        st.error(f"Failed to load knowledge base: {e}")
        return None

def extract_contract_terms(
    client: OpenAI,
    contract_text: str, 
    step_context: str
) -> List[str]:
    """
    Extract contract-specific terms relevant to a particular ASC 606 step
    This makes semantic search more precise and adaptable
    """
    step_descriptions = {
        "contract_identification": "contract formation, enforceability, legal validity, agreement terms",
        "performance_obligations": "deliverables, services, goods, obligations, commitments, work to be performed",
        "transaction_price": "payment terms, pricing, fees, consideration, amounts, variable payments",
        "price_allocation": "allocation methods, relative values, standalone prices, bundling",
        "revenue_recognition": "timing, milestones, completion, transfer of control, satisfaction"
    }
    
    description = step_descriptions.get(step_context, "relevant contract terms")
    
    prompt = f"""Extract 5-7 key terms from this contract that are most relevant to {description}.

Focus on:
- Specific terminology used in this contract (not generic accounting terms)
- Industry-specific language
- Unique aspects of this arrangement
- Terms that would help find relevant ASC 606 guidance

Contract text:
{contract_text[:2000]}...

Return only the terms as a comma-separated list, no explanations."""

    try:
        openai_messages = cast(List[Any], [{"role": "user", "content": prompt}])
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,
            max_tokens=100,
            temperature=0.1
        )
        
        terms_text = response.choices[0].message.content.strip()
        terms = [term.strip() for term in terms_text.split(',')]
        return terms[:7]  # Limit to 7 terms max
        
    except Exception as e:
        st.warning(f"Could not extract contract terms: {e}")
        return []

def create_debug_sidebar() -> Dict[str, Any]:
    """Create debugging controls in sidebar for development"""
    with st.sidebar.expander("🔧 Debug Controls", expanded=False):
        st.markdown("**AI Model Settings**")
        
        model = st.selectbox(
            "Model",
            ["gpt-4o", "gpt-4o-mini", "gpt-4"],
            index=0,
            help="Choose AI model for analysis"
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="Controls creativity vs consistency"
        )
        
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100,
            help="Maximum response length"
        )
        
        st.markdown("**Development Tools**")
        
        debug_mode = st.checkbox(
            "Debug Mode",
            value=st.session_state.get("debug_mode", False),
            help="Show additional debugging information"
        )
        
        show_prompts = st.checkbox(
            "Show AI Prompts",
            value=st.session_state.get("show_prompts", False),
            help="Display prompts sent to AI"
        )
        
        show_raw_response = st.checkbox(
            "Show Raw AI Response",
            value=st.session_state.get("show_raw_response", False),
            help="Display unformatted AI responses"
        )
        
        # Store in session state
        st.session_state.debug_mode = debug_mode
        st.session_state.show_prompts = show_prompts
        st.session_state.show_raw_response = show_raw_response
        
        return {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "debug_mode": debug_mode,
            "show_prompts": show_prompts,
            "show_raw_response": show_raw_response
        }