import os
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ProcessingSettings:
    """Settings for PDF processing"""
    
    # Chunking settings
    default_chunk_size: int = 800
    min_chunk_size: int = 200
    max_chunk_size: int = 2000
    default_overlap: int = 20
    min_overlap: int = 10
    max_overlap: int = 30
    
    # Quality settings
    default_quality_threshold: float = 85.0
    min_quality_threshold: float = 70.0
    max_quality_threshold: float = 95.0
    
    # File settings
    max_file_size_mb: float = 100.0
    min_file_size_mb: float = 0.1
    allowed_file_types: List[str] = None
    
    # Processing settings
    max_processing_time_seconds: int = 600  # 10 minutes
    enable_table_extraction: bool = True
    enable_example_extraction: bool = True
    enable_metadata_enrichment: bool = True
    
    # Chapter 4 specific settings
    target_pages: tuple = (63, 83)
    expected_sections: int = 7
    expected_examples: int = 5
    expected_tables: int = 3
    
    def __post_init__(self):
        if self.allowed_file_types is None:
            self.allowed_file_types = ['application/pdf', 'pdf']

class Settings:
    """Main settings class for ASC 606 processing"""
    
    def __init__(self):
        self.processing = ProcessingSettings()
        self.api_keys = self._load_api_keys()
        self.paths = self._setup_paths()
        self.features = self._setup_features()
        
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables"""
        return {
            'unstructured_api_key': os.getenv('UNSTRUCTURED_API_KEY', ''),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', '')
        }
    
    def _setup_paths(self) -> Dict[str, str]:
        """Setup file paths"""
        return {
            'temp_dir': os.getenv('TEMP_DIR', '/tmp'),
            'output_dir': os.getenv('OUTPUT_DIR', './output'),
            'cache_dir': os.getenv('CACHE_DIR', './cache'),
            'logs_dir': os.getenv('LOGS_DIR', './logs')
        }
    
    def _setup_features(self) -> Dict[str, bool]:
        """Setup feature flags"""
        return {
            'enable_caching': os.getenv('ENABLE_CACHING', 'true').lower() == 'true',
            'enable_logging': os.getenv('ENABLE_LOGGING', 'true').lower() == 'true',
            'enable_debug': os.getenv('ENABLE_DEBUG', 'false').lower() == 'true',
            'enable_metrics': os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            'enable_exports': os.getenv('ENABLE_EXPORTS', 'true').lower() == 'true'
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration"""
        return {
            'chunk_size': self.processing.default_chunk_size,
            'chunk_overlap': self.processing.default_overlap,
            'quality_threshold': self.processing.default_quality_threshold,
            'max_file_size': self.processing.max_file_size_mb,
            'target_pages': self.processing.target_pages,
            'enable_table_extraction': self.processing.enable_table_extraction,
            'enable_example_extraction': self.processing.enable_example_extraction,
            'enable_metadata_enrichment': self.processing.enable_metadata_enrichment
        }
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration"""
        return {
            'quality_threshold': self.processing.default_quality_threshold,
            'expected_sections': self.processing.expected_sections,
            'expected_examples': self.processing.expected_examples,
            'expected_tables': self.processing.expected_tables,
            'target_pages': self.processing.target_pages
        }
    
    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration"""
        return {
            'output_dir': self.paths['output_dir'],
            'enable_exports': self.features['enable_exports'],
            'formats': ['json', 'txt', 'csv']
        }
    
    def validate_settings(self) -> Dict[str, Any]:
        """Validate settings configuration"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate processing settings
        if self.processing.default_chunk_size < self.processing.min_chunk_size:
            validation_results['errors'].append(
                f"Default chunk size ({self.processing.default_chunk_size}) "
                f"below minimum ({self.processing.min_chunk_size})"
            )
            validation_results['valid'] = False
        
        if self.processing.default_chunk_size > self.processing.max_chunk_size:
            validation_results['errors'].append(
                f"Default chunk size ({self.processing.default_chunk_size}) "
                f"above maximum ({self.processing.max_chunk_size})"
            )
            validation_results['valid'] = False
        
        # Validate paths
        for path_name, path_value in self.paths.items():
            if not path_value:
                validation_results['warnings'].append(f"Empty path for {path_name}")
        
        # Validate API keys
        if not self.api_keys.get('unstructured_api_key'):
            validation_results['warnings'].append("No Unstructured API key provided")
        
        return validation_results
    
    def get_chapter_4_config(self) -> Dict[str, Any]:
        """Get Chapter 4 specific configuration"""
        return {
            'title': 'Identify the performance obligations in the contract',
            'pages': self.processing.target_pages,
            'expected_sections': [
                '4.1 Identifying the promised goods and services in the contract',
                '4.1.1 Promised goods or services that are immaterial',
                '4.1.2 Shipping and handling activities',
                '4.2 Determining when promises are performance obligations',
                '4.2.1 Determination of distinct',
                '4.2.2 Series of distinct goods or services',
                '4.2.3 Examples of identifying performance obligations',
                '4.3 Promised goods and services that are not distinct',
                '4.4 Principal versus agent considerations',
                '4.4.1 Identifying the specified good or service',
                '4.4.2 Control of the specified good or service',
                '4.4.3 Recognizing revenue as a principal or agent',
                '4.4.4 Examples',
                '4.5 Consignment arrangements',
                '4.6 Customer options for additional goods or services',
                '4.7 Sale of products with a right of return'
            ],
            'key_concepts': [
                'performance obligations',
                'distinct goods and services',
                'principal versus agent',
                'control',
                'transfer',
                'customer options',
                'consignment',
                'right of return'
            ],
            'processing_hints': {
                'preserve_examples': True,
                'maintain_table_structure': True,
                'track_cross_references': True,
                'identify_key_terms': True
            }
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            'version': '1.0.0',
            'description': 'ASC 606 PDF Processing Proof of Concept',
            'target_document': 'EY ASC 606 Comprehensive Guide - Chapter 4',
            'processing_method': 'Semantic chunking with metadata enrichment',
            'validation_approach': 'Multi-dimensional quality assessment',
            'supported_formats': ['PDF'],
            'output_formats': ['JSON', 'TXT', 'CSV'],
            'libraries': {
                'pdf_processing': ['unstructured', 'pdfplumber', 'pypdf2'],
                'text_processing': ['re', 'nltk'],
                'web_interface': ['streamlit'],
                'data_handling': ['pandas', 'json']
            }
        }
