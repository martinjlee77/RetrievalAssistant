"""
ASC 805 Knowledge Search

This module provides ASC 805 specific knowledge base search functionality.
Simple wrapper around the shared knowledge base for ASC 805 authoritative guidance.

"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from shared.knowledge_base import ASC805KnowledgeBase

logger = logging.getLogger(__name__)

class ASC805KnowledgeSearch:
    """
    ASC 606 specific knowledge search functionality.
    Provides relevant authoritative guidance for contract analysis.
    """
    
    def __init__(self):
        """Initialize ASC 606 knowledge search."""
        try:
            self.knowledge_base = ASC805KnowledgeBase()
            logger.info("ASC 606 knowledge search initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ASC 606 knowledge search: {str(e)}")
            # Don't continue without knowledge base - this is critical for ASC 606 analysis
            raise RuntimeError(f"ASC 606 knowledge base is required but not available: {str(e)}. Please process the ASC 606 guidance documents first.")
    
    def search_for_step(self, step_number: int, contract_text: str) -> str:
        """
        Search for relevant ASC 606 guidance for a specific step.
        
        Args:
            step_number: ASC 606 step number (1-5)
            contract_text: Contract text to help focus the search
            
        Returns:
            Formatted authoritative guidance context
        """
        if not self.knowledge_base:
            raise RuntimeError("ASC 606 knowledge base not available. Cannot perform authoritative analysis.")
        
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
        Perform a general search of ASC 606 guidance.
        
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
        Build a targeted search query for a specific ASC 606 step.
        
        Args:
            step_number: Step number (1-5)
            contract_text: Contract text to extract relevant terms
            
        Returns:
            Optimized search query string
        """
        # Base step queries
        step_queries = {
            1: "contract existence criteria ASC 606-10-25-1 approval commitment rights payment commercial substance collectibility",
            2: "performance obligations distinct goods services ASC 606-10-25-19 ASC 606-10-25-21 separately identifiable",
            3: "transaction price consideration ASC 606-10-32-2 variable consideration financing component",
            4: "allocation standalone selling price ASC 606-10-32-28 ASC 606-10-32-33 discount allocation",
            5: "revenue recognition timing over time point in time ASC 606-10-25-27 ASC 606-10-25-30 control transfer"
        }
        
        base_query = step_queries.get(step_number, "ASC 606 revenue recognition")
        
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
            step_number: ASC 606 step number
            
        Returns:
            List of relevant search terms
        """
        if not contract_text:
            return []
        
        contract_lower = contract_text.lower()
        relevant_terms = []
        
        # Step-specific term extraction
        if step_number == 1:
            # Contract formation terms
            terms = [
                # Approval and commitment (25-1a)
                'approve', 'approval', 'commit', 'commitment', 'agreement', 'contract', 'accept', 'acceptance',
                'signature', 'signed', 'execute', 'execution', 'effective', 'binding', 'enforceable',

                # Rights and obligations (25-1b)
                'rights', 'obligations', 'responsibilities', 'duties', 'promise', 'promises', 'obligate',

                # Payment terms (25-1c)
                'payment', 'pay', 'fee', 'fees', 'consideration', 'price', 'payment terms', 'payment schedule',
                'invoice', 'billing', 'remittance',

                # Commercial substance (25-1d)
                'commercial', 'substance', 'economic', 'business purpose', 'arm\'s length',

                # Collectibility (25-1e)
                'collect', 'collectibility', 'ability to pay', 'credit', 'payment ability', 'financial ability',
                'creditworthiness', 'solvency' 
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 2:
            # Performance obligation terms
            terms = [
                # Promised goods and services
                'software', 'hardware', 'services', 'service', 'license', 'licensing', 'implementation',
                'support', 'maintenance', 'training', 'consulting', 'development', 'customization',
                'installation', 'configuration', 'updates', 'upgrades', 'warranty',

                # Distinctness criteria (25-19, 25-21)
                'distinct', 'separate', 'separately', 'independent', 'standalone', 'bundled', 'package',
                'capable', 'benefit', 'identifiable', 'interdependent', 'interrelated', 'dependent',

                # Customer options/material rights (25-20)
                'option', 'options', 'renewal', 'extension', 'upgrade', 'discount', 'future services',
                'material right', 'additional goods', 'additional services'              
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 3:
            # Transaction price terms
            terms = [
                # Fixed consideration
                'fee', 'fees', 'price', 'fixed price', 'fixed fee', 'base price', 'base fee',

                # Variable consideration (32-5 to 32-14)
                'variable', 'bonus', 'penalty', 'discount', 'rebate', 'credit', 'incentive',
                'contingent', 'performance-based', 'usage-based', 'milestone', 'threshold',

                # Financing components (32-15 to 32-20)
                'financing', 'interest', 'payment terms', 'payment schedule', 'installment',
                'deferred payment', 'time value', 'present value',

                # Noncash consideration (32-21 to 32-25)
                'noncash', 'non-cash', 'goods', 'services', 'equity', 'stock', 'shares', 'barter',

                # Consideration to customer (32-26 to 32-27)
                'refund', 'credit', 'reimbursement', 'cash back', 'customer credit'     
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 4:
            # Allocation terms
            terms = [
                # Allocation concepts
                'allocation', 'allocate', 'distribution', 'proportion', 'proportional', 'split',

                # Standalone selling price (32-31 to 32-34)
                'standalone', 'selling price', 'market price', 'list price', 'historical price',
                'observed price', 'estimated price', 'cost-plus', 'margin',

                # Allocation methodology
                'relative', 'proportionate', 'percentage', 'ratio', 'weighted',

                # Discount allocation (32-36)
                'discount', 'discount allocation', 'bundle discount', 'package discount',

                # Performance obligations
                'obligation', 'obligations', 'deliverable', 'deliverables', 'component', 'elements'

                
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
            
        elif step_number == 5:
            # Recognition terms
            terms = [

                # Timing concepts
                'delivery', 'completion', 'shipment', 'shipping', 'installation', 'acceptance',
                'go-live', 'live', 'deployment', 'implementation',

                # Over time vs. point in time (25-27)
                'over time', 'point in time', 'time-based', 'event-based', 'milestone', 'phases',
                'progress', 'percentage of completion',

                # Control transfer (25-30)
                'control', 'transfer', 'customer control', 'risk of loss', 'benefits', 'direct',
                'obligation', 'performance obligation',

                # Progress measurement (25-31 to 25-33)
                'progress', 'completion', 'input method', 'output method', 'cost-to-cost',
                'efforts-expended', 'units-of-delivery', 'units-of-production'

                
            ]
            relevant_terms.extend([term for term in terms if term in contract_lower])
        
        # Limit to most relevant terms to avoid overly long queries
        return relevant_terms[:3]
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get technical statistics about the ASC 606 knowledge base for internal monitoring.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        if not self.knowledge_base:
            return {
                "status": "unavailable",
                "error": "Knowledge base not initialized",
                "recommendation": "Process ASC 606 guidance documents first"
            }
        
        try:
            stats = self.knowledge_base.get_stats()
            # Add metadata for internal monitoring
            stats["type"] = "ASC 606 Revenue Recognition Knowledge Base"
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
                "note": "Analysis proceeding with general ASC 606 knowledge"
            }
        
        doc_count = stats.get("document_count", 0)
        return {
            "standard": "ASC 606 Revenue Recognition",
            "documents": f"{doc_count:,} guidance documents" if doc_count else "guidance documents",
            "status": "Active",
            "note": "Analysis based on current FASB's ASC 606 authoritative guidance"
        }
    
    def is_available(self) -> bool:
        """Check if knowledge base is available."""
        return self.knowledge_base is not None
    
    def _get_fallback_guidance(self, step_number: int) -> str:
        """Provide fallback ASC 606 guidance when knowledge base is unavailable."""
        step_guidance = {
            1: """Step 1: Identify the Contract with a Customer
