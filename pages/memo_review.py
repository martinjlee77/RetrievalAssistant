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
from shared.job_progress_monitor import check_and_resume_polling, resume_job_from_url, get_job_from_url
from shared.subscription_manager import SubscriptionManager
from utils.document_extractor import DocumentExtractor

from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.clean_memo_generator import CleanMemoGenerator as ASC606CleanMemoGenerator
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


def _extract_review_comments_section(memo_content: str) -> tuple:
    """
    Extract the review comments section from memo content.
    
    Returns:
        Tuple of (review_comments_html, vlogic_memo_html)
    """
    # Look for the review comments section marker
    review_marker = '<div class="review-comments-section"'
    
    if review_marker in memo_content:
        parts = memo_content.split(review_marker, 1)
        vlogic_memo = parts[0].strip()
        review_comments = review_marker + parts[1]
        return review_comments, vlogic_memo
    
    # No review comments found
    return None, memo_content


def _fix_review_comments_styling(review_html: str) -> str:
    """
    Fix review comments styling for dark background display.
    Replace blue colors with white for better visibility.
    """
    if not review_html:
        return review_html
    
    # Replace blue header colors with white
    fixed = review_html.replace('color: #1a365d;', 'color: #ffffff;')
    fixed = fixed.replace('color: #2d5a87;', 'color: #e0e0e0;')
    fixed = fixed.replace('color: #666;', 'color: rgba(255,255,255,0.8);')
    fixed = fixed.replace('border-top: 2px solid #1a365d;', 'border-top: 2px solid #4a7c59;')
    
    return fixed


