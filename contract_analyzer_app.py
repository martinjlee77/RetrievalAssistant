import streamlit as st
import time
import json
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ValidationError
from simple_asc606_analyzer import SimpleASC606Analyzer
from document_extractor import DocumentExtractor


# --- CHANGE 4: Use Pydantic for robust data modeling ---
# This class defines the data structure for our contract inputs.
# It provides automatic validation and makes the code self-documenting.
class PerformanceObligation(BaseModel):
    name: str
    type: str  # License, Service, Good, etc.
    timing: str  # Point in Time, Over Time
    ssp: float  # Standalone selling price

class VariableConsideration(BaseModel):
    type: str  # Performance Bonus, Penalty, etc.
    estimated_amount: float

class ContractData(BaseModel):
    # Basic contract information
    analysis_title: str
    customer_name: str
    arrangement_description: str
    contract_start: date
    contract_end: date
    currency: str
    analysis_depth: str
    output_format: str
    include_citations: bool
    include_examples: bool
    additional_notes: Optional[str] = ""
    uploaded_file_name: str
    
    # New Trust, but Verify fields
    is_modification: bool = False
    performance_obligations: List[PerformanceObligation] = []
    fixed_consideration: float = 0.0
    variable_consideration: Optional[VariableConsideration] = None
    financing_component: bool = False
    material_rights: bool = False
    customer_options: bool = False
    
    # Legacy field for backward compatibility
    transaction_price: Optional[float] = None