Key considerations:
- Legal enforceability under relevant law  
- Commercial substance (parties are committed to perform)
- Approved contract and commitment of parties to perform obligations
- Payment terms are identified
- Collection is probable (customer has ability and intention to pay)

Assess whether the arrangement meets the definition of a contract under ASC 606-10-25-1.""",
            
            2: """Step 2: Identify the Performance Obligations in the Contract  
Key considerations:
- Promise to transfer goods or services that are distinct
- Distinct = capable of being distinct AND distinct within context of contract
- Capable of being distinct: customer can benefit from good/service on its own
- Distinct within context: promise is separately identifiable from other promises

Apply ASC 606-10-25-14 through 25-22 to identify distinct performance obligations.""",
            
            3: """Step 3: Determine the Transaction Price
Key considerations:  
- Amount of consideration expected to be entitled to in exchange for goods/services
- Variable consideration and constraint (ASC 606-10-32-11)
- Significant financing component (ASC 606-10-32-15)
- Noncash consideration (ASC 606-10-32-21)
- Consideration payable to customer (ASC 606-10-32-25)

Calculate total transaction price per ASC 606-10-32-2 through 32-27.""",
            
            4: """Step 4: Allocate the Transaction Price to Performance Obligations
Key considerations:
- Relative standalone selling price approach (ASC 606-10-32-31)
- Standalone selling price estimation methods when not observable
- Allocation of discounts and variable consideration
- Contract modifications affecting allocation

Allocate transaction price per ASC 606-10-32-28 through 32-41.""",
            
            5: """Step 5: Recognize Revenue When Performance Obligations are Satisfied
Key considerations:
- Control transfer to customer (ASC 606-10-25-23)
- Over time vs. point in time recognition (ASC 606-10-25-27)
- Over time criteria: customer benefits, customer controls, no alternative use + enforceable payment right
- Measure progress for over time recognition (output vs. input methods)
 
Recognize revenue per ASC 606-10-25-23 through 25-37."""
        }
        
        return step_guidance.get(step_number, "Step guidance not available.")