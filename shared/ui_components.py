"""
Shared UI Components Module

This module provides truly reusable UI components across accounting standards.
Only includes universal elements - each ASC handles its own specific UI needs.

Author: Accounting Platform Team
"""

import streamlit as st
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class SharedUIComponents:
    """Universal UI components that work across all accounting standards."""
    
    @staticmethod
    def analysis_progress(steps: List[str], current_step: int = 0, placeholder=None) -> None:
        """
        Display analysis progress indicator - works for any number of steps.
        
        Args:
            steps: List of step names
            current_step: Current step index (0-based)
            placeholder: Optional st.empty() placeholder to render progress in (for clearable progress)
        """
        def _render_progress():
            # Create progress columns (handle different numbers of steps)
            cols = st.columns(min(len(steps), 6))  # Max 6 columns for readability
            
            for i, (col, step) in enumerate(zip(cols, steps)):
                with col:
                    if i < current_step:
                        st.success(f"✅ {step}")
                    elif i == current_step:
                        st.info(f"🔄 {step}")
                    else:
                        st.write(f"⏳ {step}")
        
        if placeholder:
            with placeholder.container():
                _render_progress()
        else:
            _render_progress()
    
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
    def display_knowledge_base_stats(kb_info: Dict[str, str]) -> None:
        """
        Display user-friendly knowledge base information.
        
        Args:
            kb_info: User-friendly knowledge base information dictionary
        """
        if kb_info.get("status") == "Knowledge base information unavailable":
            st.info(f"ℹ️ {kb_info.get('note', 'Analysis proceeding with general knowledge')}")
            return
        
        with st.expander("📚 Knowledge Base Information", expanded=False):
            st.write(f"**Standard:** {kb_info.get('standard', 'ASC 606 Revenue Recognition')}")
            st.write(f"**Knowledge Base:** {kb_info.get('documents', 'guidance documents')}")
            st.write(f"**Status:** {kb_info.get('status', 'Active')}")
            st.write(f"_{kb_info.get('note', 'Analysis based on current authoritative guidance')}_")
    
    @staticmethod
    def display_document_quality_feedback(file_results: List[Dict[str, Any]]) -> None:
        """
        Display document quality feedback with 3-tier quality indicators.
        
        Args:
            file_results: List of document extraction results with quality metrics
        """
        if not file_results:
            return
        
        # Group files by quality state
        quality_groups = {'good': [], 'degraded': [], 'blocked': []}
        
        for result in file_results:
            filename = result.get('filename', 'Unknown file')
            # Derive quality state more robustly
            quality_state = result.get('quality_state')
            if not quality_state:
                # Fallback logic for missing quality_state
                if (result.get('error') == 'scanned_pdf_detected' or 
                    result.get('is_likely_scanned') or 
                    result.get('error')):
                    quality_state = 'blocked'
                else:
                    quality_state = 'good'
            
            word_count = result.get('word_count', 0)
            reasons = result.get('detection_reasons', [])
            
            quality_groups[quality_state].append({
                'filename': filename,
                'word_count': word_count,
                'reasons': reasons,
                'result': result
            })
        
        # Display overall summary
        total_files = len(file_results)
        good_count = len(quality_groups['good'])
        degraded_count = len(quality_groups['degraded'])
        blocked_count = len(quality_groups['blocked'])
        
        if blocked_count > 0:
            st.error(f"❌ Document Processing: {blocked_count} file(s) blocked, {good_count + degraded_count} processed")
        elif degraded_count > 0:
            st.warning(f"⚠️ Document Processing: {total_files} file(s) processed ({degraded_count} with quality issues)")
        else:
            st.success(f"✅ Document Processing: {total_files} file(s) processed successfully")
        
        # Display file details
        for result in file_results:
            filename = result.get('filename', 'Unknown file')
            # Use same robust quality state derivation
            quality_state = result.get('quality_state')
            if not quality_state:
                if (result.get('error') == 'scanned_pdf_detected' or 
                    result.get('is_likely_scanned') or 
                    result.get('error')):
                    quality_state = 'blocked'
                else:
                    quality_state = 'good'
            
            word_count = result.get('word_count', 0)
            reasons = result.get('detection_reasons', [])
            
            # Quality indicator and basic info
            if quality_state == 'good':
                st.write(f"📄 **{filename}** - ✅ Good Quality ({word_count:,} words)")
            elif quality_state == 'degraded':
                st.write(f"📄 **{filename}** - ⚠️ Degraded Quality ({word_count:,} words)")
                
                # Show quality details in expandable section
                with st.expander(f"Quality Details: {filename}", expanded=False):
                    if reasons:
                        st.write("**Issues Detected:**")
                        for reason in reasons:
                            st.write(f"• {reason}")
                    st.info("💡 **Tip:** Analysis will proceed with enhanced text cleaning. For best results, use original text-based PDFs when possible.")
            else:  # blocked
                st.write(f"📄 **{filename}** - ❌ Blocked")
                if reasons:
                    st.write("**Issues:**")
                    for reason in reasons[:2]:  # Show first 2 reasons
                        st.write(f"• {reason}")
                    
        # Show degraded quality tips if any degraded files
        if degraded_count > 0:
            with st.expander("📋 Document Quality Tips", expanded=False):
                st.markdown("""
                **For better analysis quality:**
                - Use original text-based PDFs instead of scanned documents
                - Ensure documents are not password-protected
                - Check that text is selectable in the PDF viewer
                - Consider using OCR software for scanned documents
                """)
    
    @staticmethod 
    def get_quality_icon(quality_state: str) -> str:
        """Get the appropriate icon for quality state."""
        icons = {
            'good': '✅',
            'degraded': '⚠️', 
            'blocked': '❌'
        }
        return icons.get(quality_state, '❓')