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
    def analysis_progress(steps: List[str], current_step: int = 0) -> None:
        """
        Display analysis progress indicator - works for any number of steps.
        
        Args:
            steps: List of step names
            current_step: Current step index (0-based)
        """
        st.subheader("🔄 Analysis Progress")
        
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
    def display_knowledge_base_stats(kb_stats: Dict[str, Any]) -> None:
        """
        Display knowledge base statistics - useful for debugging.
        
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