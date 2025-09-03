"""
ASC 718 Knowledge Search

This module provides ASC 718 specific knowledge base search functionality.
Simple wrapper around the shared knowledge base for ASC 718 authoritative guidance.

"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from shared.knowledge_base import ASC718KnowledgeBase

logger = logging.getLogger(__name__)

class ASC718KnowledgeSearch:
    """
    ASC 718 specific knowledge search functionality.
    Provides relevant authoritative guidance for stock compensation analysis.
    """
    
    def __init__(self):
        """Initialize ASC 718 knowledge search."""
        try:
            self.knowledge_base = ASC718KnowledgeBase()
            logger.info("ASC 718 knowledge search initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ASC 718 knowledge search: {str(e)}")
            # Don't continue without knowledge base - this is critical for ASC 718 analysis
            raise RuntimeError(f"ASC 718 knowledge base is required but not available: {str(e)}. Please process the ASC 718 guidance documents first.")
    
    def search_for_step(self, step_number: int, contract_text: str) -> str:
        """
        Search for relevant ASC 718 guidance for a specific step.
        
        Args:
            step_number: ASC 718 step number (1-5)
            contract_text: Award document text to help focus the search
            
        Returns:
            Formatted authoritative guidance context
        """
        if not self.knowledge_base:
            raise RuntimeError("ASC 718 knowledge base not available. Cannot perform authoritative analysis.")
        
        try:
            # Create step-specific search query
            search_query = self._build_step_query(step_number, contract_text)
            
            # Search the knowledge base for comprehensive guidance
            guidance = self.knowledge_base.search(search_query, max_results=8)
            
            logger.info(f"Retrieved guidance for Step {step_number}")
            return guidance
            
        except Exception as e:
            logger.error(f"Error searching guidance for Step {step_number}: {str(e)}")
            return f"Error retrieving guidance: {str(e)}"
    
    def search_general(self, query: str) -> str:
        """
        Perform a general search of ASC 718 guidance.
        
        Args:
            query: Search query string
            
        Returns:
            Formatted search results
        """
        if not self.knowledge_base:
            return "Knowledge base not available."
        
        try:
            return self.knowledge_base.search(query, max_results=6)
        except Exception as e:
            logger.error(f"Error in general search: {str(e)}")
            return f"Search error: {str(e)}"
    
    def _build_step_query(self, step_number: int, contract_text: str) -> str:
        """
        Build a targeted search query for a specific ASC 718 step.
        
        Args:
            step_number: Step number (1-5)
            contract_text: Award document text to extract relevant terms
            
        Returns:
            Optimized search query string
        """
        # Base step queries
        step_queries = {
            1: "share-based payment scope ASC 718-10 grant date equity liability classification stock options RSU PSU employee nonemployee",
            2: "fair value measurement grant date valuation Black-Scholes lattice model ASC 718-20 ASC 718-30 option pricing volatility",
            3: "requisite service period vesting attribution forfeitures performance conditions market conditions ASC 718-10-35",
            4: "modifications repricing subsequent measurement liability remeasurement settlement exercises cancellations ASC 718-20-35",
            5: "tax accounting deferred tax assets excess tax benefits journal entries compensation expense APIC ASC 718-740"
        }
        
        base_query = step_queries.get(step_number, "ASC 718 stock compensation")
        
        # Extract relevant terms from award documents to enhance search
        contract_terms = self._extract_relevant_terms(contract_text, step_number)
        
        if contract_terms:
            enhanced_query = f"{base_query} {' '.join(contract_terms)}"
        else:
            enhanced_query = base_query
        
        return enhanced_query
    
    def _extract_relevant_terms(self, contract_text: str, step_number: int) -> List[str]:
        """
        Extract relevant terms from transaction document text to enhance search.
        
        Args:
            contract_text: Transaction document text
            step_number: ASC 805 step number
            
        Returns:
            List of relevant search terms
        """
        if not contract_text:
            return []
        
        contract_lower = contract_text.lower()
        relevant_terms = []
        
        # Step-specific term extraction
        if step_number == 1:
            # Business combination scope and acquirer identification terms
            terms = [
                # Business combination scope
                'acquisition', 'acquire', 'purchase', 'merger', 'business combination', 'transaction',
                'asset acquisition', 'stock purchase', 'asset purchase', 'common control',

                # Business definition
                'business', 'inputs', 'processes', 'outputs', 'workforce', 'employees', 'operations',
                'revenue', 'customers', 'intellectual property', 'substantive processes',

                # Acquirer identification
                'acquirer', 'acquiree', 'target', 'buyer', 'seller', 'control', 'controlling interest',
                'voting rights', 'board control', 'primary beneficiary', 'VIE',

                # Acquisition date
                'closing', 'closing date', 'effective date', 'acquisition date', 'control transfer',
                'completion', 'consummation', 'regulatory approval'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 2:
            # Consideration and transaction terms
            terms = [
                # Consideration transferred
                'purchase price', 'consideration', 'cash', 'stock', 'shares', 'equity', 'debt',
                'promissory note', 'liabilities', 'assets transferred',

                # Contingent consideration
                'contingent', 'earnout', 'milestone', 'performance-based', 'escrow',
                'holdback', 'adjustment', 'working capital adjustment',

                # Step acquisition
                'previously held', 'existing interest', 'step acquisition', 'incremental',
                'fair value remeasurement',

                # Items not part of exchange
                'preexisting relationship', 'settlement', 'consulting agreement',
                'employment agreement', 'acquisition costs', 'transaction costs'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 3:
            # Asset and liability recognition terms
            terms = [
                # Identifiable assets
                'assets', 'identifiable assets', 'tangible assets', 'intangible assets',
                'property', 'equipment', 'inventory', 'receivables', 'investments',

                # Intangible assets
                'intangible', 'intellectual property', 'patents', 'trademarks', 'customer relationships',
                'trade names', 'technology', 'software', 'developed technology', 'IPR&D',

                # Liabilities
                'liabilities', 'debt', 'obligations', 'accrued', 'payables', 'contingencies',
                'warranties', 'restructuring', 'environmental',

                # Fair value measurement
                'fair value', 'valuation', 'appraisal', 'market approach', 'income approach',
                'cost approach', 'goodwill', 'bargain purchase'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 4:
            # Recording and measurement period terms
            terms = [
                # Journal entries and recording
                'journal entry', 'recording', 'entry', 'debit', 'credit', 'consolidated',
                'consolidation', 'elimination',

                # Measurement period
                'measurement period', 'provisional', 'provisional amounts', 'one year',
                'additional information', 'facts and circumstances', 'retrospective',

                # Subsequent measurement
                'subsequent', 'remeasurement', 'fair value changes', 'contingent consideration',
                'indemnification', 'amortization', 'impairment',

                # Pushdown accounting
                'pushdown', 'pushdown accounting', 'acquiree', 'separate financial statements'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 5:
            # Disclosure and documentation terms
            terms = [
                # Required disclosures
                'disclosure', 'disclosures', 'footnote', 'financial statements', 'pro forma',
                'unaudited', 'supplemental', 'material',

                # Business combination disclosures
                'acquisition date', 'primary reasons', 'qualitative factors', 'goodwill',
                'consideration by class', 'assets acquired', 'liabilities assumed',

                # Pro forma information
                'pro forma', 'revenue', 'net income', 'earnings', 'combined entity',
                'as if', 'comparable periods',

                # Technical memo
                'memo', 'memorandum', 'documentation', 'supporting', 'analysis',
                'conclusion', 'judgment', 'assumptions'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
        
        # Limit to most relevant terms to avoid overly long queries
        return relevant_terms[:3]
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get technical statistics about the ASC 805 knowledge base for internal monitoring.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        if not self.knowledge_base:
            return {
                "status": "unavailable",
                "error": "Knowledge base not initialized",
                "recommendation": "Process ASC 805 guidance documents first"
            }
        
        try:
            stats = self.knowledge_base.get_stats()
            # Add metadata for internal monitoring
            stats["type"] = "ASC 805 Business Combinations Knowledge Base"
            stats["timestamp"] = datetime.now().isoformat()
            return stats
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "recommendation": "Check knowledge base connection and initialization"
            }
    
    def get_user_kb_info(self) -> Dict[str, str]:
        """
        Get user-friendly knowledge base information for display.
        
        Returns:
            Simple dictionary with information suitable for end users
        """
        stats = self.get_knowledge_base_stats()
        
        if stats.get("status") not in ["active", "available"] or stats.get("error"):
            return {
                "status": "Knowledge base information unavailable",
                "note": "Analysis proceeding with general ASC 805 knowledge"
            }
        
        doc_count = stats.get("document_count", 0)
        return {
            "standard": "ASC 805 Business Combinations",
            "documents": f"{doc_count:,} guidance documents" if doc_count else "guidance documents",
            "status": "Active",
            "note": "Analysis based on current FASB's ASC 805 authoritative guidance"
        }
    
    def is_available(self) -> bool:
        """Check if knowledge base is available."""
        return self.knowledge_base is not None
    
    def _get_fallback_guidance(self, step_number: int) -> str:
        """Provide fallback ASC 805 guidance when knowledge base is unavailable."""
        step_guidance = {
            1: """Step 1: Scope, Business Assessment, Acquirer, and Acquisition Date
