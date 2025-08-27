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
        "description": "Incremental Costs of Obtaining Contracts"
    },
    # Ready for future standards
    "ASC 842 - Leases": {
        "database_path": "asc842_knowledge_base",
        "collection_name": "asc842_guidance", 
        "description": "Lease Accounting"
    }
}

class ASCResearchAssistant:
    """ASC Research Assistant for interactive guidance queries."""
    
    def __init__(self):
        """Initialize the research assistant."""
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
    
    def get_response(self, question: str, selected_standard: str) -> Tuple[str, List[str]]:
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
            answer = self._generate_answer(question, relevant_guidance, selected_standard)
            
            # Generate follow-up suggestions
            suggestions = self._generate_follow_ups(question, answer, selected_standard)
            
            return answer, suggestions
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}", []
    
    def _generate_answer(self, question: str, guidance: str, standard: str) -> str:
        """Generate a comprehensive answer with citations."""
        
        prompt = f"""You are an expert accounting research assistant specializing in {standard}.

User Question: {question}

Relevant ASC Guidance:
{guidance}

Instructions:
1. Provide a concise but comprehensive answer (2-4 paragraphs)
2. Focus specifically on {standard} requirements
3. Include specific ASC paragraph citations in brackets [ASC XXX-XX-XX-XX]
4. Use professional accounting language
5. If the guidance doesn't fully address the question, acknowledge limitations
6. Structure the answer logically with clear conclusions

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
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
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use faster model for suggestions
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
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
    
    # Chat interface
    st.markdown("---")
    
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
    
    # Question input
    st.markdown("## ❓ Ask a Question")
    
    # Check for auto-filled question from suggestion click
    default_question = st.session_state.get('auto_question', '')
    if default_question:
        del st.session_state.auto_question  # Clear after use
    
    question = st.text_input(
        "Type your question about the selected ASC standard:",
        value=default_question,
        placeholder="e.g., What are the key criteria for revenue recognition under ASC 606?",
        key="question_input"
    )
    
    # Submit button
    if st.button("🔍 Get Answer", type="primary", disabled=not question.strip()):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            # Show loading spinner
            with st.spinner(f"Searching {selected_standard} guidance..."):
                # Get response
                answer, suggestions = st.session_state.research_assistant.get_response(
                    question, selected_standard
                )
                
                # Add to chat history
                timestamp = time.strftime("%I:%M %p")
                st.session_state.chat_history.append((
                    question, answer, suggestions, timestamp
                ))
                
                # Clear the input
                st.session_state.question_input = ""
                
                # Rerun to show the new response
                st.rerun()
    
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