"""
Analyzer Factory for Multi-Standard Platform
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

class BaseAnalyzer(ABC):
    """Abstract base class for all accounting standard analyzers"""
    
    def __init__(self, standard_code: str):
        self.standard_code = standard_code
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for analysis tracking"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @abstractmethod
    def analyze_document(self, document_text: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document according to the specific accounting standard"""
        pass
    
    @abstractmethod
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        pass
    
    @abstractmethod
    def validate_analysis_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analysis quality"""
        pass

def get_analyzer(standard: str) -> BaseAnalyzer:
    """Factory function to get the appropriate analyzer for a standard"""
    
    if standard == "ASC 606":
        from hybrid_asc606_analyzer import HybridASC606Analyzer
        return HybridASC606Analyzer()
    
    elif standard == "ASC 842":
        from core.analyzers.asc842_analyzer import ASC842Analyzer
        return ASC842Analyzer()
    
    elif standard == "ASC 815":
        from core.analyzers.asc815_analyzer import ASC815Analyzer
        return ASC815Analyzer()
    
    elif standard == "ASC 326":
        from core.analyzers.asc326_analyzer import ASC326Analyzer
        return ASC326Analyzer()
    
    else:
        raise ValueError(f"No analyzer available for standard: {standard}")

# Standard configuration registry
STANDARDS_CONFIG = {
    'ASC 606': {
        'name': 'Revenue from Contracts with Customers',
        'description': 'Analyze revenue recognition under the 5-step model',
        'status': 'available',
        'analyzer_class': 'HybridASC606Analyzer',
        'knowledge_base_collection': 'asc606',
        'prompt_framework': 'asc606_framework'
    },
    'ASC 842': {
        'name': 'Leases',
        'description': 'Analyze lease classification and measurement',
        'status': 'coming_soon',
        'analyzer_class': 'ASC842Analyzer',
        'knowledge_base_collection': 'asc842',
        'prompt_framework': 'asc842_framework'
    },
    'ASC 815': {
        'name': 'Derivatives and Hedging',
        'description': 'Analyze derivative instruments and hedging activities',
        'status': 'coming_soon',
        'analyzer_class': 'ASC815Analyzer',
        'knowledge_base_collection': 'asc815',
        'prompt_framework': 'asc815_framework'
    },
    'ASC 326': {
        'name': 'Credit Losses',
        'description': 'Analyze current expected credit losses',
        'status': 'coming_soon',
        'analyzer_class': 'ASC326Analyzer',
        'knowledge_base_collection': 'asc326',
        'prompt_framework': 'asc326_framework'
    }
}

def get_standard_config(standard: str) -> Dict[str, str]:
    """Get configuration for a specific standard"""
    return STANDARDS_CONFIG.get(standard, {})

def get_available_standards() -> List[str]:
    """Get list of available standards"""
    return [code for code, config in STANDARDS_CONFIG.items() if config['status'] == 'available']

def get_all_standards() -> Dict[str, Dict[str, str]]:
    """Get all standards configuration"""
    return STANDARDS_CONFIG