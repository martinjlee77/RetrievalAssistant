import re
from typing import Dict, List, Any, Optional
import logging

class QualityValidator:
    """Quality validation system for ASC 606 PDF processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_processing(self, chunks: List[Dict[str, Any]], structure_analysis: Dict[str, Any], 
                          tables: List[Dict[str, Any]], examples: List[Dict[str, Any]], 
                          quality_threshold: float) -> Dict[str, Any]:
        """Comprehensive quality validation of processing results"""
        
        try:
            # Calculate individual quality metrics
            text_quality = self._validate_text_quality(chunks)
            structure_quality = self._validate_structure_quality(structure_analysis)
            table_quality = self._validate_table_quality(tables)
            example_quality = self._validate_example_quality(examples)
            
            # Calculate detailed metrics
            character_accuracy = self._calculate_character_accuracy(chunks)
            section_hierarchy = self._validate_section_hierarchy(structure_analysis)
            cross_references = self._validate_cross_references(chunks)
            table_formatting = self._validate_table_formatting(tables)
            example_integrity = self._validate_example_integrity(examples)
            
            # Calculate overall score
            overall_score = (
                text_quality * 0.3 +
                structure_quality * 0.25 +
                table_quality * 0.2 +
                example_quality * 0.25
            )
            
            # Identify issues and recommendations
            issues = self._identify_issues(chunks, structure_analysis, tables, examples, quality_threshold)
            recommendations = self._generate_recommendations(issues, overall_score, quality_threshold)
            
            return {
                'overall_score': overall_score,
                'text_quality': text_quality,
                'structure_quality': structure_quality,
                'table_quality': table_quality,
                'example_quality': example_quality,
                'character_accuracy': character_accuracy,
                'section_hierarchy': section_hierarchy,
                'cross_references': cross_references,
                'table_formatting': table_formatting,
                'example_integrity': example_integrity,
                'issues': issues,
                'recommendations': recommendations,
                'meets_threshold': overall_score >= quality_threshold,
                'validation_timestamp': self._get_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Error in quality validation: {str(e)}")
            return self._create_error_result(str(e))
    
    def _validate_text_quality(self, chunks: List[Dict[str, Any]]) -> float:
        """Validate text extraction quality"""
        if not chunks:
            return 0.0
        
        total_score = 0.0
        
        for chunk in chunks:
            content = chunk.get('content', '')
            chunk_score = 100.0
            
            # Check for common extraction errors
            if self._has_extraction_errors(content):
                chunk_score -= 20.0
            
            # Check for incomplete sentences
            if self._has_incomplete_sentences(content):
                chunk_score -= 15.0
            
            # Check for proper formatting
            if not self._has_proper_formatting(content):
                chunk_score -= 10.0
            
            # Check for missing characters
            if self._has_missing_characters(content):
                chunk_score -= 25.0
            
            total_score += max(0.0, chunk_score)
        
        return total_score / len(chunks)
    
    def _validate_structure_quality(self, structure_analysis: Dict[str, Any]) -> float:
        """Validate structure preservation quality"""
        score = 100.0
        
        # Check section count
        sections = structure_analysis.get('sections', [])
        expected_sections = 7  # Approximate number of main sections in Chapter 4
        
        if len(sections) < expected_sections * 0.8:
            score -= 30.0
        
        # Check hierarchy depth
        hierarchy_depth = structure_analysis.get('hierarchy_depth', 0)
        if hierarchy_depth < 3:  # Should have at least 3 levels (4, 4.1, 4.1.1)
            score -= 20.0
        
        # Check for proper section numbering
        if not self._has_proper_section_numbering(sections):
            score -= 25.0
        
        return max(0.0, score)
    
    def _validate_table_quality(self, tables: List[Dict[str, Any]]) -> float:
        """Validate table extraction quality"""
        if not tables:
            return 60.0  # Partial score if no tables found
        
        total_score = 0.0
        
        for table in tables:
            table_score = 100.0
            
            # Check for proper structure
            if table.get('rows', 0) == 0:
                table_score -= 40.0
            
            if table.get('columns', 0) == 0:
                table_score -= 30.0
            
            # Check for content
            if not table.get('content'):
                table_score -= 30.0
            
            total_score += max(0.0, table_score)
        
        return total_score / len(tables)
    
    def _validate_example_quality(self, examples: List[Dict[str, Any]]) -> float:
        """Validate example extraction quality"""
        if not examples:
            return 50.0  # Partial score if no examples found
        
        total_score = 0.0
        
        for example in examples:
            example_score = 100.0
            
            # Check completeness
            completeness = example.get('completeness', 0)
            if completeness < 80:
                example_score -= 30.0
            
            # Check content length
            content = example.get('content', '')
            if len(content) < 100:
                example_score -= 25.0
            
            # Check for key components
            if not self._has_example_components(content):
                example_score -= 20.0
            
            total_score += max(0.0, example_score)
        
        return total_score / len(examples)
    
    def _calculate_character_accuracy(self, chunks: List[Dict[str, Any]]) -> float:
        """Calculate character-level accuracy"""
        if not chunks:
            return 0.0
        
        total_chars = 0
        error_chars = 0
        
        for chunk in chunks:
            content = chunk.get('content', '')
            total_chars += len(content)
            
            # Count potential character errors
            error_chars += self._count_character_errors(content)
        
        if total_chars == 0:
            return 0.0
        
        accuracy = ((total_chars - error_chars) / total_chars) * 100
        return max(0.0, accuracy)
    
    def _validate_section_hierarchy(self, structure_analysis: Dict[str, Any]) -> float:
        """Validate section hierarchy preservation"""
        sections = structure_analysis.get('sections', [])
        
        if not sections:
            return 0.0
        
        score = 100.0
        
        # Check for proper sequence
        section_numbers = [s.get('number', '') for s in sections]
        if not self._is_proper_sequence(section_numbers):
            score -= 40.0
        
        # Check for missing critical sections
        critical_sections = ['4.1', '4.2', '4.3', '4.4']
        found_critical = sum(1 for num in section_numbers if num in critical_sections)
        if found_critical < len(critical_sections):
            score -= 30.0
        
        return max(0.0, score)
    
    def _validate_cross_references(self, chunks: List[Dict[str, Any]]) -> float:
        """Validate cross-references preservation"""
        total_refs = 0
        valid_refs = 0
        
        for chunk in chunks:
            content = chunk.get('content', '')
            
            # Find ASC 606 references
            asc_refs = re.findall(r'ASC 606[-\s]\d+[-\s]\d+[-\s]\d+', content)
            total_refs += len(asc_refs)
            
            # Count valid references (proper format)
            valid_refs += sum(1 for ref in asc_refs if self._is_valid_reference(ref))
            
            # Find internal references
            internal_refs = re.findall(r'paragraph\s+\d+[-\s]\d+[-\s]\d+', content)
            total_refs += len(internal_refs)
            valid_refs += len(internal_refs)  # Assume internal refs are valid
        
        if total_refs == 0:
            return 85.0  # Good score if no references to validate
        
        return (valid_refs / total_refs) * 100
    
    def _validate_table_formatting(self, tables: List[Dict[str, Any]]) -> float:
        """Validate table formatting quality"""
        if not tables:
            return 75.0  # Neutral score if no tables
        
        total_score = 0.0
        
        for table in tables:
            score = 100.0
            
            # Check quality score if available
            if 'quality_score' in table:
                score = table['quality_score']
            else:
                # Basic validation
                if not table.get('content'):
                    score -= 50.0
                if table.get('rows', 0) == 0:
                    score -= 30.0
                if table.get('columns', 0) == 0:
                    score -= 20.0
            
            total_score += max(0.0, score)
        
        return total_score / len(tables)
    
    def _validate_example_integrity(self, examples: List[Dict[str, Any]]) -> float:
        """Validate example integrity"""
        if not examples:
            return 60.0  # Partial score if no examples
        
        total_score = 0.0
        
        for example in examples:
            score = example.get('completeness', 50.0)
            total_score += score
        
        return total_score / len(examples)
    
    def _has_extraction_errors(self, content: str) -> bool:
        """Check for common extraction errors"""
        error_patterns = [
            r'[^\w\s\.\,\!\?\:\;\(\)\[\]\{\}\"\']+',  # Unusual characters
            r'\s{5,}',  # Excessive whitespace
            r'[A-Z]{10,}',  # Excessive capitalization
            r'\d{10,}',  # Excessive numbers
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _has_incomplete_sentences(self, content: str) -> bool:
        """Check for incomplete sentences"""
        sentences = re.split(r'[.!?]', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) < 10:  # Very short sentence
                return True
            if sentence and not re.match(r'^[A-Z]', sentence):  # Doesn't start with capital
                return True
        
        return False
    
    def _has_proper_formatting(self, content: str) -> bool:
        """Check for proper formatting"""
        # Check for basic formatting elements
        has_paragraphs = '\n\n' in content or len(content.split('\n')) > 1
        has_proper_sentences = re.search(r'[.!?]', content)
        
        return has_paragraphs and has_proper_sentences
    
    def _has_missing_characters(self, content: str) -> bool:
        """Check for missing characters"""
        # Look for patterns that suggest missing characters
        missing_patterns = [
            r'\s[a-z]',  # Single lowercase letter after space
            r'[A-Z][a-z]*[A-Z]',  # Mixed case within word
            r'\d[A-Za-z]',  # Number directly followed by letter
            r'[A-Za-z]\d',  # Letter directly followed by number
        ]
        
        for pattern in missing_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _has_proper_section_numbering(self, sections: List[Dict[str, Any]]) -> bool:
        """Check if sections have proper numbering"""
        if not sections:
            return False
        
        # Check for expected section pattern
        section_numbers = [s.get('number', '') for s in sections]
        
        # Should start with 4.
        if not any(num.startswith('4.') for num in section_numbers):
            return False
        
        # Should have reasonable progression
        main_sections = [num for num in section_numbers if re.match(r'^4\.\d+$', num)]
        if len(main_sections) < 3:  # Should have at least 3 main sections
            return False
        
        return True
    
    def _has_example_components(self, content: str) -> bool:
        """Check if example has proper components"""
        content_lower = content.lower()
        
        # Check for typical example components
        components = [
            'facts', 'analysis', 'conclusion', 'scenario', 'entity', 'customer'
        ]
        
        found_components = sum(1 for comp in components if comp in content_lower)
        return found_components >= 2
    
    def _count_character_errors(self, content: str) -> int:
        """Count potential character errors"""
        error_count = 0
        
        # Count unusual character sequences
        error_count += len(re.findall(r'[^\w\s\.\,\!\?\:\;\(\)\[\]\{\}\"\'"-]', content))
        
        # Count excessive whitespace
        error_count += len(re.findall(r'\s{3,}', content))
        
        # Count malformed words
        error_count += len(re.findall(r'\b[A-Z][a-z]*[A-Z][a-z]*\b', content))
        
        return error_count
    
    def _is_proper_sequence(self, section_numbers: List[str]) -> bool:
        """Check if section numbers are in proper sequence"""
        if not section_numbers:
            return False
        
        # Filter for Chapter 4 sections
        chapter_4_sections = [num for num in section_numbers if num.startswith('4.')]
        
        if len(chapter_4_sections) < 3:
            return False
        
        # Check for basic sequence
        has_4_1 = any('4.1' in num for num in chapter_4_sections)
        has_4_2 = any('4.2' in num for num in chapter_4_sections)
        
        return has_4_1 and has_4_2
    
    def _is_valid_reference(self, reference: str) -> bool:
        """Check if reference is valid format"""
        # Basic format validation for ASC 606 references
        return re.match(r'ASC 606[-\s]\d+[-\s]\d+[-\s]\d+', reference) is not None
    
    def _identify_issues(self, chunks: List[Dict[str, Any]], structure_analysis: Dict[str, Any], 
                        tables: List[Dict[str, Any]], examples: List[Dict[str, Any]], 
                        quality_threshold: float) -> List[str]:
        """Identify quality issues"""
        issues = []
        
        # Check chunks
        if not chunks:
            issues.append("No chunks were created from the document")
        elif len(chunks) < 5:
            issues.append("Very few chunks created - may indicate extraction problems")
        
        # Check structure
        sections = structure_analysis.get('sections', [])
        if len(sections) < 5:
            issues.append("Insufficient section headers detected - structure may be compromised")
        
        # Check tables
        if not tables:
            issues.append("No tables detected - Chapter 4 typically contains tabular data")
        
        # Check examples
        if not examples:
            issues.append("No examples detected - Chapter 4 should contain example scenarios")
        
        # Check for critical sections
        section_numbers = [s.get('number', '') for s in sections]
        critical_sections = ['4.1', '4.2', '4.4']
        missing_critical = [sec for sec in critical_sections if not any(sec in num for num in section_numbers)]
        
        if missing_critical:
            issues.append(f"Missing critical sections: {', '.join(missing_critical)}")
        
        return issues
    
    def _generate_recommendations(self, issues: List[str], overall_score: float, 
                                quality_threshold: float) -> List[str]:
        """Generate recommendations based on issues"""
        recommendations = []
        
        if overall_score < quality_threshold:
            recommendations.append("Overall quality below threshold - consider manual review")
        
        if any("chunks" in issue for issue in issues):
            recommendations.append("Review chunking parameters - consider smaller chunk size or different overlap")
        
        if any("section" in issue for issue in issues):
            recommendations.append("Review section detection - may need manual section identification")
        
        if any("table" in issue for issue in issues):
            recommendations.append("Use specialized table extraction tools or manual table processing")
        
        if any("example" in issue for issue in issues):
            recommendations.append("Implement specialized example detection patterns")
        
        if overall_score > quality_threshold:
            recommendations.append("Quality acceptable - proceed with RAG implementation")
        
        return recommendations
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'overall_score': 0.0,
            'text_quality': 0.0,
            'structure_quality': 0.0,
            'table_quality': 0.0,
            'example_quality': 0.0,
            'character_accuracy': 0.0,
            'section_hierarchy': 0.0,
            'cross_references': 0.0,
            'table_formatting': 0.0,
            'example_integrity': 0.0,
            'issues': [f"Validation error: {error_message}"],
            'recommendations': ["Fix validation errors and retry processing"],
            'meets_threshold': False,
            'validation_timestamp': self._get_timestamp()
        }
