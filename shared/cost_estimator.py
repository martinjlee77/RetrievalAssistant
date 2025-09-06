"""
Cost Estimation System for VeritasLogic Analysis Platform
Calculates analysis costs based on document complexity and ASC standard
"""

import logging
from typing import Dict, Any, Tuple
from decimal import Decimal
import re

logger = logging.getLogger(__name__)

class CostEstimator:
    """Calculates cost estimates for ASC analyses"""
    
    # Base pricing per analysis type (in USD)
    BASE_COSTS = {
        'ASC 606': Decimal('15.00'),  # Revenue Recognition - complex
        'ASC 340-40': Decimal('12.00'),  # Contract Costs - moderate
        'ASC 842': Decimal('18.00'),  # Leases - very complex
        'ASC 718': Decimal('20.00'),  # Stock Compensation - very complex  
        'ASC 805': Decimal('25.00'),  # Business Combinations - most complex
    }
    
    # Complexity multipliers based on document characteristics
    COMPLEXITY_MULTIPLIERS = {
        'simple': Decimal('0.8'),      # Short, straightforward docs
        'moderate': Decimal('1.0'),    # Standard complexity
        'complex': Decimal('1.3'),     # Long or complex docs
        'very_complex': Decimal('1.6') # Very long or highly complex docs
    }
    
    # Word count thresholds for complexity assessment
    WORD_COUNT_THRESHOLDS = {
        'simple': 500,        # Under 500 words
        'moderate': 2000,     # 500-2000 words  
        'complex': 5000,      # 2000-5000 words
        'very_complex': 5000  # Over 5000 words
    }
    
    def __init__(self):
        pass
    
    def estimate_analysis_cost(
        self, 
        asc_standard: str, 
        document_text: str, 
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """
        Calculate cost estimate for an ASC analysis
        
        Args:
            asc_standard: The ASC standard (e.g., 'ASC 606')
            document_text: The main document content
            additional_context: Additional context provided by user
            
        Returns:
            Dict containing cost estimate, breakdown, and metadata
        """
        try:
            # Get base cost for the standard
            base_cost = self.BASE_COSTS.get(asc_standard, Decimal('15.00'))
            
            # Analyze document complexity
            complexity_info = self._analyze_document_complexity(document_text, additional_context)
            
            # Calculate final cost with complexity multiplier
            complexity_multiplier = self.COMPLEXITY_MULTIPLIERS[complexity_info['level']]
            estimated_cost = base_cost * complexity_multiplier
            
            # Round to nearest cent
            estimated_cost = estimated_cost.quantize(Decimal('0.01'))
            
            # Calculate cap (115% of estimate as mentioned in requirements)
            cost_cap = (estimated_cost * Decimal('1.15')).quantize(Decimal('0.01'))
            
            return {
                'estimated_cost': float(estimated_cost),
                'cost_cap': float(cost_cap),
                'base_cost': float(base_cost),
                'complexity_multiplier': float(complexity_multiplier),
                'complexity_info': complexity_info,
                'asc_standard': asc_standard,
                'billing_model': 'pay_actual_capped_at_estimate'
            }
            
        except Exception as e:
            logger.error(f"Cost estimation error: {e}")
            # Return safe fallback estimate
            fallback_cost = Decimal('20.00')
            return {
                'estimated_cost': float(fallback_cost),
                'cost_cap': float(fallback_cost * Decimal('1.15')),
                'base_cost': float(fallback_cost),
                'complexity_multiplier': 1.0,
                'complexity_info': {
                    'level': 'moderate',
                    'word_count': 0,
                    'reason': 'Error in analysis - using fallback'
                },
                'asc_standard': asc_standard,
                'billing_model': 'pay_actual_capped_at_estimate'
            }
    
    def _analyze_document_complexity(self, document_text: str, additional_context: str = "") -> Dict[str, Any]:
        """
        Analyze document complexity to determine appropriate multiplier
        
        Returns:
            Dict with complexity level, word count, and reasoning
        """
        # Combine all text for analysis
        full_text = f"{document_text} {additional_context}".strip()
        
        # Count words
        word_count = len(full_text.split())
        
        # Initialize complexity assessment
        complexity_factors = []
        complexity_score = 0
        
        # Factor 1: Document length
        if word_count < self.WORD_COUNT_THRESHOLDS['simple']:
            complexity_factors.append("Short document")
            length_score = -1
        elif word_count < self.WORD_COUNT_THRESHOLDS['moderate']:
            complexity_factors.append("Standard length document")
            length_score = 0
        elif word_count < self.WORD_COUNT_THRESHOLDS['complex']:
            complexity_factors.append("Long document")
            length_score = 1
        else:
            complexity_factors.append("Very long document")
            length_score = 2
        
        complexity_score += length_score
        
        # Factor 2: Contract complexity indicators
        complex_terms = [
            r'contingent\s+consideration', r'earnout', r'variable\s+consideration',
            r'performance\s+obligation', r'stand\s+alone\s+selling\s+price',
            r'modification', r'amendment', r'renewal', r'extension',
            r'multiple\s+element', r'bundled', r'combined\s+contract',
            r'lease\s+term', r'renewal\s+option', r'termination\s+option',
            r'purchase\s+option', r'residual\s+value', r'implicit\s+rate',
            r'incremental\s+borrowing', r'variable\s+lease\s+payment',
            r'stock\s+option', r'restricted\s+stock', r'performance\s+share',
            r'vesting', r'graded\s+vesting', r'market\s+condition',
            r'service\s+condition', r'performance\s+condition',
            r'fair\s+value', r'grant\s+date', r'modification',
            r'business\s+combination', r'acquisition', r'merger',
            r'goodwill', r'intangible\s+asset', r'purchase\s+price\s+allocation',
            r'contingent\s+asset', r'contingent\s+liability'
        ]
        
        complex_matches = 0
        for term in complex_terms:
            if re.search(term, full_text, re.IGNORECASE):
                complex_matches += 1
        
        if complex_matches >= 5:
            complexity_factors.append("Multiple complex accounting terms")
            complexity_score += 2
        elif complex_matches >= 2:
            complexity_factors.append("Some complex accounting terms")
            complexity_score += 1
        
        # Factor 3: Financial data complexity
        financial_patterns = [
            r'\$[\d,]+(?:\.\d{2})?', r'[0-9]+%', r'million', r'billion',
            r'schedule', r'exhibit', r'attachment', r'appendix'
        ]
        
        financial_matches = sum(1 for pattern in financial_patterns 
                              if re.search(pattern, full_text, re.IGNORECASE))
        
        if financial_matches >= 10:
            complexity_factors.append("Extensive financial data")
            complexity_score += 1
        elif financial_matches >= 5:
            complexity_factors.append("Moderate financial data")
        
        # Factor 4: Multiple party complexity
        if re.search(r'subsidiary|affiliate|related\s+party|joint\s+venture', full_text, re.IGNORECASE):
            complexity_factors.append("Multiple party transaction")
            complexity_score += 1
        
        # Determine final complexity level
        if complexity_score <= -1:
            level = 'simple'
        elif complexity_score <= 1:
            level = 'moderate'
        elif complexity_score <= 3:
            level = 'complex'
        else:
            level = 'very_complex'
        
        return {
            'level': level,
            'word_count': word_count,
            'complexity_score': complexity_score,
            'factors': complexity_factors,
            'reason': f"Document analysis: {', '.join(complexity_factors[:3])}"
        }
    
    def format_cost_display(self, cost_estimate: Dict[str, Any]) -> str:
        """Format cost estimate for user display"""
        estimated = cost_estimate['estimated_cost']
        cap = cost_estimate['cost_cap']
        complexity = cost_estimate['complexity_info']['level'].title()
        
        return f"""
        **💰 Cost Estimate: ${estimated:.2f}**
        
        - **Base Cost ({cost_estimate['asc_standard']}):** ${cost_estimate['base_cost']:.2f}
        - **Complexity Level:** {complexity} (×{cost_estimate['complexity_multiplier']:.1f})
        - **Maximum Charge:** ${cap:.2f} (115% cap)
        - **Document:** {cost_estimate['complexity_info']['word_count']:,} words
        
        *You pay actual usage, capped at ${cap:.2f}*
        """

# Global instance for use across the application
cost_estimator = CostEstimator()