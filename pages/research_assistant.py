"""
ASC Research Assistant - Interactive Chat Interface

Provides conversational access to ASC guidance across all standards.
Users can ask questions and get authoritative answers with citations.

Using GPT-4o for main research answers and GPT4o-mini for follow-up suggestions.
"""

import streamlit as st
import openai
import os
import logging
import time
from typing import Dict, List, Optional, Tuple
from shared.knowledge_base import SharedKnowledgeBase

logger = logging.getLogger(__name__)

# Standard configurations
STANDARDS_CONFIG = {
    "ASC 606 - Revenue Recognition": {
        "database_path": "asc606_knowledge_base",
        "collection_name": "asc606_guidance",
        "description": "Revenue from Contracts with Customers"
    },
    "ASC 340-40 - Contract Costs": {
        "database_path": "asc340_knowledge_base", 
        "collection_name": "asc340_contract_costs",
        "description": "Contract Costs"
    },
    "ASC 805 - Business Combinations": {
        "database_path": "asc805_knowledge_base",
        "collection_name": "asc805_guidance",
        "description": "Business Combinations"
    },
    "ASC 842 - Leases": {
        "database_path": "asc842_knowledge_base",
        "collection_name": "asc842_leases", 
        "description": "Lease Accounting (Lessee)"
    }
}

class ASCResearchAssistant:
    """ASC Research Assistant for interactive guidance queries."""
    
    def __init__(self):
        """Initialize the research assistant."""
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # ===== MODEL CONFIGURATION (CHANGE HERE TO SWITCH MODELS) =====
        # Set use_premium_models to True for GPT-5/GPT-5-mini, False for GPT-4o/GPT-4o-mini
        self.use_premium_models = True
        
        # Model selection based on configuration
        if self.use_premium_models:
            self.main_model = "gpt-5"           # For main research answers
            self.light_model = "gpt-5-mini"     # For follow-up suggestions
        else:
            self.main_model = "gpt-4o"          # For main research answers  
            self.light_model = "gpt-4o-mini"    # For follow-up suggestions
    
    def get_response(self, question: str, selected_standard: str, debug_container=None) -> Tuple[str, List[str]]:
        """
        Get response to user question from selected ASC standard.
        
        Returns:
            Tuple of (answer, follow_up_suggestions)
        """
        try:
            # Get standard configuration
            if selected_standard not in STANDARDS_CONFIG:
                return "Please select a valid ASC standard.", []
            
            config = STANDARDS_CONFIG[selected_standard]
            
            # Initialize knowledge base for selected standard
            try:
                knowledge_base = SharedKnowledgeBase(
                    database_path=config["database_path"],
                    collection_name=config["collection_name"]
                )
            except Exception as e:
                return f"Knowledge base for {selected_standard} is not available. Please ensure the guidance has been processed.", []
            
            # Search for relevant guidance
            relevant_guidance = knowledge_base.search(question, max_results=10)
            
            # Generate response with citations
            guidance_tokens = len(relevant_guidance)//4
            chunk_count = len(relevant_guidance.split('Source:')) - 1
            
            # Show debug info in app if container provided
            if debug_container:
                debug_container.info(f"🔍 **RAG Debug**: Retrieved {chunk_count} relevant chunks ({len(relevant_guidance):,} chars ≈ {guidance_tokens:,} tokens)")
            
            answer = self._generate_answer(question, relevant_guidance, selected_standard)
            
            # Generate follow-up suggestions
            suggestions = self._generate_follow_ups(question, answer, selected_standard)
            
            return answer, suggestions
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}", []
    
    def _get_temperature(self, model_name=None):
        """Get appropriate temperature based on model."""
        target_model = model_name or self.main_model
        if target_model in ["gpt-5", "gpt-5-mini"]:
            return 1  # GPT-5 models only support default temperature of 1
        else:
            return 0.1  # GPT-4o models can use 0.1 for research consistency
    
    def _get_max_tokens_param(self, request_type="main", model_name=None):
        """Get appropriate max tokens parameter based on model and request type."""
        target_model = model_name or self.main_model
        if target_model in ["gpt-5", "gpt-5-mini"]:
            # GPT-5 models need much higher token counts for complex research tasks
            token_limits = {
                "main": 8000,        # Main research answers - increased for complex prompts
                "suggestions": 800   # Follow-up suggestions
            }
            return {"max_completion_tokens": token_limits.get(request_type, 8000)}
        else:
            # GPT-4o models use standard limits
            token_limits = {
                "main": 1000,        # Main research answers
                "suggestions": 200   # Follow-up suggestions
            }
            return {"max_tokens": token_limits.get(request_type, 1000)}

    def _generate_answer(self, question: str, guidance: str, standard: str) -> str:
        """Generate a comprehensive answer with citations."""
        
        prompt = f"""You are an expert accounting research assistant specializing in {standard}.

User Question: {question}

Relevant ASC Guidance:
{guidance}

Instructions:
1. Provide a concise but comprehensive answer (2-10 paragraphs)
2. Focus specifically on {standard} requirements
3. Include specific ASC paragraph citations in brackets [ASC XXX-XX-XX-XX]
4. Use professional accounting language
5. If the guidance doesn't fully address the question, acknowledge limitations
6. Structure the answer logically with clear conclusions

Answer:"""

        try:
            # Build request parameters
            request_params = {
                "model": self.main_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._get_temperature(self.main_model),
                **self._get_max_tokens_param("main", self.main_model)
            }
            
            # Add response_format only for GPT-5
            if self.main_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # Debug: Show what's actually happening
            print(f"🐛 API Response Debug:")
            print(f"   - Content length: {len(content) if content else 0}")
            print(f"   - Finish reason: {finish_reason}")
            print(f"   - Token limit used: {request_params.get('max_completion_tokens', request_params.get('max_tokens', 'unknown'))}")
            
            # Handle various error conditions
            if finish_reason == 'length':
                return f"⚠️ **Token Limit Reached**: The response was cut off. Current limit: {request_params.get('max_completion_tokens', request_params.get('max_tokens', 'unknown'))} tokens."
            
            if not content or content.strip() == '':
                return f"⚠️ **Empty Response**: Got empty response with finish_reason='{finish_reason}'. This might be a model issue."
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return f"Error generating answer: {str(e)}"
    
    def _generate_follow_ups(self, question: str, answer: str, standard: str) -> List[str]:
        """Generate relevant follow-up questions."""
        
        prompt = f"""Based on this accounting research exchange about {standard}, suggest 3-4 relevant follow-up questions that users commonly ask.

Original Question: {question}
Answer Provided: {answer}

Generate follow-up questions that are:
1. Directly related to {standard}
2. Natural extensions of the original question
3. Practical implementation focused
4. Short and clear (under 10 words each)

Return only the questions, one per line, without numbering or bullets."""

        try:
            # Build request parameters
            request_params = {
                "model": self.light_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._get_temperature(self.light_model),
                **self._get_max_tokens_param("suggestions", self.light_model)
            }
            
            # Add response_format only for GPT-5
            if self.light_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            suggestions = response.choices[0].message.content.strip().split('\n')
            return [s.strip() for s in suggestions if s.strip()][:4]  # Max 4 suggestions
            
        except Exception as e:
            logger.error(f"Error generating follow-ups: {str(e)}")
            return []