# --- Main Application Class ---
class ContractAnalyzerApp:
    # --- CHANGE 5: Centralize app configuration ---
    APP_CONFIG = {
        'version': "1.1.0",
        'last_updated': "July 2025",
    }
    AVAILABLE_STANDARDS = {
        'ASC 606': {
            'name': 'Revenue from Contracts with Customers',
            'description':
            'Analyze revenue recognition under the 5-step model.',
            'status': 'available'
        },
        'ASC 842': {
            'name': 'Leases',
            'description': 'Analyze lease classification and measurement.',
            'status': 'coming_soon'
        },
        'ASC 815': {
            'name': 'Derivatives and Hedging',
            'description':
            'Analyze derivative instruments and hedging activities.',
            'status': 'coming_soon'
        },
        'ASC 326': {
            'name': 'Credit Losses',
            'description': 'Analyze current expected credit losses.',
            'status': 'coming_soon'
        }
    }

    def __init__(self):
        # Configure page settings
        st.set_page_config(page_title="Technical Accounting Analyzer",
                           page_icon="📄",
                           layout="wide",
                           initial_sidebar_state="expanded")
        # Initialize session state safely
        self.initialize_session_state()
        # Initialize analysis components with caching
        self.analyzer = self.get_cached_analyzer()
        self.extractor = DocumentExtractor()
        
        # Store RAG initialization status
        self.rag_status = "ready" if self.analyzer.authoritative_sources else "failed"

    @st.cache_resource
    def get_cached_analyzer(_self):
        """Get cached analyzer instance to prevent reinitialization on every input change"""
        return SimpleASC606Analyzer()

    def update_form_state(self):
        """Update form state without triggering full rerun"""
        pass

    def initialize_session_state(self):
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'contract_data' not in st.session_state:
            st.session_state.contract_data = None
        if 'selected_standard' not in st.session_state:
            st.session_state.selected_standard = 'ASC 606'
        if 'tab1_complete' not in st.session_state:
            st.session_state.tab1_complete = False
        if 'tab2_complete' not in st.session_state:
            st.session_state.tab2_complete = False

    def run(self):
        self.render_sidebar()

        st.title(
            f"📄 {st.session_state.selected_standard} - Revenue Contract Analyzer"
        )

        if st.session_state.analysis_results is None:
            self.render_upload_interface()
        else:
            self.render_analysis_results()

    def render_sidebar(self):
        with st.sidebar:
            st.header("📋 Accounting Standards")

            # Display currently selected standard
            current_standard = st.session_state.selected_standard
            current_info = self.AVAILABLE_STANDARDS[current_standard]
            st.success(f"✅ **{current_standard}**")
            st.write(f"*{current_info['description']}*")
            st.divider()

            # Selection for other standards
            st.subheader("Select Standard")
            for code, info in self.AVAILABLE_STANDARDS.items():
                if info['status'] == 'available':
                    if st.button(f"{code}: {info['name']}",
                                 key=f"select_{code}",
                                 disabled=(code == current_standard),
                                 use_container_width=True):
                        st.session_state.selected_standard = code
                        st.rerun()
                else:
                    # --- CHANGE 5: Cleaner display for "Coming Soon" ---
                    st.info(f"**{code}**\n\n*{info['name']}*\n\n(Coming Soon)",
                            icon="⏳")

            st.divider()
            st.subheader("ℹ️ System Information")
            st.caption(
                f"Version: {self.APP_CONFIG['version']}\n\nLast Updated: {self.APP_CONFIG['last_updated']}"
            )
            
            # RAG System Status
            st.subheader("📚 Knowledge Base")
            if self.analyzer.authoritative_sources:
                st.success("✅ Authoritative Sources Loaded")
                st.caption(f"Using {len(self.analyzer.authoritative_sources)} ASC 606 sources")
            else:
                st.error("❌ Sources Failed to Load")
                st.caption("Check ASC 606 files in attached_assets")

    def render_upload_interface(self):
        # --- CHANGE 3: Organize inputs into clear tabs ---
        # Dynamic tab status that updates immediately
        tab1, tab2, tab3, tab4 = st.tabs([
            "1. Contract Details", "2. Upload Document",
            "3. Preliminary Assessment", "4. Analysis Options (Optional)"
        ])

        with tab1:
            # Show completion status in tab content
            tab1_complete = bool(
                st.session_state.get('analysis_title', '')
                and st.session_state.get('customer_name', '')
                and st.session_state.get('arrangement_description', ''))
            status1 = "✅ Complete" if tab1_complete else "⚠️ Required fields missing"
            st.caption(status1)

            st.subheader("Key Contract Information")
            col1, col2 = st.columns(2)
            analysis_title = col1.text_input(
                "Analysis Title / Contract ID *",
                value=st.session_state.get('analysis_title', ''),
                placeholder="e.g., Q4 Project Phoenix SOW",
                help=
                "A unique, user-friendly name for this specific analysis. This allows you and the system to easily track and reference this specific contract memo.",
                key="analysis_title",
                on_change=self.update_form_state)
            customer_name = col2.text_input(
                "Customer Name *",
                value=st.session_state.get('customer_name', ''),
                placeholder="e.g., ABC Corporation",
                help=
                "The legal name of the customer. This is the most basic identifier for the counterparty and will be used throughout the memo.",
                key="customer_name")

            col3, col4, col5 = st.columns(3)
            contract_start = col3.date_input(
                "Contract Start Date *",
                value=st.session_state.get('contract_start', None),
                help=
                "The beginning of the period over which goods or services are expected to be delivered. This directly informs the revenue recognition period, especially for services recognized 'over time.'",
                key="contract_start")
            contract_end = col4.date_input(
                "Contract End Date *",
                value=st.session_state.get('contract_end', None),
                help=
                "The end of the period over which goods or services are expected to be delivered. This directly informs the revenue recognition period, especially for services recognized 'over time.'",
                key="contract_end")
            
            currency_options = [
                "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "Other"
            ]
            currency_index = currency_options.index(
                st.session_state.get(
                    'currency', 'USD')) if st.session_state.get(
                        'currency', 'USD') in currency_options else 0
            currency = col5.selectbox(
                "Currency *",
                currency_options,
                index=currency_index,
                help=
                "The currency of the contract. This is critical context for the transaction price and any financial figures mentioned in the memo.",
                key="currency")

            arrangement_description = st.text_area(
                "Brief Description of the Arrangement *",
                value=st.session_state.get('arrangement_description', ''),
                placeholder=
                "e.g., A three-year SaaS subscription with one-time implementation services.",
                height=100,
                help=
                "A one- or two-sentence, plain-English summary of the deal. This is a powerful input that gives the LLM immediate, high-level context of the business purpose, helping it better interpret the legal language and structure of the contract.",
                key="arrangement_description")

        with tab2:
            # Show completion status at the very top first - use session state for persistence
            tab2_complete = bool(st.session_state.get('uploaded_files_names', []))
            status2 = "✅ Complete" if tab2_complete else "⚠️ File upload required"
            st.caption(status2)

            st.subheader("Contract Documents")
            st.write("Upload up to 5 related documents (contract, invoices, change orders, etc.)")
            
            uploaded_files = st.file_uploader(
                "Upload your documents in PDF or Word format *",
                type=['pdf', 'docx', 'doc'],
                accept_multiple_files=True,
                key="uploaded_files",
                help="You can upload multiple files: main contract, invoices, change orders, amendments, etc.")

            # Handle multiple files and enforce limit
            if uploaded_files:
                if len(uploaded_files) > 5:
                    st.error("❌ Please upload a maximum of 5 files at once.")
                    st.session_state.uploaded_files_names = []
                else:
                    st.session_state.uploaded_files_names = [f.name for f in uploaded_files]
                    st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully:")
                    for i, file in enumerate(uploaded_files, 1):
                        st.write(f"{i}. {file.name}")
            elif 'uploaded_files_names' not in st.session_state:
                st.session_state.uploaded_files_names = []

        with tab3:
            st.subheader("📋 Preliminary Assessment")
            st.write("Provide your initial analysis - the AI will verify against the contract text")
            
            # Contract modification section
            st.subheader("Contract Nature")
            is_modification = st.checkbox(
                "Is this a contract modification or amendment?",
                value=st.session_state.get('is_modification', False),
                help="Check if this contract modifies or amends an existing agreement",
                key="is_modification"
            )
            
            # Performance obligations section
            st.subheader("Performance Obligations")
            st.write("Identify the distinct performance obligations in this contract:")
            
            # Initialize performance obligations in session state if not exists
            if 'performance_obligations' not in st.session_state:
                st.session_state.performance_obligations = []
            
            # Add new performance obligation
            with st.expander("Add Performance Obligation"):
                col1, col2 = st.columns(2)
                new_po_name = col1.text_input("Performance Obligation Name", placeholder="e.g., Software License")
                new_po_type = col2.selectbox("Type", ["License", "Service", "Good", "Other"])
                
                col3, col4 = st.columns(2)
                new_po_timing = col3.selectbox("Recognition Timing", ["Point in Time", "Over Time"])
                new_po_ssp = col4.number_input("Standalone Selling Price", min_value=0.0, format="%.2f")
                
                if st.button("Add Performance Obligation"):
                    if new_po_name and new_po_ssp > 0:
                        st.session_state.performance_obligations.append({
                            'name': new_po_name,
                            'type': new_po_type,
                            'timing': new_po_timing,
                            'ssp': new_po_ssp
                        })
                        st.success(f"Added: {new_po_name}")
                        st.rerun()
            
            # Display current performance obligations
            if st.session_state.performance_obligations:
                st.write("**Current Performance Obligations:**")
                for i, po in enumerate(st.session_state.performance_obligations):
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"**{po['name']}** ({po['type']}) - {po['timing']} - {currency} {po['ssp']:,.2f}")
                    if col2.button("Remove", key=f"remove_po_{i}"):
                        st.session_state.performance_obligations.pop(i)
                        st.rerun()
            
            # Transaction price section
            st.subheader("Transaction Price")
            col1, col2 = st.columns(2)
            
            fixed_consideration = col1.number_input(
                "Fixed Consideration",
                value=st.session_state.get('fixed_consideration', 0.0),
                min_value=0.0,
                format="%.2f",
                help="The guaranteed, fixed amount in the contract",
                key="fixed_consideration"
            )
            
            has_variable = col2.checkbox(
                "Has Variable Consideration?",
                value=st.session_state.get('has_variable_consideration', False),
                key="has_variable_consideration"
            )
            
            if has_variable:
                col3, col4 = st.columns(2)
                variable_type = col3.selectbox(
                    "Variable Consideration Type",
                    ["Performance Bonus", "Penalty", "Usage-based", "Other"],
                    key="variable_type"
                )
                variable_amount = col4.number_input(
                    "Estimated Variable Amount",
                    value=st.session_state.get('variable_amount', 0.0),
                    min_value=0.0,
                    format="%.2f",
                    key="variable_amount"
                )
            
            # Additional elements
            st.subheader("Additional Elements")
            col1, col2 = st.columns(2)
            
            financing_component = col1.checkbox(
                "Significant Financing Component?",
                value=st.session_state.get('financing_component', False),
                key="financing_component"
            )
            
            material_rights = col2.checkbox(
                "Material Rights Present?",
                value=st.session_state.get('material_rights', False),
                key="material_rights"
            )

        with tab4:
            st.subheader("Analysis Configuration")
            col7, col8 = st.columns(2)
            analysis_depth = col7.selectbox(
                "Analysis Depth", ["Standard Analysis", "Detailed Analysis"])
            output_format = col8.selectbox(
                "Output Format", ["Professional Memo", "Executive Summary"])

            col7.markdown("<br>", unsafe_allow_html=True)  # Spacer
            include_citations = col7.checkbox("Include Citations", value=True)
            include_examples = col8.checkbox("Include Examples", value=False)

            additional_notes = st.text_area(
                "Additional Instructions (Optional)",
                placeholder=
                "e.g., Focus specifically on variable consideration and the series guidance.",
                height=100)

        # Check completion status for button styling and text
        tab1_ready = bool(analysis_title and customer_name
                          and arrangement_description)
        tab2_ready = bool(uploaded_files)
        both_tabs_ready = tab1_ready and tab2_ready

        # Button appearance changes based on readiness
        if both_tabs_ready:
            button_text = "📋 Analyze Contract"
            button_type = "primary"
            button_help = "All required fields completed - ready to analyze!"
        else:
            button_text = "📋 Complete Required Fields First to Enable Analysis"
            button_type = "secondary"
            button_help = "Please complete tabs 1 and 2 before analyzing"

        submitted = st.button(button_text,
                              type=button_type,
                              use_container_width=True,
                              help=button_help)

        # Small helper text at bottom
        st.caption(
            "* Required fields — Complete tabs 1 and 2 to enable analysis")

        if submitted:
            # --- CHANGE 4: Validate inputs using Pydantic model ---
            try:
                # Check all required fields are completed
                missing_fields = []
                if not analysis_title.strip():
                    missing_fields.append("Analysis Title")
                if not customer_name.strip():
                    missing_fields.append("Customer Name")
                if not arrangement_description.strip():
                    missing_fields.append("Brief Description")
                if not uploaded_files:
                    missing_fields.append("Contract Documents")

                if missing_fields:
                    st.error(
                        f"Please complete the following required fields: {', '.join(missing_fields)}"
                    )
                    st.warning(
                        "💡 **Tip:** Make sure to fill out both Tab 1 (Contract Details) and Tab 2 (Upload Document)"
                    )
                    return

                # Create performance obligations list
                performance_obligations = []
                for po in st.session_state.get('performance_obligations', []):
                    performance_obligations.append(PerformanceObligation(
                        name=po['name'],
                        type=po['type'],
                        timing=po['timing'],
                        ssp=po['ssp']
                    ))
                
                # Create variable consideration if applicable
                variable_consideration = None
                if st.session_state.get('has_variable_consideration', False):
                    variable_consideration = VariableConsideration(
                        type=st.session_state.get('variable_type', 'Performance Bonus'),
                        estimated_amount=st.session_state.get('variable_amount', 0.0)
                    )
                
                # Create an instance of our Pydantic model
                contract_data = ContractData(
                    analysis_title=analysis_title,
                    customer_name=customer_name,
                    contract_start=contract_start,
                    contract_end=contract_end,
                    transaction_price=st.session_state.get('fixed_consideration', 0.0),  # Use fixed consideration from Tab 3
                    currency=currency,
                    arrangement_description=arrangement_description,
                    uploaded_file_name=", ".join([f.name for f in uploaded_files]),
                    analysis_depth=analysis_depth,
                    output_format=output_format,
                    include_citations=include_citations,
                    include_examples=include_examples,
                    additional_notes=additional_notes,
                    # New Trust, but Verify fields
                    is_modification=st.session_state.get('is_modification', False),
                    performance_obligations=performance_obligations,
                    fixed_consideration=st.session_state.get('fixed_consideration', 0.0),
                    variable_consideration=variable_consideration,
                    financing_component=st.session_state.get('financing_component', False),
                    material_rights=st.session_state.get('material_rights', False)
                )
                # Store the validated data model in session state
                st.session_state.contract_data = contract_data
                self.process_contract(uploaded_files)

            except ValidationError as e:
                # Pydantic raises an error if fields are missing or types are wrong
                st.error("Please fill in all required fields marked with *")
                # For debugging, you can print the detailed error:
                # st.error(e)

            # --- CHANGE 1: BUG FIX ---
            # The original code had a NameError because `effective_date` wasn't defined.
            # This is now prevented by using the Pydantic model, which only includes defined fields.

    def process_contract(self, uploaded_files):
        with st.spinner("Analyzing contract documents... This may take a moment."):
            start_time = time.time()
            
            try:
                # Step 1: Extract text from all documents
                st.info(f"📄 Extracting text from {len(uploaded_files)} document(s)...")
                
                all_extracted_text = []
                all_metadata = []
                
                for i, uploaded_file in enumerate(uploaded_files, 1):
                    st.write(f"Processing file {i}/{len(uploaded_files)}: {uploaded_file.name}")
                    
                    extraction_result = self.extractor.extract_text(uploaded_file)
                    
                    if extraction_result.get('error'):
                        st.error(f"Document extraction failed for {uploaded_file.name}: {extraction_result['error']}")
                        continue
                    
                    # Add file identifier to the text
                    file_text = f"\n\n=== DOCUMENT {i}: {uploaded_file.name} ===\n{extraction_result['text']}\n=== END DOCUMENT {i} ===\n"
                    all_extracted_text.append(file_text)
                    all_metadata.append({
                        'filename': uploaded_file.name,
                        'extraction_method': extraction_result.get('method', 'unknown'),
                        'word_count': extraction_result.get('word_count', 0),
                        'char_count': len(extraction_result.get('text', ''))
                    })
                
                if not all_extracted_text:
                    st.error("❌ No documents could be processed successfully.")
                    return
                
                # Combine all extracted text
                combined_text = "\n".join(all_extracted_text)
                
                # Step 2: Create combined extraction result
                combined_extraction = {
                    'text': combined_text,
                    'method': 'multi-document',
                    'word_count': sum(meta['word_count'] for meta in all_metadata),
                    'files_processed': len(all_extracted_text),
                    'files_metadata': all_metadata
                }
                
                # Step 3: Validate extraction quality
                validation = self.extractor.validate_extraction(combined_extraction)
                if not validation['is_valid']:
                    st.warning("⚠️ Document extraction quality issues detected:")
                    for issue in validation['issues']:
                        st.write(f"• {issue}")
                    
                    if not st.button("Continue with analysis anyway"):
                        return
                
                # Step 4: Perform ASC 606 analysis
                st.info("🔍 Performing ASC 606 analysis...")
                contract_data = st.session_state.contract_data.__dict__
                analysis_result = self.analyzer.analyze_contract(
                    combined_extraction['text'], 
                    contract_data
                )
                
                # Step 5: Quality validation
                st.info("✅ Validating analysis quality...")
                quality_result = self.analyzer.validate_analysis_quality(analysis_result)
                
                processing_time = time.time() - start_time
                
                # Store results
                st.session_state.analysis_results = {
                    'asc606_analysis': analysis_result,
                    'quality_validation': quality_result,
                    'extraction_info': combined_extraction,
                    'processing_time': processing_time,
                    'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                st.success(f"✅ Contract analysis completed! Processed {len(uploaded_files)} document(s).")
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                st.error("Please check your document and try again.")
                return
        
        st.rerun()

    def render_analysis_results(self):
        st.header("📊 Analysis Results")

        contract: ContractData = st.session_state.contract_data
        results = st.session_state.analysis_results

        # Display key metrics with source transparency
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Analysis Type", st.session_state.selected_standard)
        col2.metric("Processing Time", f"{results['processing_time']:.1f}s")
        col3.metric("Quality Score", f"{results['quality_validation']['quality_score']}/100")
        
        # Source transparency metrics
        analysis_result = results['asc606_analysis']
        source_transparency = getattr(analysis_result, 'source_transparency', {})
        
        authoritative_count = len(source_transparency.get('authoritative_sources_used', []))
        interpretative_count = len(source_transparency.get('interpretative_sources_used', []))
        general_knowledge_count = len(source_transparency.get('general_knowledge_areas', []))
        
        # Check citations as fallback indicator
        citations = getattr(analysis_result, 'citations', [])
        has_citations = len(citations) > 0
        
        col4.metric("Source Quality", 
                   "Authoritative" if authoritative_count > 0 or has_citations else 
                   "Interpretative" if interpretative_count > 0 else 
                   "General Knowledge")
        
        # Source transparency alert
        if general_knowledge_count > 0:
            st.warning(f"⚠️ {general_knowledge_count} analysis areas used general knowledge fallback")
            with st.expander("View General Knowledge Areas"):
                for area in source_transparency.get('general_knowledge_areas', []):
                    st.write(f"• {area}")
        else:
            st.success("✅ Analysis based on authoritative and interpretative sources")

        # Display a summary of the inputs
        with st.expander("Show Original Contract Details", expanded=False):
            st.write(f"**Analysis Title:** {contract.analysis_title}")
            st.write(f"**Customer:** {contract.customer_name}")
            st.write(
                f"**Contract Period:** {contract.contract_start.strftime('%b %d, %Y')} to {contract.contract_end.strftime('%b %d, %Y')}"
            )
            st.write(
                f"**Transaction Price:** {contract.currency} {contract.transaction_price:,.2f}"
            )
            st.write(f"**File:** {contract.uploaded_file_name}")

        # Display ASC 606 analysis results
        analysis = results['asc606_analysis']
        quality = results['quality_validation']
        
        # Quality indicator
        if quality['quality_score'] >= 80:
            st.success(f"✅ High Quality Analysis (Score: {quality['quality_score']}/100)")
        elif quality['quality_score'] >= 60:
            st.warning(f"⚠️ Moderate Quality Analysis (Score: {quality['quality_score']}/100)")
        else:
            st.error(f"❌ Low Quality Analysis (Score: {quality['quality_score']}/100)")

        # NEW: Trust, but Verify Reconciliation Analysis
        reconciliation = getattr(analysis, 'reconciliation_analysis', {})
        if reconciliation and (reconciliation.get('confirmations') or reconciliation.get('discrepancies')):
            st.subheader("🔍 Trust, but Verify Reconciliation")
            
            # Confirmations
            confirmations = reconciliation.get('confirmations', [])
            if confirmations:
                st.success(f"✅ {len(confirmations)} items confirmed")
                with st.expander("View Confirmations"):
                    for conf in confirmations:
                        st.write(f"**{conf.get('area', 'Unknown')}:** {conf.get('detail', 'No detail')}")
            
            # Discrepancies
            discrepancies = reconciliation.get('discrepancies', [])
            if discrepancies:
                st.warning(f"⚠️ {len(discrepancies)} discrepancies found")
                with st.expander("View Discrepancies and AI Corrections", expanded=True):
                    for i, disc in enumerate(discrepancies, 1):
                        st.write(f"**Discrepancy {i}: {disc.get('area', 'Unknown')}**")
                        st.write(f"*Your Input:* {disc.get('user_input', 'No input recorded')}")
                        st.write(f"*AI Recommendation:* {disc.get('ai_recommendation', 'No recommendation')}")
                        st.write(f"*Rationale:* {disc.get('rationale', 'No rationale provided')}")
                        if disc.get('supporting_quote'):
                            st.code(f"Contract Quote: {disc['supporting_quote']}")
                        st.divider()
            
            if not confirmations and not discrepancies:
                st.info("No preliminary assessment data to reconcile")
        
        # ASC 606 Five-Step Analysis
        st.subheader("🔍 ASC 606 Five-Step Analysis")
        step1, step2, step3, step4, step5 = st.tabs([
            "Step 1: Contract", "Step 2: Performance Obligations", "Step 3: Transaction Price",
            "Step 4: Price Allocation", "Step 5: Revenue Recognition"
        ])
        
        with step1:
            step1_data = analysis.step1_contract_identification
            st.write("**Contract Identification Analysis**")
            st.write(f"**Contract Exists:** {'Yes' if step1_data.get('contract_exists') else 'No'}")
            st.write(f"**Rationale:** {step1_data.get('rationale', 'Not provided')}")
            st.write(f"**Combination Required:** {'Yes' if step1_data.get('combination_required') else 'No'}")
            st.write(f"**Modifications Present:** {'Yes' if step1_data.get('modifications_present') else 'No'}")
            
            if step1_data.get('key_findings'):
                st.write("**Key Findings:**")
                for finding in step1_data['key_findings']:
                    st.write(f"• {finding}")
        
        with step2:
            step2_data = analysis.step2_performance_obligations
            st.write("**Performance Obligations Analysis**")
            
            if step2_data.get('identified_obligations'):
                st.write("**Identified Performance Obligations:**")
                for i, obligation in enumerate(step2_data['identified_obligations'], 1):
                    st.write(f"{i}. {obligation}")
            
            st.write(f"**Distinctness Analysis:** {step2_data.get('distinctness_analysis', 'Not provided')}")
            st.write(f"**Principal vs Agent Analysis:** {step2_data.get('principal_agent_analysis', 'Not provided')}")
            
            if step2_data.get('key_judgments'):
                st.write("**Key Judgments:**")
                for judgment in step2_data['key_judgments']:
                    st.write(f"• {judgment}")
        
        with step3:
            step3_data = analysis.step3_transaction_price
            st.write("**Transaction Price Analysis**")
            
            if step3_data.get('fixed_consideration'):
                st.write(f"**Fixed Consideration:** {contract.currency} {step3_data['fixed_consideration']:,.2f}")
            
            st.write(f"**Variable Consideration:** {step3_data.get('variable_consideration', 'Not provided')}")
            st.write(f"**Constraint Analysis:** {step3_data.get('constraint_analysis', 'Not provided')}")
            st.write(f"**Financing Components:** {step3_data.get('financing_components', 'Not provided')}")
            
            if step3_data.get('key_estimates'):
                st.write("**Key Estimates:**")
                for estimate in step3_data['key_estimates']:
                    st.write(f"• {estimate}")
        
        with step4:
            step4_data = analysis.step4_price_allocation
            st.write("**Price Allocation Analysis**")
            
            st.write(f"**Allocation Method:** {step4_data.get('allocation_method', 'Not provided')}")
            
            if step4_data.get('standalone_selling_prices'):
                st.write("**Standalone Selling Prices:**")
                ssp = step4_data['standalone_selling_prices']
                if isinstance(ssp, dict):
                    for obligation, price in ssp.items():
                        st.write(f"• {obligation}: {price}")
                else:
                    st.write(f"• {ssp}")
            
            if step4_data.get('key_assumptions'):
                st.write("**Key Assumptions:**")
                for assumption in step4_data['key_assumptions']:
                    st.write(f"• {assumption}")
        
        with step5:
            step5_data = analysis.step5_revenue_recognition
            st.write("**Revenue Recognition Analysis**")
            
            st.write(f"**Recognition Pattern:** {step5_data.get('recognition_pattern', 'Not provided')}")
            st.write(f"**Control Transfer Analysis:** {step5_data.get('control_transfer_analysis', 'Not provided')}")
            st.write(f"**Timing Determination:** {step5_data.get('timing_determination', 'Not provided')}")
            
            if step5_data.get('implementation_steps'):
                st.write("**Implementation Steps:**")
                for i, step in enumerate(step5_data['implementation_steps'], 1):
                    st.write(f"{i}. {step}")

        # Professional memo section
        st.subheader("📋 Premium Professional Memo")
        
        # Show memo preview with key sections
        memo_text = analysis.professional_memo
        if memo_text:
            # Extract key sections for preview
            if "Executive Summary" in memo_text:
                summary_start = memo_text.find("Executive Summary")
                summary_end = memo_text.find("\n\n", summary_start + 50)
                if summary_end > summary_start:
                    summary = memo_text[summary_start:summary_end]
                    st.info(f"📝 **Memo Preview:**\n{summary[:300]}...")
            
            # Display memo structure
            sections = []
            if "Executive Summary" in memo_text:
                sections.append("Executive Summary")
            if "Background of the Arrangement" in memo_text:
                sections.append("Background of the Arrangement")
            if "Detailed ASC 606 Five-Step Analysis" in memo_text:
                sections.append("Detailed ASC 606 Five-Step Analysis")
            if "Key Judgments and Estimates" in memo_text:
                sections.append("Key Judgments and Estimates")
            if "Financial & Operational Impact" in memo_text:
                sections.append("Financial & Operational Impact")
            if "Illustrative Journal Entries" in memo_text:
                sections.append("Illustrative Journal Entries")
            if "Conclusion" in memo_text:
                sections.append("Conclusion")
            
            if sections:
                st.success(f"✅ **Premium Memo Structure:** {', '.join(sections)}")
            
        with st.expander("View Complete Professional Memo", expanded=False):
            st.text_area("Audit-Ready Professional Accounting Memo", 
                        value=analysis.professional_memo, 
                        height=600, 
                        disabled=True)

        # Export options
        st.subheader("📥 Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Download Professional Memo", use_container_width=True):
                st.download_button(
                    label="Download Memo as Text",
                    data=analysis.professional_memo,
                    file_name=f"ASC606_Analysis_{contract.analysis_title.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
        
        with col2:
            if st.button("📊 Download Full Analysis", use_container_width=True):
                full_analysis = {
                    'contract_data': contract.__dict__,
                    'analysis_results': analysis.__dict__,
                    'quality_assessment': quality
                }
                st.download_button(
                    label="Download Analysis as JSON",
                    data=json.dumps(full_analysis, indent=2, default=str),
                    file_name=f"ASC606_Full_Analysis_{contract.analysis_title.replace(' ', '_')}.json",
                    mime="application/json"
                )

        st.divider()
        if st.button("🔄 Analyze Another Contract", use_container_width=True):
            st.session_state.analysis_results = None
            st.session_state.contract_data = None
            st.rerun()


if __name__ == "__main__":
    app = ContractAnalyzerApp()
    app.run()
