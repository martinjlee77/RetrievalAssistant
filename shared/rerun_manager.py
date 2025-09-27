"""
Rerun Manager for VeritasLogic Platform
Simplified to redirect users to unified contact form
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)

class RerunManager:
    def __init__(self):
        pass  # No complex initialization needed anymore
    
    def add_rerun_button(self, memo_id: str) -> None:
        """
        Add rerun button to memo display
        
        Args:
            memo_id: The memo ID
        """
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.link_button(
                "📝 **Request Rerun**", 
                f"https://veritaslogic.ai/contact.html?memo_id={memo_id}&type=rerun",
                use_container_width=True,
                type="secondary"
            )
        
        with col2:
            if st.button("🔄 **Analyze Another Contract**", key=f"new_analysis_btn_{memo_id}", type="secondary", use_container_width=True):
                # Clear session state for new analysis
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 
                               any(term in k.lower() for term in ['analysis', 'memo', 'upload', 'file'])]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()