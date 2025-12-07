"""
Memo Review - Compare External Memos with vLogic Analysis

Allows reviewers to upload an existing memo prepared by someone else,
along with the source contract, and compare it with what vLogic would produce.
"""

import streamlit as st
import logging
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from shared.auth_utils import require_authentication, auth_manager, WEBSITE_URL
from shared.job_progress_monitor import check_and_resume_polling
from shared.subscription_manager import SubscriptionManager
from utils.document_extractor import DocumentExtractor

from asc606.step_analyzer import ASC606StepAnalyzer
from asc340.step_analyzer import ASC340StepAnalyzer
from asc842.step_analyzer import ASC842StepAnalyzer
from asc718.step_analyzer import ASC718StepAnalyzer
from asc805.step_analyzer import ASC805StepAnalyzer

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


def get_analyzer_for_standard(standard_key: str):
    """Get the appropriate analyzer based on ASC standard key."""
    analyzers = {
        'asc606': ASC606StepAnalyzer,
        'asc340': ASC340StepAnalyzer,
        'asc842': ASC842StepAnalyzer,
        'asc718': ASC718StepAnalyzer,
        'asc805': ASC805StepAnalyzer
    }
    analyzer_class = analyzers.get(standard_key, ASC606StepAnalyzer)
    return analyzer_class()


def deidentify_with_known_parties(text: str, vendor_name: str, customer_name: str, standard_key: str) -> str:
    """Apply de-identification using already-known party names."""
    try:
        analyzer = get_analyzer_for_standard(standard_key)
        result = analyzer.deidentify_contract_text(text, vendor_name, customer_name)
        if result.get('success'):
            return result['text']
        return text
    except Exception as e:
        logger.error(f"De-identification error: {e}")
        return text


def deidentify_text(contract_text: str, standard_key: str) -> Dict[str, Any]:
    """Apply de-identification to contract text using the appropriate analyzer."""
    try:
        analyzer = get_analyzer_for_standard(standard_key)
        parties = analyzer.extract_party_names_llm(contract_text)
        vendor_name = parties.get('vendor')
        customer_name = parties.get('customer')
        
        if not vendor_name and not customer_name:
            return {
                'success': False,
                'text': contract_text,
                'error': 'Could not identify contract parties',
                'vendor_name': None,
                'customer_name': None
            }
        
        result = analyzer.deidentify_contract_text(contract_text, vendor_name, customer_name)
        result['vendor_name'] = vendor_name
        result['customer_name'] = customer_name
        return result
        
    except Exception as e:
        logger.error(f"De-identification error: {e}")
        return {
            'success': False,
            'text': contract_text,
            'error': str(e),
            'vendor_name': None,
            'customer_name': None
        }


def display_completed_memo(memo_data: Dict[str, Any], asc_standard: str):
    """Display completed memo review results."""
    st.success("✅ **Memo Review Complete!** This AI-generated analysis requires review by qualified accounting professionals.")
    
    st.markdown(f"**Standard:** {asc_standard}")
    
    if memo_data.get('source_memo_filename'):
        st.markdown(f"**Reviewed Memo:** {memo_data.get('source_memo_filename')}")
    
    st.markdown("---")
    
    memo_content = memo_data.get('memo_content', '')
    if memo_content:
        st.markdown(memo_content, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("💾 Save Your Review")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Download as Word (.docx)",
                data=memo_content.encode('utf-8'),
                file_name=f"memo_review_{memo_data.get('memo_uuid', 'result')}.html",
                mime="text/html",
                use_container_width=True
            )
        with col2:
            if st.button("🔄 Start New Review", type="secondary", use_container_width=True):
                keys_to_clear = [k for k in st.session_state.keys() 
                               if isinstance(k, str) and ('_analysis_complete_' in k or '_memo_data_' in k or 'memo_review' in k.lower())]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
    else:
        st.error("Memo content not available")


