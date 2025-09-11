"""
Request Memo Rerun Page
"""

import streamlit as st
import requests
import logging

logger = logging.getLogger(__name__)

def main():
    """Main function for the request rerun page"""
    
    st.title("🔄 Request Memo Rerun")
    
    with st.container(border=True):
        st.markdown("""
        **Need changes to an existing memo?** Submit your request below and we'll manually review and apply your $200 rerun credit.
        
        📋 **How it works:**
        1. Enter your Memo ID (found at the top of your memo)
        2. Describe what changes you need
        3. We'll review and apply your $200 rerun credit  
        4. Rerun the analysis yourself with the new credit
        """)
    
    with st.form("rerun_request_form"):
        st.markdown("### Request Details")
        
        # Memo ID input
        memo_id = st.text_input(
            "Memo ID *", 
            placeholder="e.g., MEM-23fdc477 or 23fdc477",
            help="Enter the Memo ID shown at the top of your analysis memo"
        )
        
        # Request type selection
        request_type = st.selectbox(
            "Request Type *",
            options=[
                "",
                "Change accounting methodology or approach",
                "Correct contract data or interpretation", 
                "Revise conclusions or judgments",
                "Formatting or presentation changes",
                "Add additional analysis or considerations",
                "Other (please specify in details)"
            ]
        )
        
        # Change details
        change_details = st.text_area(
            "Change Details *",
            placeholder="Describe the specific changes you need. Be as detailed as possible to ensure we understand your requirements.",
            height=150
        )
        
        # Urgency level
        urgency = st.selectbox(
            "Urgency Level",
            options=[
                "Standard (1-2 business days)",
                "High (Same day)", 
                "Urgent (Within 4 hours)"
            ]
        )
        
        # Submit button
        submitted = st.form_submit_button("Submit Rerun Request", use_container_width=True, type="primary")
        
        if submitted:
            # Validation
            if not memo_id or not request_type or not change_details:
                st.error("Please fill in all required fields (marked with *)")
                return
                
            # Prepare request data
            request_data = {
                'memoId': memo_id,
                'requestType': request_type,
                'changeDetails': change_details,
                'urgency': urgency
            }
            
            try:
                # Submit to backend
                response = requests.post(
                    'http://localhost:3000/api/submit-rerun-request',
                    json=request_data,
                    timeout=10
                )
                
                if response.ok:
                    st.success("✅ **Rerun request submitted successfully!** You will receive an email confirmation shortly. We'll review your request and apply the $200 rerun credit within 1-2 business days.")
                    
                    # Clear form by rerunning
                    st.balloons()
                    
                else:
                    st.error("❌ Error submitting request. Please try again or contact support directly.")
                    
            except Exception as e:
                logger.error(f"Rerun request submission error: {e}")
                st.error("❌ Network error. Please try again or contact support directly.")

if __name__ == "__main__":
    main()