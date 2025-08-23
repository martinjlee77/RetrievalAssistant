"""
ASC 606 Memo Display Page
"""

import streamlit as st
import logging
from datetime import datetime
from asc606.clean_memo_generator import CleanMemoGenerator

logger = logging.getLogger(__name__)


def render_memo_page():
    """Render the ASC 606 memo display page."""
    
    # Check if memo data exists in session state
    if not hasattr(st.session_state, 'asc606_memo_data'):
        st.error("No memo data found. Please complete an ASC 606 analysis first.")
        
        # Provide navigation back to analysis
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to ASC 606 Analysis", 
                        type="primary", 
                        use_container_width=True):
                st.switch_page("asc606/asc606_page.py")
        return
    
    # Get memo data from session state
    memo_data = st.session_state.asc606_memo_data
    memo_content = memo_data.get('memo_content', '')
    customer_name = memo_data.get('customer_name', 'Customer')
    analysis_title = memo_data.get('analysis_title', 'Contract Analysis')
    
    # Page header with navigation
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Back to Analysis", 
                    type="secondary",
                    help="Return to the ASC 606 analysis page"):
            st.switch_page("asc606/asc606_page.py")
    
    with col2:
        st.title("📋 ASC 606 Analysis Memo")
        st.markdown(f"**Customer:** {customer_name} | **Analysis:** {analysis_title}")
    
    with col3:
        if st.button("🔄 Analyze Another Contract", 
                    type="primary",
                    help="Start a new ASC 606 analysis"):
            # Clear current memo data and navigate back
            if hasattr(st.session_state, 'asc606_memo_data'):
                del st.session_state.asc606_memo_data
            st.switch_page("asc606/asc606_page.py")
    
    st.markdown("---")
    
    # Display the memo using the CleanMemoGenerator display method
    if memo_content:
        memo_generator = CleanMemoGenerator()
        memo_generator.display_clean_memo(memo_content)
    else:
        st.error("Memo content is empty. Please regenerate the analysis.")
        
        # Provide option to go back
        if st.button("← Return to Analysis", 
                    type="primary",
                    use_container_width=True):
            st.switch_page("asc606/asc606_page.py")


def main():
    """Main function called by Streamlit navigation."""
    render_memo_page()


if __name__ == "__main__":
    main()