def render_research_assistant():
    """Render the ASC Research Assistant page."""
    
    # Page header
    st.title("🔍 ASC Research Assistant")
    with st.container(border=True):
        st.markdown("""
        :primary[**Ask questions about ASC standards and get instant answers with authoritative citations.**]
        
        Select your standard and ask anything - from basic concepts to complex implementation scenarios.
        """)
    
    # Initialize session state for chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'research_assistant' not in st.session_state:
        st.session_state.research_assistant = ASCResearchAssistant()
    
    # Standard selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_standard = st.selectbox(
            "📚 Select ASC Standard",
            options=list(STANDARDS_CONFIG.keys()),
            help="Choose which ASC standard you want to research"
        )
    
    with col2:
        if selected_standard:
            description = STANDARDS_CONFIG[selected_standard]["description"]
            st.info(f"**{selected_standard}**: {description}")
    
    # Question input (always visible for easy follow-ups)
    st.markdown("---")
    
    # Check for auto-filled question from suggestion click
    default_question = st.session_state.get('auto_question', '')
    if default_question:
        del st.session_state.auto_question  # Clear after use
    
    # Question input without repetitive header
    if st.session_state.chat_history:
        question_label = "💬 Ask a follow-up question:"
        placeholder_text = "e.g., Can you explain that in more detail?"
    else:
        question_label = "❓ Ask your question:"
        placeholder_text = "e.g., What are the key criteria for revenue recognition under ASC 606?"
    
    question = st.text_area(
        question_label,
        value=default_question,
        placeholder=placeholder_text,
        key="question_input"
    )
    
    # Submit button
    if st.button("🔍 Get Answer", type="primary", disabled=not question.strip()):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            # Show loading spinner with debug info
            with st.spinner(f"Searching {selected_standard} guidance..."):
                # Create debug info container
                debug_container = st.empty()
                # Get response with debug container
                answer, suggestions = st.session_state.research_assistant.get_response(
                    question, selected_standard, debug_container
                )
                
                # Clear debug info
                debug_container.empty()
                
                # Add to chat history
                timestamp = time.strftime("%I:%M %p")
                st.session_state.chat_history.append((
                    question, answer, suggestions, timestamp
                ))
                
                # Rerun to show the new response
                st.rerun()
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("## 💬 Conversation")
        
        for i, (user_q, assistant_response, suggestions, timestamp) in enumerate(st.session_state.chat_history):
            # User question
            with st.container():
                st.markdown(f"**You asked:** {user_q}")
                st.markdown(f"*{timestamp}*")
            
            # Assistant response
            with st.container(border=True):
                st.markdown(assistant_response)
                
                # Show follow-up suggestions as clickable buttons
                if suggestions:
                    st.markdown("**💡 Related questions:**")
                    cols = st.columns(min(len(suggestions), 2))
                    for j, suggestion in enumerate(suggestions):
                        with cols[j % 2]:
                            if st.button(suggestion, key=f"suggestion_{i}_{j}", use_container_width=True):
                                # Auto-fill the question input
                                st.session_state.auto_question = suggestion
                                st.rerun()
            
            st.markdown("")  # Spacing
    
    # Clear chat button
    if st.session_state.chat_history:
        st.markdown("---")
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

# Main execution
if __name__ == "__main__":
    render_research_assistant()
else:
    render_research_assistant()