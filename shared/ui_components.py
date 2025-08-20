"""
Shared UI Components Module

This module provides reusable Streamlit components for all accounting standards.
Keeps UI consistent and reduces code duplication.

Author: Accounting Platform Team
"""

import streamlit as st
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class SharedUIComponents:
    """Reusable UI components for all accounting standard pages."""
    
    @staticmethod
    def page_header(title: str, subtitle: str, icon: str = "📊") -> None:
        """Display a consistent page header across all standards."""
        st.title(f"{icon} {title}")
        st.markdown(f"*{subtitle}*")
        st.markdown("---")
    
    @staticmethod
    def input_section(standard_name: str) -> Tuple[Optional[str], Optional[str], str, str]:
        """
        Display the input section for contract analysis.
        
        Args:
            standard_name: Name of the accounting standard (e.g., "ASC 606")
            
        Returns:
            Tuple of (contract_text, filename, customer_name, analysis_title)
        """
        st.subheader("📄 Contract Information")
        
        # Document upload (handled by shared document processor)
        from shared.document_processor import SharedDocumentProcessor
        processor = SharedDocumentProcessor()
        
        contract_text, filename = processor.upload_and_process(
            f"Upload Contract Document for {standard_name} Analysis"
        )
        
        # Basic contract information
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input(
                "Customer/Entity Name",
                placeholder="Enter customer or entity name",
                help="Name of the customer or entity for the contract"
            )
        
        with col2:
            analysis_title = st.text_input(
                "Analysis Title",
                value=f"{standard_name} Revenue Recognition Analysis" if "606" in standard_name else f"{standard_name} Analysis",
                help="Title for this analysis (will appear in the memo)"
            )
        
        # Display document info if processed
        if contract_text and filename:
            processor.display_document_info(contract_text, filename)
        
        return contract_text, filename, customer_name, analysis_title
    
    @staticmethod
    def analysis_progress(steps: List[str], current_step: int = 0) -> None:
        """
        Display analysis progress indicator.
        
        Args:
            steps: List of step names
            current_step: Current step index (0-based)
        """
        st.subheader("🔄 Analysis Progress")
        
        # Create progress columns
        cols = st.columns(len(steps))
        
        for i, (col, step) in enumerate(zip(cols, steps)):
            with col:
                if i < current_step:
                    st.success(f"✅ {step}")
                elif i == current_step:
                    st.info(f"🔄 {step}")
                else:
                    st.write(f"⏳ {step}")
    
    @staticmethod
    def analysis_button(label: str = "🚀 Analyze Contract", key: str = None) -> bool:
        """
        Display a consistent analysis button.
        
        Args:
            label: Button label
            key: Unique key for the button
            
        Returns:
            True if button was clicked
        """
        return st.button(
            label,
            type="primary",
            use_container_width=True,
            key=key,
            help="Start the contract analysis process"
        )
    
    @staticmethod
    def validation_errors(errors: List[str]) -> None:
        """
        Display validation errors in a consistent format.
        
        Args:
            errors: List of error messages
        """
        if not errors:
            return
            
        st.error("⚠️ Please correct the following issues before proceeding:")
        for error in errors:
            st.write(f"• {error}")
    
    @staticmethod
    def analysis_results_section(title: str, content: str, expanded: bool = True) -> None:
        """
        Display analysis results in a consistent expandable section.
        
        Args:
            title: Section title
            content: Section content
            expanded: Whether section should be expanded by default
        """
        with st.expander(f"📋 {title}", expanded=expanded):
            st.markdown(content)
    
    @staticmethod
    def loading_spinner(message: str = "Processing..."):
        """Context manager for loading spinner."""
        return st.spinner(message)
    
    @staticmethod
    def success_message(message: str, icon: str = "✅") -> None:
        """Display a success message."""
        st.success(f"{icon} {message}")
    
    @staticmethod
    def info_message(message: str, icon: str = "ℹ️") -> None:
        """Display an info message."""
        st.info(f"{icon} {message}")
    
    @staticmethod
    def warning_message(message: str, icon: str = "⚠️") -> None:
        """Display a warning message."""
        st.warning(f"{icon} {message}")
    
    @staticmethod
    def error_message(message: str, icon: str = "❌") -> None:
        """Display an error message."""
        st.error(f"{icon} {message}")
    
    @staticmethod
    def sidebar_info(standard_name: str, features: List[str]) -> None:
        """
        Display standard information in the sidebar.
        
        Args:
            standard_name: Name of the accounting standard
            features: List of key features
        """
        with st.sidebar:
            st.subheader(f"About {standard_name}")
            st.write("**Key Features:**")
            for feature in features:
                st.write(f"• {feature}")
            
            st.markdown("---")
            st.write("**How it works:**")
            st.write("1. Upload your contract document")
            st.write("2. Provide basic information")
            st.write("3. Click analyze to start")
            st.write("4. Review the generated memo")
    
    @staticmethod
    def validate_inputs(contract_text: Optional[str], 
                       customer_name: str, 
                       analysis_title: str) -> List[str]:
        """
        Validate user inputs and return list of errors.
        
        Args:
            contract_text: Extracted contract text
            customer_name: Customer name
            analysis_title: Analysis title
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not contract_text:
            errors.append("Please upload a contract document")
        
        if not customer_name.strip():
            errors.append("Please enter a customer/entity name")
        
        if not analysis_title.strip():
            errors.append("Please enter an analysis title")
        
        # Validate contract content if provided
        if contract_text:
            from shared.document_processor import SharedDocumentProcessor
            processor = SharedDocumentProcessor()
            if not processor.validate_document_content(contract_text):
                errors.append("Document appears to be incomplete or not a valid contract")
        
        return errors
    
    @staticmethod
    def display_knowledge_base_stats(kb_stats: Dict[str, Any]) -> None:
        """
        Display knowledge base statistics.
        
        Args:
            kb_stats: Knowledge base statistics dictionary
        """
        if kb_stats.get("error"):
            st.error(f"Knowledge base error: {kb_stats['error']}")
            return
        
        with st.expander("📚 Knowledge Base Information", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Documents", kb_stats.get("document_count", "Unknown"))
                
            with col2:
                st.metric("Status", kb_stats.get("status", "Unknown").title())
            
            st.write(f"**Database:** {kb_stats.get('collection_name', 'Unknown')}")


class StandardPageLayout:
    """Template layout class for accounting standard pages."""
    
    def __init__(self, standard_name: str, subtitle: str, features: List[str]):
        self.standard_name = standard_name
        self.subtitle = subtitle
        self.features = features
        self.ui = SharedUIComponents()
    
    def render_page_start(self) -> None:
        """Render the start of the page (header and sidebar)."""
        # Page header
        self.ui.page_header(
            title=f"{self.standard_name} Analysis",
            subtitle=self.subtitle,
            icon="📊"
        )
        
        # Sidebar info
        self.ui.sidebar_info(self.standard_name, self.features)
    
    def get_inputs(self) -> Tuple[Optional[str], Optional[str], str, str, List[str]]:
        """
        Get and validate user inputs.
        
        Returns:
            Tuple of (contract_text, filename, customer_name, analysis_title, validation_errors)
        """
        # Get inputs
        contract_text, filename, customer_name, analysis_title = self.ui.input_section(self.standard_name)
        
        # Validate inputs
        validation_errors = self.ui.validate_inputs(contract_text, customer_name, analysis_title)
        
        # Display validation errors if any
        if validation_errors:
            self.ui.validation_errors(validation_errors)
        
        return contract_text, filename, customer_name, analysis_title, validation_errors