def render_page():
    """Main page rendering function."""
    
    if not require_authentication():
        return
    
    # Initialize user session ID for memo persistence (same pattern as ASC pages)
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
    session_id = st.session_state.get('user_session_id', '')
    logger.info(f"Memo Review page load - session_id: {session_id[:8] if session_id else 'empty'}")
    
    prefix_map = {
        'ASC 606': 'asc606',
        'ASC 340-40': 'asc340',
        'ASC 718': 'asc718',
        'ASC 805': 'asc805',
        'ASC 842': 'asc842'
    }
    
    # Resume polling for any active analysis
    for asc_standard, asc_prefix in prefix_map.items():
        check_and_resume_polling(asc_standard=asc_standard, session_id=session_id)
    
    # Check for completed analysis in session state
    for asc_standard, asc_prefix in prefix_map.items():
        analysis_key = f'{asc_prefix}_analysis_complete_{session_id}'
        memo_key = f'{asc_prefix}_memo_data_{session_id}'
        
        logger.info(f"Checking {asc_standard}: analysis_key={analysis_key}, has_key={st.session_state.get(analysis_key, False)}")
        
        if st.session_state.get(analysis_key) and st.session_state.get(memo_key):
            memo_data = st.session_state.get(memo_key, {})
            st.title("Memo Review - Results")
            display_completed_memo(memo_data, asc_standard)
            return
    
    st.title("Memo Review")
    st.markdown("""
    Compare an existing memo with what vLogic would produce for the same contract.
    Upload the original contract and the memo you want to review.
    """)
    
    st.divider()
    
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
    detected_vendor = None
    detected_customer = None
    
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
        
        raw_contract_text = "\n\n---\n\n".join(all_contract_text)
        contract_word_count = total_words
        
        if contract_word_count > 0:
            with st.spinner("Applying privacy protection..."):
                deidentify_result = deidentify_text(raw_contract_text, standard_config['key'])
            
            if deidentify_result.get('success'):
                contract_text = deidentify_result['text']
                detected_vendor = deidentify_result.get('vendor_name')
                detected_customer = deidentify_result.get('customer_name')
                st.success("Privacy protection applied successfully")
                
                with st.container(border=True):
                    st.markdown("**Party names replaced:**")
                    if detected_vendor:
                        st.markdown(f"• Vendor: **\"{detected_vendor}\"** → **\"the Company\"**")
                    if detected_customer:
                        st.markdown(f"• Customer: **\"{detected_customer}\"** → **\"the Customer\"**")
            else:
                contract_text = raw_contract_text
                st.warning(f"Could not apply privacy protection: {deidentify_result.get('error', 'Unknown error')}. Proceeding with original text.")
            
            with st.expander(f"View Contract Text ({contract_word_count:,} words)", expanded=False):
                st.text_area("Contract content", contract_text[:5000] + ("..." if len(contract_text) > 5000 else ""), height=200, disabled=True)
    
    if memo_file:
        st.markdown("---")
        st.markdown("**Existing Memo Preview**")
        
        result = extract_document_text(memo_file)
        if result.get('success', False) or result.get('text'):
            raw_memo_text = result.get('text', '')
            memo_word_count = len(raw_memo_text.split())
            st.success(f"✅ {memo_file.name}: {memo_word_count:,} words extracted")
            
            if detected_vendor or detected_customer:
                memo_text = deidentify_with_known_parties(
                    raw_memo_text, 
                    detected_vendor, 
                    detected_customer, 
                    standard_config['key']
                )
                st.caption("Privacy protection applied using party names from contract")
            else:
                memo_text = raw_memo_text
            
            with st.expander(f"View Memo Text ({memo_word_count:,} words)", expanded=False):
                st.text_area("Memo content", memo_text[:5000] + ("..." if len(memo_text) > 5000 else ""), height=200, disabled=True)
        else:
            st.error(f"❌ {memo_file.name}: {result.get('error', 'Failed to extract')}")
    
    st.divider()
    
    can_proceed = contract_files and memo_file and contract_word_count > 0 and memo_word_count > 0
    
    total_words_to_charge = contract_word_count + memo_word_count
    
    if can_proceed:
        allowance_check = check_subscription_allowance(org_id, total_words_to_charge)
        
        if not allowance_check.get('allowed', False):
            st.error(f"{allowance_check.get('reason', 'Insufficient word allowance')}")
            can_proceed = False
        else:
            remaining_after = allowance_check.get('words_remaining_after', 0)
            st.info(f"This analysis will use **{total_words_to_charge:,} words** ({contract_word_count:,} contract + {memo_word_count:,} memo). You'll have {remaining_after:,} words remaining after.")
    
    st.subheader("3️⃣ Start Review")
    
    if not contract_files:
        st.caption("Upload the source contract to continue")
    elif not memo_file:
        st.caption("Upload the existing memo to compare")
    elif not can_proceed:
        st.caption("Please resolve the issues above to continue")
    else:
        if st.button("Analyze & Review", type="primary", use_container_width=True):
            from pages.memo_review_job_runner import submit_and_monitor_memo_review_job
            
            standard_key = standard_config['key']
            asc_standard_map = {
                'asc606': 'ASC 606',
                'asc340': 'ASC 340-40',
                'asc842': 'ASC 842',
                'asc718': 'ASC 718',
                'asc805': 'ASC 805'
            }
            asc_standard = asc_standard_map.get(standard_key, 'ASC 606')
            
            user_data = st.session_state.get('user_data', {})
            user_token = user_data.get('token', st.session_state.get('auth_token'))
            session_id = st.session_state.get('user_session_id', str(datetime.now().timestamp()))
            contract_filenames = [f.name for f in contract_files]
            memo_filename = memo_file.name if memo_file else 'Unknown'
            
            allowance_check['file_count'] = len(contract_filenames) + 1
            allowance_check['total_words'] = total_words_to_charge
            
            submit_and_monitor_memo_review_job(
                allowance_result=allowance_check,
                asc_standard=asc_standard,
                user_token=user_token,
                contract_text=contract_text,
                source_memo_text=memo_text,
                source_memo_filename=memo_filename,
                contract_filenames=contract_filenames,
                session_id=session_id,
                org_id=org_id,
                total_words=total_words_to_charge
            )


render_page()
