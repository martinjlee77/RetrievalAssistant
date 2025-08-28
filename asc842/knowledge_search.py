"""
ASC 842 Knowledge Search

This module provides ASC 842 specific knowledge base search functionality.
Simple wrapper around the shared knowledge base for ASC 842 authoritative guidance.

"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from shared.knowledge_base import ASC842KnowledgeBase

logger = logging.getLogger(__name__)

class ASC842KnowledgeSearch:
    """
    ASC 842 specific knowledge search functionality.
    Provides relevant authoritative guidance for lease contract analysis.
    """
    
    def __init__(self):
        """Initialize ASC 842 knowledge search."""
        try:
            self.knowledge_base = ASC842KnowledgeBase()
            logger.info("ASC 842 knowledge search initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ASC 842 knowledge search: {str(e)}")
            # Don't continue without knowledge base - this is critical for ASC 842 analysis
            raise RuntimeError(f"ASC 842 knowledge base is required but not available: {str(e)}. Please process the ASC 842 guidance documents first.")
    
    def search_for_step(self, step_number: int, contract_text: str) -> str:
        """
        Search for relevant ASC 842 guidance for a specific step.
        
        Args:
            step_number: ASC 842 step number (1-5)
            contract_text: Contract text to help focus the search
            
        Returns:
            Formatted authoritative guidance context
        """
        if not self.knowledge_base:
            raise RuntimeError("ASC 842 knowledge base not available. Cannot perform authoritative analysis.")
        
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
        Perform a general search of ASC 842 guidance.
        
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
        Build a targeted search query for a specific ASC 842 step.
        
        Args:
            step_number: Step number (1-5)
            contract_text: Contract text to extract relevant terms
            
        Returns:
            Optimized search query string
        """
        # Base step queries based on ASC 842 methodology
        step_queries = {
            1: "lease definition identified asset control substitution rights enforceable period lease term ASC 842-10-15-3 ASC 842-10-15-9",
            2: "lease components nonlease components allocation practical expedient standalone prices lease payments ASC 842-10-15-28 ASC 842-20-30-5",
            3: "lease classification finance operating ownership transfer purchase option economic life present value fair value ASC 842-10-25-2",
            4: "initial recognition lease liability ROU asset present value journal entries commencement date ASC 842-20-25-1 ASC 842-20-30-1",
            5: "subsequent measurement amortization interest expense remeasurement modifications subleases ASC 842-20-25 ASC 842-10-35-1"
        }
        
        base_query = step_queries.get(step_number, "ASC 842 lease accounting")
        
        # Extract relevant terms from contract to enhance search
        contract_terms = self._extract_relevant_terms(contract_text, step_number)
        
        if contract_terms:
            enhanced_query = f"{base_query} {' '.join(contract_terms)}"
        else:
            enhanced_query = base_query
        
        return enhanced_query
    
    def _extract_relevant_terms(self, contract_text: str, step_number: int) -> List[str]:
        """
        Extract relevant terms from contract text to enhance search.
        
        Args:
            contract_text: Contract text
            step_number: ASC 842 step number
            
        Returns:
            List of relevant search terms
        """
        if not contract_text:
            return []
        
        contract_lower = contract_text.lower()
        relevant_terms = []
        
        # Step-specific term extraction
        if step_number == 1:
            # Scope and lease identification terms
            terms = [
                'lease', 'rental', 'rent', 'tenant', 'landlord', 'lessor', 'lessee',
                'premises', 'property', 'building', 'office', 'warehouse', 'equipment',
                'vehicle', 'asset', 'identified asset', 'control', 'use', 'direct',
                'substitution', 'alternative', 'termination', 'cancel', 'renewal',
                'extension', 'option', 'period', 'term', 'month', 'year'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 2:
            # Components and payments terms
            terms = [
                'rent', 'payment', 'fee', 'base rent', 'additional rent', 'cam',
                'common area maintenance', 'utilities', 'insurance', 'taxes',
                'services', 'maintenance', 'repairs', 'management', 'administrative',
                'fixed', 'variable', 'escalation', 'increase', 'index', 'cpi',
                'percentage rent', 'tenant improvement', 'allowance', 'incentive'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 3:
            # Classification and measurement terms
            terms = [
                'ownership', 'title', 'transfer', 'purchase', 'option', 'buy',
                'fair value', 'economic life', 'useful life', 'specialized',
                'alternative use', 'discount rate', 'interest rate', 'implicit rate',
                'incremental borrowing', 'present value', 'liability', 'asset'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 4:
            # Initial accounting outputs terms
            terms = [
                'commencement', 'available', 'possession', 'occupancy',
                'initial direct costs', 'prepaid', 'incentive', 'journal entry',
                'accounting', 'recognition', 'measurement', 'liability', 'asset'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 5:
            # Subsequent accounting terms
            terms = [
                'amortization', 'depreciation', 'interest', 'expense', 'modification',
                'amendment', 'remeasurement', 'sublease', 'assignment', 'variable',
                'contingent', 'reassessment', 'impairment'
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
        
        # Limit to most relevant terms to avoid overly long queries
        return relevant_terms[:3]
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get technical statistics about the ASC 842 knowledge base for internal monitoring.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        if not self.knowledge_base:
            return {
                "status": "unavailable",
                "error": "Knowledge base not initialized",
                "recommendation": "Process ASC 842 guidance documents first"
            }
        
        try:
            stats = self.knowledge_base.get_stats()
            # Add metadata for internal monitoring
            stats["type"] = "ASC 842 Lease Accounting Knowledge Base"
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
                "note": "Analysis proceeding with general ASC 842 knowledge"
            }
        
        doc_count = stats.get("document_count", 0)
        return {
            "standard": "ASC 842 Lease Accounting",
            "documents": f"{doc_count:,} guidance documents" if doc_count else "guidance documents",
            "status": "Active",
            "note": "Analysis based on current FASB's ASC 842 authoritative guidance"
        }
    
    def is_available(self) -> bool:
        """Check if knowledge base is available."""
        return self.knowledge_base is not None
    
    def _get_fallback_guidance(self, step_number: int) -> str:
        """Provide fallback ASC 842 guidance when knowledge base is unavailable."""
        step_guidance = {
            1: """Step 1: Scope, Identify a Lease, and Determine Enforceable Period and Lease Term
Key considerations:
- Contract contains a lease if it conveys right to control use of identified asset
- Asset must be identified (not substantive substitution rights)
- Customer must have right to obtain substantially all economic benefits
- Customer must have right to direct use of the asset
- Enforceable period assessment (both parties termination without penalty)
- Lease term includes noncancellable periods plus extension/termination options

Apply ASC 842-10-15-3 and 842-10-15-9 through 15-16 for lease identification.""",
            
            2: """Step 2: Identify Components and Determine Lease Payments
Key considerations:
- Separate lease components (right to use underlying assets) from nonlease components
- Practical expedient election to not separate by asset class
- Include fixed payments, variable payments based on index/rate, residual value guarantees
- Exclude variable payments based on performance or usage
- Consider lease incentives, initial direct costs, prepaid amounts

Apply ASC 842-10-15-28 through 15-38 and ASC 842-20-30-5.""",
            
            3: """Step 3: Classify the Lease and Measure at Commencement
Key considerations:
- Finance lease if any criteria met: ownership transfer, purchase option, major part of economic life, substantially all fair value, no alternative use
- Otherwise operating lease
- Measure lease liability at present value of lease payments
- Measure ROU asset as lease liability plus prepaid payments plus initial direct costs minus incentives
- Use discount rate: implicit rate if determinable, otherwise incremental borrowing rate

Apply ASC 842-10-25-2 and ASC 842-20-25-1, 842-20-30-1.""",
            
            4: """Step 4: Produce Initial Accounting Outputs
Key considerations:
- Document classification conclusion with rationale
- Show lease payments calculation and present value
- Prepare commencement date journal entries
- Identify policy elections and significant judgments
- Consider presentation and disclosure requirements

Apply ASC 842-20-25-1, 842-20-30-1, 842-20-45-1, and 842-20-50-1.""",
            
            5: """Step 5: Reminders Beyond Initial Recognition
Key considerations:
- Subsequent measurement differs by classification (finance vs operating)
- Remeasurement triggers: lease term changes, purchase option assessments, RVG changes
- Modification accounting assessment
- Sublease considerations if applicable
- Ongoing disclosure requirements

Apply ASC 842-20-25, ASC 842-10-35-1 through 35-3, and ASC 842-10-25-8 through 25-10."""
        }
        
        return step_guidance.get(step_number, "Step guidance not available.")