Key considerations:
- ASC 805 acquisition method vs asset acquisition
- Business definition using inputs, processes, and outputs framework
- Acquirer identification and control determination
- Acquisition date when control transfers
- Step acquisition considerations

Apply ASC 805-10 scope and business definition criteria.""",
            
            2: """Step 2: Consideration and Items Not Part of the Exchange
Key considerations:
- Measure consideration transferred at fair value
- Classify contingent consideration as liability or equity
- Separate items not part of the business combination
- Handle step acquisitions and NCI measurement
- Account for acquisition costs separately

Apply ASC 805-30 consideration measurement principles.""",
            
            3: """Step 3: Recognize and Measure Assets and Liabilities; Compute Goodwill
Key considerations:
- Recognize identifiable assets and liabilities at fair value
- Apply measurement exceptions (revenue contracts, leases, CECL)
- Identify and measure intangible assets separately
- Recognize contingencies meeting asset/liability definition
- Compute goodwill or bargain purchase gain

Apply ASC 805-20 recognition and measurement principles.""",
            
            4: """Step 4: Record Acquisition, Measurement Period, and Subsequent Measurement
Key considerations:
- Record acquisition-date journal entries
- Use provisional amounts during measurement period
- Handle measurement period adjustments retrospectively
- Apply subsequent measurement for contingent consideration
- Consider pushdown accounting elections

Apply ASC 805-10 recording and measurement period guidance.""",
            
            5: """Step 5: Prepare Required Disclosures and Technical Memo
Key considerations:
- Prepare comprehensive ASC 805 disclosures
- Include pro forma information requirements
- Document all judgments and measurements
- Address SEC requirements if applicable
- Complete technical memo with supporting analysis

Apply ASC 805-10-50 and ASC 805-30-50 disclosure requirements."""
        }
        
        return step_guidance.get(step_number, "ASC 805 step guidance not available.")