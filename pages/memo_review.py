"""
Memo Review - Compare External Memos with vLogic Analysis

Allows reviewers to upload an existing memo prepared by someone else,
along with the source contract, and compare it with what vLogic would produce.
"""

import streamlit as st
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from shared.auth_utils import require_authentication, auth_manager
from shared.subscription_manager import SubscriptionManager
from utils.document_extractor import DocumentExtractor

logger = logging.getLogger(__name__)

ASC_STANDARDS = {
    "ASC 606 - Revenue Recognition": {
        "key": "asc606",
        "description": "Revenue from Contracts with Customers",
        "analyzer_module": "asc606.step_analyzer",
        "analyzer_class": "ASC606StepAnalyzer"
    },
    "ASC 340-40 - Contract Costs": {
        "key": "asc340",
        "description": "Costs to Obtain a Contract",
        "analyzer_module": "asc340.step_analyzer",
        "analyzer_class": "ASC340StepAnalyzer"
    },
    "ASC 842 - Leases (Lessee)": {
        "key": "asc842",
        "description": "Lease Accounting",
        "analyzer_module": "asc842.step_analyzer",
        "analyzer_class": "ASC842StepAnalyzer"
    },
    "ASC 718 - Stock Compensation": {
        "key": "asc718",
        "description": "Share-Based Payment Transactions",
        "analyzer_module": "asc718.step_analyzer",
        "analyzer_class": "ASC718StepAnalyzer"
    },
    "ASC 805 - Business Combinations": {
        "key": "asc805",
        "description": "Business Combinations",
        "analyzer_module": "asc805.step_analyzer",
        "analyzer_class": "ASC805StepAnalyzer"
    }
}


def get_org_id_from_session() -> Optional[int]:
    """Get organization ID from authenticated user session."""
    user_data = st.session_state.get('user_data', {})
    return user_data.get('org_id')


def check_subscription_allowance(org_id: int, words_needed: int) -> Dict[str, Any]:
    """Check if organization has sufficient word allowance."""
    try:
        sub_manager = SubscriptionManager()
        result = sub_manager.check_word_allowance(org_id, words_needed)
        return result
    except Exception as e:
        logger.error(f"Error checking subscription allowance: {e}")
        return {
            'allowed': False,
            'reason': f'Error checking subscription: {str(e)}',
            'words_available': 0
        }


def extract_document_text(uploaded_file) -> Dict[str, Any]:
    """Extract text from uploaded document (PDF or DOCX)."""
    try:
        extractor = DocumentExtractor()
        result = extractor.extract_text(uploaded_file)
        return result
    except Exception as e:
        logger.error(f"Error extracting document: {e}")
        return {
            'success': False,
            'error': str(e),
            'text': '',
            'word_count': 0
        }