def display_completed_memo(memo_data: Dict[str, Any], asc_standard: str):
    """Display completed memo review results."""
    st.success("✅ **Memo Review Complete!** This AI-generated analysis requires review by qualified accounting professionals.")
    
    st.markdown(f"**Standard:** {asc_standard}")
    
    if memo_data.get('source_memo_filename'):
        st.markdown(f"**Reviewed Memo:** {memo_data.get('source_memo_filename')}")
    
    st.markdown("---")
    
    memo_content = memo_data.get('memo_content', '')
    if memo_content:
        # Parse out the review comments and vLogic memo
        review_comments_html, vlogic_memo_html = _extract_review_comments_section(memo_content)
        
        # Display Review Comments FIRST (primary purpose of this page)
        if review_comments_html:
            st.subheader("📋 Review Comments")
            st.markdown("*Comparison of your uploaded memo against vLogic's independent analysis:*")
            
            # Fix styling for dark background
            fixed_review_html = _fix_review_comments_styling(review_comments_html)
            st.markdown(fixed_review_html, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Display vLogic Memo in collapsible section
        if vlogic_memo_html:
            with st.expander("📄 View vLogic's Independent Analysis", expanded=False):
                st.markdown("*This is the memo vLogic would generate for the same contract:*")
                st.markdown(vlogic_memo_html, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("💾 Save Your Review")
        st.info("**IMPORTANT:** Choose your preferred format to save this review before navigating away.")
        
        memo_generator = ASC606CleanMemoGenerator()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"memo_review_{timestamp}"
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Download full document (review + memo)
            docx_data = memo_generator._generate_docx(memo_content)
            if docx_data:
                st.download_button(
                    label="📄 Full Review (.docx)",
                    data=docx_data,
                    file_name=f"{base_filename}_full.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_docx_full_{hash(memo_content[:100]) if len(memo_content) > 100 else hash(memo_content)}",
                    use_container_width=True
                )
            else:
                st.button("📄 Full Review", disabled=True, use_container_width=True, help="Word generation failed")
        
        with col2:
            # Download just review comments
            if review_comments_html:
                review_docx_data = memo_generator._generate_docx(review_comments_html)
                if review_docx_data:
                    st.download_button(
                        label="💬 Comments Only (.docx)",
                        data=review_docx_data,
                        file_name=f"{base_filename}_comments.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"download_docx_comments_{hash(review_comments_html[:100]) if len(review_comments_html) > 100 else hash(review_comments_html)}",
                        use_container_width=True
                    )
                else:
                    st.button("💬 Comments Only", disabled=True, use_container_width=True, help="Word generation failed")
            else:
                st.button("💬 Comments Only", disabled=True, use_container_width=True, help="No review comments")
        
        with col3:
            st.download_button(
                label="📝 Markdown (.md)",
                data=memo_content.encode('utf-8'),
                file_name=f"{base_filename}.md",
                mime="text/markdown",
                key=f"download_md_review_{hash(memo_content[:100]) if len(memo_content) > 100 else hash(memo_content)}",
                use_container_width=True
            )
        
        with col4:
            if st.button("🔄 Start New Review", type="secondary", use_container_width=True):
                # Only clear review_* keys, not regular analysis keys
                keys_to_clear = [k for k in st.session_state.keys() 
                               if isinstance(k, str) and (k.startswith('review_') or 'memo_review' in k.lower())]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
    else:
        st.error("Memo content not available")


def load_analysis_from_db(analysis_id: int, user_token: str) -> Optional[Dict[str, Any]]:
    """Load an existing analysis from the database for viewing."""
    try:
        import requests
        response = requests.get(
            f'{WEBSITE_URL}/api/analysis/status/{analysis_id}',
            headers={'Authorization': f'Bearer {user_token}'},
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            if data.get('status') == 'completed' and data.get('memo_content'):
                return {
                    'memo_content': data['memo_content'],
                    'analysis_id': analysis_id,
                    'memo_uuid': data.get('memo_uuid'),
                    'asc_standard': data.get('asc_standard', 'ASC 606'),
                    'source_memo_filename': data.get('source_memo_filename'),
                    'analysis_type': data.get('analysis_type', 'review')
                }
        
        logger.error(f"Failed to load analysis {analysis_id}: {response.text if response else 'No response'}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading analysis from DB: {e}")
        return None


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
    
    # Check for persisted job in URL (survives page reloads)
    url_job = get_job_from_url()
    if url_job:
        logger.info(f"Found persisted job in URL, resuming: {url_job['job_id']}")
        # Determine ASC standard from URL or default to ASC 606 for review
        asc_standard = 'ASC 606'  # Default for memo review
        if resume_job_from_url(asc_standard, session_id):
            return  # Job is still running, polling resumed
    
    # Check if we're loading an existing analysis from history (via URL param)
    query_params = st.query_params
    analysis_id_param = query_params.get('analysis_id')
    
    if analysis_id_param:
        try:
            analysis_id_int = int(analysis_id_param)
            logger.info(f"Loading existing review from history: analysis_id={analysis_id_int}")
            
            # Try multiple sources for auth token
            user_token = st.session_state.get('auth_token') or st.session_state.get('user_data', {}).get('auth_token')
            
            if user_token:
                memo_data = load_analysis_from_db(analysis_id_int, user_token)
                if memo_data and memo_data.get('memo_content'):
                    asc_standard = memo_data.get('asc_standard', 'ASC 606')
                    st.title("Memo Review - Results")
                    display_completed_memo(memo_data, asc_standard)
                    return
                else:
                    logger.warning(f"Failed to load memo data for analysis_id={analysis_id_int}")
                    st.error("Unable to load the requested review. It may have been deleted or you don't have access.")
            else:
                logger.warning("No auth token available for loading analysis from history")
                st.error("Please log in to view this analysis.")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid analysis_id in URL: {analysis_id_param}, error: {e}")
            st.warning("Invalid analysis ID in URL")
    
    prefix_map = {
        'ASC 606': 'asc606',
        'ASC 340-40': 'asc340',
        'ASC 718': 'asc718',
        'ASC 805': 'asc805',
        'ASC 842': 'asc842'
    }
    
    # Resume polling for any active REVIEW analysis (not standard analysis)
    for asc_standard, asc_prefix in prefix_map.items():
        check_and_resume_polling(asc_standard=asc_standard, session_id=session_id, analysis_type='review')
    
    # Check for completed REVIEW analysis in session state (use review_* prefix)
    for asc_standard, asc_prefix in prefix_map.items():
        # Use review_ prefix to separate from regular analysis results
        review_prefix = f'review_{asc_prefix}'
        analysis_key = f'{review_prefix}_analysis_complete_{session_id}'
        memo_key = f'{review_prefix}_memo_data_{session_id}'
        
        logger.info(f"Checking {asc_standard}: analysis_key={analysis_key}, has_key={st.session_state.get(analysis_key, False)}")
        
        if st.session_state.get(analysis_key) and st.session_state.get(memo_key):
            memo_data = st.session_state.get(memo_key, {})
            st.title("Memo Review - Results")
            display_completed_memo(memo_data, asc_standard)
            return
    
    st.title("Memo Review")
    st.markdown("""
    Compare an user provided memo with what vLogic would produce for the same contract.
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
        st.markdown("**User Memo to Review**")
        st.caption("The memo you want to compare against vLogic")
        memo_file = st.file_uploader(
            "Upload your memo",
            type=['pdf', 'docx', 'doc', 'txt'],
            accept_multiple_files=False,
            key="memo_upload",
            help="Upload the memo that was prepared by someone else and needs to be reviewed"
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
        st.markdown("**User Memo Preview**")
        
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
        st.caption("Upload your memo to compare")
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
