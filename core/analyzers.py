"""
Analyzer Factory for Multi-Standard Platform
Provides centralized access to RAG-enabled analyzers for different accounting standards
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

class BaseAnalyzer(ABC):
    """Abstract base class for all accounting standard analyzers with RAG capabilities"""
    
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
    def analyze_contract(self, contract_text: str, contract_data: Any, debug_config: Optional[Dict] = None) -> Any:
        """Analyze contract using RAG-enhanced analysis framework"""
        pass
    
    @abstractmethod
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics for debugging purposes"""
        pass

def get_analyzer(standard: str):
    """Factory function to get the appropriate RAG-enabled analyzer for a standard"""
    
    if standard == "ASC 606":
        from utils.asc606_analyzer import ASC606Analyzer
        return ASC606Analyzer()
    
    elif standard == "ASC340":
        from utils.asc340_analyzer import ASC340Analyzer
        return ASC340Analyzer()
        
    elif standard == "ASC 340-40":
        from utils.asc340_analyzer import ASC340Analyzer
        return ASC340Analyzer()
    
    elif standard == "ASC 842":
        # Placeholder - will be implemented when ASC 842 documents are available
        raise NotImplementedError(f"ASC 842 analyzer not yet implemented - awaiting authoritative source documents")
    
    elif standard == "ASC 815":
        # Placeholder - will be implemented when ASC 815 documents are available  
        raise NotImplementedError(f"ASC 815 analyzer not yet implemented - awaiting authoritative source documents")
    
    elif standard == "ASC 326":
        # Placeholder - will be implemented when ASC 326 documents are available
        raise NotImplementedError(f"ASC 326 analyzer not yet implemented - awaiting authoritative source documents")
    
    else:
        raise ValueError(f"No analyzer available for standard: {standard}")

# Standard configuration registry
STANDARDS_CONFIG = {
    'ASC 606': {
        'name': 'Revenue from Contracts with Customers',
        'description': 'Analyze revenue recognition under the 5-step model',
        'status': 'available',
        'analyzer_class': 'ASC606Analyzer',
        'knowledge_base_collection': 'asc606_paragraphs',
        'prompt_framework': 'asc606_framework',
        'rag_enabled': True,
        'capabilities': ['contract_term_extraction', 'authoritative_citations', 'professional_memos']
    },
    'ASC 842': {
        'name': 'Leases',
        'description': 'Analyze lease classification and measurement',
        'status': 'coming_soon',
        'analyzer_class': 'ASC842Analyzer',
        'knowledge_base_collection': 'kb_asc_842',
        'prompt_framework': 'asc842_framework',
        'rag_enabled': False,
        'capabilities': ['awaiting_authoritative_sources']
    },
    'ASC 815': {
        'name': 'Derivatives and Hedging',
        'description': 'Analyze derivative instruments and hedging activities',
        'status': 'coming_soon',
        'analyzer_class': 'ASC815Analyzer',
        'knowledge_base_collection': 'kb_asc_815',
        'prompt_framework': 'asc815_framework',
        'rag_enabled': False,
        'capabilities': ['awaiting_authoritative_sources']
    },
    'ASC 326': {
        'name': 'Credit Losses',
        'description': 'Analyze current expected credit losses',
        'status': 'coming_soon',
        'analyzer_class': 'ASC326Analyzer',
        'knowledge_base_collection': 'kb_asc_326',
        'prompt_framework': 'asc326_framework',
        'rag_enabled': False,
        'capabilities': ['awaiting_authoritative_sources']
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