def render_page():
    """Main page rendering function."""
    
    st.title("📋 Memo Review")
    st.markdown("""
    Compare an existing memo with what vLogic would produce for the same contract.
    Upload the original contract and the memo you want to review.
    """)
    
    st.divider()
    
    if not auth_manager.is_authenticated():
        st.warning("🔒 Please log in to use Memo Review.")
        st.markdown("[Log in to your account](https://www.veritaslogic.ai/login.html)")
        return
    
    org_id = get_org_id_from_session()
    if not org_id:
        st.error("Unable to determine your organization. Please contact support.")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1️⃣ Select ASC Standard")
        selected_standard = st.selectbox(
            "Which standard does this memo cover?",
            options=list(ASC_STANDARDS.keys()),
            index=0,
            help="Select the accounting standard that applies to this analysis"
        )
        
        standard_config = ASC_STANDARDS[selected_standard]
        st.caption(f"*{standard_config['description']}*")
    
    with col2:
        st.subheader("📊 Your Word Allowance")
        try:
            sub_manager = SubscriptionManager()
            usage = sub_manager.get_current_usage(org_id)
            
            if usage.get('has_subscription'):
                words_available = usage.get('words_available', 0)
                plan_name = usage.get('plan_name', 'Unknown')
                st.metric("Available Words", f"{words_available:,}")
                st.caption(f"Plan: {plan_name}")
            else:
                st.warning("No active subscription")
        except Exception as e:
            st.caption("Unable to load usage info")
            logger.error(f"Error loading usage: {e}")
    
    st.divider()
    
    st.subheader("2️⃣ Upload Documents")
    
    upload_col1, upload_col2 = st.columns(2)
    
    with upload_col1:
        st.markdown("**Source Contract**")
        st.caption("The original contract/agreement to analyze")
        contract_files = st.file_uploader(
            "Upload contract document(s)",
            type=['pdf', 'docx', 'doc', 'txt'],
            accept_multiple_files=True,
            key="contract_upload",
            help="Upload the original contract that the memo is based on"
        )
    
    with upload_col2:
        st.markdown("**Existing Memo to Review**")
        st.caption("The memo you want to compare against vLogic")
        memo_file = st.file_uploader(
            "Upload existing memo",
            type=['pdf', 'docx', 'doc', 'txt'],
            accept_multiple_files=False,
            key="memo_upload",
            help="Upload the memo that was prepared by someone else"
        )
    
    contract_text = ""
    contract_word_count = 0
    memo_text = ""
    memo_word_count = 0
    
    if contract_files:
        st.markdown("---")
        st.markdown("**Contract Preview**")
        
        all_contract_text = []
        total_words = 0
        
        for uploaded_file in contract_files:
            result = extract_document_text(uploaded_file)
            if result.get('success', False) or result.get('text'):
                text = result.get('text', '')
                words = len(text.split())
                all_contract_text.append(text)
                total_words += words
                st.success(f"✅ {uploaded_file.name}: {words:,} words extracted")
            else:
                st.error(f"❌ {uploaded_file.name}: {result.get('error', 'Failed to extract')}")
        
        contract_text = "\n\n---\n\n".join(all_contract_text)
        contract_word_count = total_words
        
        if contract_word_count > 0:
            with st.expander(f"View Contract Text ({contract_word_count:,} words)", expanded=False):
                st.text_area("Contract content", contract_text[:5000] + ("..." if len(contract_text) > 5000 else ""), height=200, disabled=True)
    
    if memo_file:
        st.markdown("---")
        st.markdown("**Existing Memo Preview**")
        
        result = extract_document_text(memo_file)
        if result.get('success', False) or result.get('text'):
            memo_text = result.get('text', '')
            memo_word_count = len(memo_text.split())
            st.success(f"✅ {memo_file.name}: {memo_word_count:,} words extracted")
            
            with st.expander(f"View Memo Text ({memo_word_count:,} words)", expanded=False):
                st.text_area("Memo content", memo_text[:5000] + ("..." if len(memo_text) > 5000 else ""), height=200, disabled=True)
        else:
            st.error(f"❌ {memo_file.name}: {result.get('error', 'Failed to extract')}")
    
    st.divider()
    
    can_proceed = contract_files and memo_file and contract_word_count > 0 and memo_word_count > 0
    
    if can_proceed:
        allowance_check = check_subscription_allowance(org_id, contract_word_count)
        
        if not allowance_check.get('allowed', False):
            st.error(f"⚠️ {allowance_check.get('reason', 'Insufficient word allowance')}")
            st.info("Words are charged based on the contract document size only. The existing memo is not counted.")
            can_proceed = False
        else:
            remaining_after = allowance_check.get('words_remaining_after', 0)
            st.info(f"📊 This analysis will use **{contract_word_count:,} words**. You'll have {remaining_after:,} words remaining after.")
    
    st.subheader("3️⃣ Start Review")
    
    if not contract_files:
        st.caption("⏳ Upload the source contract to continue")
    elif not memo_file:
        st.caption("⏳ Upload the existing memo to compare")
    elif not can_proceed:
        st.caption("⚠️ Please resolve the issues above to continue")
    else:
        if st.button("🔍 Compare Memos", type="primary", use_container_width=True):
            st.session_state['memo_review_contract_text'] = contract_text
            st.session_state['memo_review_contract_words'] = contract_word_count
            st.session_state['memo_review_existing_memo'] = memo_text
            st.session_state['memo_review_standard'] = selected_standard
            st.session_state['memo_review_standard_key'] = standard_config['key']
            st.session_state['memo_review_org_id'] = org_id
            
            st.success("✅ Documents uploaded successfully!")
            st.info("🚧 **Phase 1 Checkpoint**: Document upload and extraction working. Background job processing coming in next phase.")
            
            with st.expander("Debug: Session State", expanded=False):
                st.json({
                    'standard': selected_standard,
                    'standard_key': standard_config['key'],
                    'contract_words': contract_word_count,
                    'memo_words': memo_word_count,
                    'org_id': org_id
                })


render_page()
