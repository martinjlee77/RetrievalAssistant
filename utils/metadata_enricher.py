import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

class MetadataEnricher:
    """Enriches chunks with comprehensive metadata for ASC 606 content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.asc_606_terms = self._load_asc_606_terms()
        self.section_patterns = self._load_section_patterns()
    
    def enrich_chunks(self, chunks: List[Dict[str, Any]], structure_analysis: Dict[str, Any],
                     tables: List[Dict[str, Any]], examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich chunks with comprehensive metadata"""
        
        enriched_chunks = []
        
        for chunk in chunks:
            try:
                # Start with existing metadata
                enriched_metadata = chunk.get('metadata', {}).copy()
                
                # Add structural metadata
                enriched_metadata.update(self._add_structural_metadata(chunk, structure_analysis))
                
                # Add content analysis metadata
                enriched_metadata.update(self._add_content_analysis_metadata(chunk))
                
                # Add relationship metadata
                enriched_metadata.update(self._add_relationship_metadata(chunk, tables, examples))
                
                # Add ASC 606 specific metadata
                enriched_metadata.update(self._add_asc_606_metadata(chunk))
                
                # Add quality metadata
                enriched_metadata.update(self._add_quality_metadata(chunk))
                
                # Add processing metadata
                enriched_metadata.update(self._add_processing_metadata(chunk))
                
                # Update chunk with enriched metadata
                enriched_chunk = chunk.copy()
                enriched_chunk['metadata'] = enriched_metadata
                
                enriched_chunks.append(enriched_chunk)
                
            except Exception as e:
                self.logger.error(f"Error enriching chunk {chunk.get('id', 'unknown')}: {str(e)}")
                # Return original chunk if enrichment fails
                enriched_chunks.append(chunk)
        
        return enriched_chunks
    
    def _add_structural_metadata(self, chunk: Dict[str, Any], structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Add structural metadata"""
        content = chunk.get('content', '')
        
        # Find section information
        section_info = self._find_section_info(content, structure_analysis)
        
        # Analyze content hierarchy
        hierarchy_info = self._analyze_content_hierarchy(content)
        
        return {
            'section_number': section_info.get('number', 'unknown'),
            'section_title': section_info.get('title', 'unknown'),
            'section_level': section_info.get('level', 0),
            'subsection_count': hierarchy_info.get('subsection_count', 0),
            'paragraph_count': hierarchy_info.get('paragraph_count', 0),
            'list_count': hierarchy_info.get('list_count', 0),
            'heading_level': hierarchy_info.get('heading_level', 0),
            'is_section_start': hierarchy_info.get('is_section_start', False),
            'is_subsection': hierarchy_info.get('is_subsection', False)
        }
    
    def _add_content_analysis_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Add content analysis metadata"""
        content = chunk.get('content', '')
        
        # Text statistics
        text_stats = self._calculate_text_statistics(content)
        
        # Content categorization
        content_category = self._categorize_content(content)
        
        # Readability analysis
        readability = self._analyze_readability(content)
        
        # Technical complexity
        technical_complexity = self._analyze_technical_complexity(content)
        
        return {
            'word_count': text_stats['word_count'],
            'sentence_count': text_stats['sentence_count'],
            'avg_sentence_length': text_stats['avg_sentence_length'],
            'avg_word_length': text_stats['avg_word_length'],
            'content_category': content_category,
            'readability_score': readability,
            'technical_complexity': technical_complexity,
            'has_numbers': self._has_numbers(content),
            'has_formulas': self._has_formulas(content),
            'has_citations': self._has_citations(content),
            'language_complexity': self._analyze_language_complexity(content)
        }
    
    def _add_relationship_metadata(self, chunk: Dict[str, Any], tables: List[Dict[str, Any]], 
                                  examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add relationship metadata"""
        content = chunk.get('content', '')
        chunk_page = chunk.get('metadata', {}).get('page', 0)
        
        # Find related tables
        related_tables = self._find_related_tables(content, chunk_page, tables)
        
        # Find related examples
        related_examples = self._find_related_examples(content, chunk_page, examples)
        
        # Find cross-references
        cross_references = self._find_cross_references(content)
        
        return {
            'related_tables': related_tables,
            'related_examples': related_examples,
            'cross_references': cross_references,
            'table_count': len(related_tables),
            'example_count': len(related_examples),
            'reference_count': len(cross_references),
            'has_internal_links': len(cross_references) > 0
        }
    
    def _add_asc_606_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Add ASC 606 specific metadata"""
        content = chunk.get('content', '')
        
        # Find ASC 606 terms
        found_terms = self._find_asc_606_terms(content)
        
        # Analyze revenue recognition concepts
        revenue_concepts = self._analyze_revenue_concepts(content)
        
        # Find step references
        step_references = self._find_step_references(content)
        
        # Analyze performance obligation concepts
        po_concepts = self._analyze_performance_obligation_concepts(content)
        
        return {
            'asc_606_terms': found_terms,
            'revenue_concepts': revenue_concepts,
            'step_references': step_references,
            'performance_obligation_concepts': po_concepts,
            'is_guidance_text': self._is_guidance_text(content),
            'is_implementation_guidance': self._is_implementation_guidance(content),
            'is_example_text': self._is_example_text(content),
            'guidance_type': self._classify_guidance_type(content),
            'compliance_relevance': self._assess_compliance_relevance(content)
        }
    
    def _add_quality_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Add quality metadata"""
        content = chunk.get('content', '')
        
        # Text quality indicators
        quality_indicators = self._assess_text_quality(content)
        
        # Completeness indicators
        completeness = self._assess_completeness(content)
        
        # Extraction quality
        extraction_quality = self._assess_extraction_quality(content)
        
        return {
            'text_quality_score': quality_indicators['score'],
            'has_extraction_errors': quality_indicators['has_errors'],
            'is_complete': completeness['is_complete'],
            'completeness_score': completeness['score'],
            'extraction_quality': extraction_quality,
            'needs_review': quality_indicators['needs_review'],
            'confidence_score': self._calculate_confidence_score(content)
        }
    
    def _add_processing_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Add processing metadata"""
        return {
            'processing_timestamp': datetime.now().isoformat(),
            'enrichment_version': '1.0',
            'chunk_id': chunk.get('id', 'unknown'),
            'original_position': chunk.get('start_pos', 0),
            'chunk_size': chunk.get('size', len(chunk.get('content', ''))),
            'processing_method': 'semantic_chunking',
            'metadata_fields': self._count_metadata_fields(chunk.get('metadata', {}))
        }
    
    def _load_asc_606_terms(self) -> List[str]:
        """Load ASC 606 specific terms"""
        return [
            'performance obligation', 'revenue recognition', 'transaction price',
            'standalone selling price', 'contract modification', 'distinct goods',
            'distinct services', 'customer', 'contract', 'consideration',
            'variable consideration', 'constraint', 'allocate', 'satisfy',
            'transfer', 'control', 'output method', 'input method',
            'over time', 'point in time', 'principal', 'agent',
            'consignment', 'bill and hold', 'right of return',
            'warranty', 'licensing', 'repurchase agreement',
            'collectibility', 'enforceable', 'commercial substance',
            'significant financing component', 'noncash consideration',
            'consideration payable to customer', 'contract asset',
            'contract liability', 'receivable', 'refund liability'
        ]
    
    def _load_section_patterns(self) -> Dict[str, str]:
        """Load section patterns for Chapter 4"""
        return {
            '4.1': 'Identifying the promised goods and services',
            '4.1.1': 'Promised goods or services that are immaterial',
            '4.1.2': 'Shipping and handling activities',
            '4.2': 'Determining when promises are performance obligations',
            '4.2.1': 'Determination of distinct',
            '4.2.2': 'Series of distinct goods or services',
            '4.2.3': 'Examples of identifying performance obligations',
            '4.3': 'Promised goods and services that are not distinct',
            '4.4': 'Principal versus agent considerations',
            '4.4.1': 'Identifying the specified good or service',
            '4.4.2': 'Control of the specified good or service',
            '4.4.3': 'Recognizing revenue as a principal or agent',
            '4.4.4': 'Examples',
            '4.5': 'Consignment arrangements',
            '4.6': 'Customer options for additional goods or services',
            '4.7': 'Sale of products with a right of return'
        }
    
    def _find_section_info(self, content: str, structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Find section information for content"""
        # Look for section headers in content
        section_match = re.search(r'(4\.[\d.]+)\s+(.+?)(?=\n|$)', content, re.MULTILINE)
        if section_match:
            number = section_match.group(1)
            title = section_match.group(2)
            level = number.count('.') + 1
            
            return {
                'number': number,
                'title': title,
                'level': level,
                'found_in_content': True
            }
        
        # Look in structure analysis
        sections = structure_analysis.get('sections', [])
        for section in sections:
            if section.get('number', '') in content:
                return section
        
        return {
            'number': 'unknown',
            'title': 'unknown',
            'level': 0,
            'found_in_content': False
        }
    
    def _analyze_content_hierarchy(self, content: str) -> Dict[str, Any]:
        """Analyze content hierarchy"""
        # Count subsections
        subsection_count = len(re.findall(r'^4\.[\d.]+\s+', content, re.MULTILINE))
        
        # Count paragraphs
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # Count lists
        list_count = len(re.findall(r'^\s*[a-z]\.|^\s*\d+\.|^\s*[•*-]', content, re.MULTILINE))
        
        # Determine heading level
        heading_level = 0
        if re.search(r'^4\.[\d.]+\s+', content, re.MULTILINE):
            section_match = re.search(r'^(4\.[\d.]+)', content, re.MULTILINE)
            if section_match:
                heading_level = section_match.group(1).count('.') + 1
        
        return {
            'subsection_count': subsection_count,
            'paragraph_count': paragraph_count,
            'list_count': list_count,
            'heading_level': heading_level,
            'is_section_start': subsection_count > 0,
            'is_subsection': heading_level > 2
        }
    
    def _calculate_text_statistics(self, content: str) -> Dict[str, Any]:
        """Calculate text statistics"""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        
        avg_sentence_length = word_count / max(1, sentence_count)
        avg_word_length = sum(len(word) for word in words) / max(1, word_count)
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_sentence_length': avg_sentence_length,
            'avg_word_length': avg_word_length
        }
    
    def _categorize_content(self, content: str) -> str:
        """Categorize content type"""
        content_lower = content.lower()
        
        if 'example' in content_lower:
            return 'example'
        elif re.search(r'table|column|row', content_lower):
            return 'table'
        elif re.search(r'^4\.[\d.]+\s+', content):
            return 'section_header'
        elif re.search(r'^\s*[a-z]\.|^\s*\d+\.', content, re.MULTILINE):
            return 'list'
        elif 'note:' in content_lower:
            return 'note'
        else:
            return 'paragraph'
    
    def _analyze_readability(self, content: str) -> float:
        """Analyze readability score (simplified)"""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        
        if not sentences:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Simple readability score (lower is easier)
        score = min(100.0, max(0.0, 100 - (avg_sentence_length * 2)))
        
        return score
    
    def _analyze_technical_complexity(self, content: str) -> float:
        """Analyze technical complexity"""
        complexity = 0.0
        
        # Count technical terms
        for term in self.asc_606_terms:
            if term in content.lower():
                complexity += 5.0
        
        # Count numbers and references
        complexity += len(re.findall(r'\d+', content)) * 0.5
        complexity += len(re.findall(r'ASC 606', content)) * 3.0
        
        return min(100.0, complexity)
    
    def _has_numbers(self, content: str) -> bool:
        """Check if content has numbers"""
        return bool(re.search(r'\d', content))
    
    def _has_formulas(self, content: str) -> bool:
        """Check if content has formulas"""
        formula_patterns = [r'=', r'\+', r'-', r'\*', r'/', r'%']
        return any(re.search(pattern, content) for pattern in formula_patterns)
    
    def _has_citations(self, content: str) -> bool:
        """Check if content has citations"""
        citation_patterns = [r'ASC 606', r'paragraph', r'section', r'subsection']
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in citation_patterns)
    
    def _analyze_language_complexity(self, content: str) -> str:
        """Analyze language complexity"""
        words = content.split()
        
        if not words:
            return 'unknown'
        
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        if avg_word_length > 7:
            return 'high'
        elif avg_word_length > 5:
            return 'medium'
        else:
            return 'low'
    
    def _find_related_tables(self, content: str, chunk_page: int, tables: List[Dict[str, Any]]) -> List[str]:
        """Find related tables"""
        related = []
        
        for table in tables:
            # Check if table is on same page
            if table.get('page') == chunk_page:
                related.append(table.get('title', 'Unknown Table'))
            
            # Check if table is referenced in content
            if 'table' in content.lower() and str(table.get('page', 0)) in content:
                related.append(table.get('title', 'Unknown Table'))
        
        return related
    
    def _find_related_examples(self, content: str, chunk_page: int, examples: List[Dict[str, Any]]) -> List[str]:
        """Find related examples"""
        related = []
        
        for example in examples:
            # Check if example is on same page
            if example.get('page') == chunk_page:
                related.append(example.get('title', 'Unknown Example'))
            
            # Check if example is referenced in content
            if 'example' in content.lower() and example.get('number', '') in content:
                related.append(example.get('title', 'Unknown Example'))
        
        return related
    
    def _find_cross_references(self, content: str) -> List[str]:
        """Find cross-references"""
        references = []
        
        # ASC 606 references
        asc_refs = re.findall(r'ASC 606[-\s]\d+[-\s]\d+[-\s]\d+', content)
        references.extend(asc_refs)
        
        # Paragraph references
        para_refs = re.findall(r'paragraph\s+\d+[-\s]\d+[-\s]\d+', content)
        references.extend(para_refs)
        
        # Section references
        section_refs = re.findall(r'section\s+\d+\.[\d.]+', content)
        references.extend(section_refs)
        
        return references
    
    def _find_asc_606_terms(self, content: str) -> List[str]:
        """Find ASC 606 terms in content"""
        found_terms = []
        content_lower = content.lower()
        
        for term in self.asc_606_terms:
            if term in content_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _analyze_revenue_concepts(self, content: str) -> List[str]:
        """Analyze revenue recognition concepts"""
        concepts = []
        content_lower = content.lower()
        
        concept_patterns = {
            'control': r'control|transfer|obtain',
            'satisfaction': r'satisf|complet|fulfill',
            'timing': r'over time|point in time|when|as',
            'measurement': r'measure|amount|price|consideration'
        }
        
        for concept, pattern in concept_patterns.items():
            if re.search(pattern, content_lower):
                concepts.append(concept)
        
        return concepts
    
    def _find_step_references(self, content: str) -> List[str]:
        """Find five-step model references"""
        steps = []
        
        step_patterns = [
            r'step\s+\d+',
            r'identify.*contract',
            r'identify.*performance obligation',
            r'determine.*transaction price',
            r'allocate.*transaction price',
            r'recognize.*revenue'
        ]
        
        for pattern in step_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                steps.append(pattern)
        
        return steps
    
    def _analyze_performance_obligation_concepts(self, content: str) -> List[str]:
        """Analyze performance obligation concepts"""
        concepts = []
        content_lower = content.lower()
        
        po_concepts = [
            'distinct', 'bundle', 'separate', 'combined', 'standalone',
            'series', 'substantially the same', 'pattern of transfer'
        ]
        
        for concept in po_concepts:
            if concept in content_lower:
                concepts.append(concept)
        
        return concepts
    
    def _is_guidance_text(self, content: str) -> bool:
        """Check if content is guidance text"""
        guidance_indicators = [
            'shall', 'should', 'must', 'entity', 'guidance', 'standard'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in guidance_indicators)
    
    def _is_implementation_guidance(self, content: str) -> bool:
        """Check if content is implementation guidance"""
        impl_indicators = [
            'implementation', 'application', 'practice', 'consider', 'factors'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in impl_indicators)
    
    def _is_example_text(self, content: str) -> bool:
        """Check if content is example text"""
        return 'example' in content.lower() or 'illustration' in content.lower()
    
    def _classify_guidance_type(self, content: str) -> str:
        """Classify guidance type"""
        if self._is_example_text(content):
            return 'example'
        elif self._is_implementation_guidance(content):
            return 'implementation'
        elif self._is_guidance_text(content):
            return 'standard'
        else:
            return 'descriptive'
    
    def _assess_compliance_relevance(self, content: str) -> str:
        """Assess compliance relevance"""
        high_relevance_terms = [
            'shall', 'must', 'required', 'prohibit', 'mandatory'
        ]
        
        medium_relevance_terms = [
            'should', 'recommend', 'consider', 'may', 'might'
        ]
        
        content_lower = content.lower()
        
        if any(term in content_lower for term in high_relevance_terms):
            return 'high'
        elif any(term in content_lower for term in medium_relevance_terms):
            return 'medium'
        else:
            return 'low'
    
    def _assess_text_quality(self, content: str) -> Dict[str, Any]:
        """Assess text quality"""
        score = 100.0
        has_errors = False
        needs_review = False
        
        # Check for extraction errors
        if re.search(r'[^\w\s\.\,\!\?\:\;\(\)\[\]\{\}\"\'"-]', content):
            score -= 20.0
            has_errors = True
        
        # Check for excessive whitespace
        if re.search(r'\s{3,}', content):
            score -= 10.0
            has_errors = True
        
        # Check for incomplete sentences
        if len(content) < 50:
            score -= 15.0
            needs_review = True
        
        return {
            'score': max(0.0, score),
            'has_errors': has_errors,
            'needs_review': needs_review
        }
    
    def _assess_completeness(self, content: str) -> Dict[str, Any]:
        """Assess content completeness"""
        score = 100.0
        
        # Check length
        if len(content) < 100:
            score -= 30.0
        
        # Check for proper sentences
        if not re.search(r'[.!?]', content):
            score -= 40.0
        
        # Check for proper structure
        if not re.search(r'[A-Z]', content):
            score -= 20.0
        
        is_complete = score > 70.0
        
        return {
            'score': max(0.0, score),
            'is_complete': is_complete
        }
    
    def _assess_extraction_quality(self, content: str) -> float:
        """Assess extraction quality"""
        score = 100.0
        
        # Penalize for extraction artifacts
        artifacts = [
            r'[^\w\s\.\,\!\?\:\;\(\)\[\]\{\}\"\'"-]',
            r'\s{5,}',
            r'[A-Z]{10,}',
            r'\d{10,}'
        ]
        
        for artifact in artifacts:
            if re.search(artifact, content):
                score -= 15.0
        
        return max(0.0, score)
    
    def _calculate_confidence_score(self, content: str) -> float:
        """Calculate confidence score"""
        score = 50.0  # Base score
        
        # Add score for proper formatting
        if re.search(r'[.!?]', content):
            score += 20.0
        
        # Add score for proper capitalization
        if re.search(r'^[A-Z]', content, re.MULTILINE):
            score += 15.0
        
        # Add score for relevant terms
        if any(term in content.lower() for term in self.asc_606_terms):
            score += 15.0
        
        return min(100.0, score)
    
    def _count_metadata_fields(self, metadata: Dict[str, Any]) -> int:
        """Count metadata fields"""
        return len(metadata)
