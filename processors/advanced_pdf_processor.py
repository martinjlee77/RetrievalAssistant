import io
import logging
from typing import Dict, Any, List, Optional
import tempfile
import os
from datetime import datetime

# Import new processors
from .layout_analyzer import LayoutAnalyzer
from .table_extractor import TableExtractor
from .structure_aware_chunker import StructureAwareChunker

class AdvancedPDFProcessor:
    """Advanced PDF processor using coordinate-based layout analysis and specialized table extraction"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Initialize specialized processors
        self.layout_analyzer = LayoutAnalyzer()
        self.table_extractor = TableExtractor()
        self.structure_chunker = StructureAwareChunker()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(level=logging.INFO)
        
    def extract_chapter_4(self, uploaded_file) -> Dict[str, Any]:
        """Extract Chapter 4 using advanced structure-aware processing"""
        try:
            # Save uploaded file to temporary location
            temp_pdf_path = self._save_temp_file(uploaded_file)
            
            if not temp_pdf_path:
                return self._create_error_result("Failed to save temporary file")
            
            # Process with advanced pipeline
            result = self._process_with_advanced_pipeline(temp_pdf_path)
            
            # Cleanup
            self._cleanup_temp_file(temp_pdf_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in advanced PDF processing: {str(e)}")
            return self._create_error_result(str(e))
    
    def _process_with_advanced_pipeline(self, pdf_path: str) -> Dict[str, Any]:
        """Process PDF using advanced pipeline following Gemini's recommendations"""
        
        # Step 1: Layout Analysis using coordinate-based approach
        self.logger.info("Starting coordinate-based layout analysis...")
        structure = self.layout_analyzer.analyze_document_structure(
            pdf_path, 
            page_range=(63, 83)  # Chapter 4 pages
        )
        
        # Step 2: Specialized table extraction
        self.logger.info("Extracting tables using specialized tools...")
        tables = self.table_extractor.extract_tables_from_pdf(
            pdf_path, 
            structure['table_regions']
        )
        
        # Step 3: Structure-aware chunking
        self.logger.info("Creating structure-aware chunks...")
        chunks = self.structure_chunker.create_structure_chunks(
            structure['text_blocks'],
            structure['sections'],
            tables,
            structure['page_layouts']
        )
        
        # Step 4: Validate processing quality
        chunk_validation = self.structure_chunker.validate_chunks(chunks)
        
        # Step 5: Calculate overall quality metrics
        quality_metrics = self._calculate_quality_metrics(structure, tables, chunks)
        
        # Step 6: Generate processing report
        processing_report = self._generate_processing_report(
            structure, tables, chunks, quality_metrics
        )
        
        return {
            'success': True,
            'processing_method': 'advanced_structure_aware',
            'chapter_content': {
                'text': self._combine_chunk_content(chunks),
                'structure': structure,
                'chunks': [self._chunk_to_dict(chunk) for chunk in chunks],
                'tables': tables,
                'pages': structure['page_layouts']
            },
            'quality_metrics': quality_metrics,
            'processing_report': processing_report,
            'chunk_validation': chunk_validation,
            'timestamp': datetime.now().isoformat()
        }
    
    def _save_temp_file(self, uploaded_file) -> Optional[str]:
        """Save uploaded file to temporary location"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_path = temp_file.name
                
                # Write uploaded file content
                uploaded_file.seek(0)
                temp_file.write(uploaded_file.read())
                
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Failed to save temporary file: {str(e)}")
            return None
    
    def _cleanup_temp_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp file: {str(e)}")
    
    def _combine_chunk_content(self, chunks: List[Any]) -> str:
        """Combine chunk content into full text"""
        content_parts = []
        
        current_section = None
        for chunk in chunks:
            # Add section headers
            if chunk.chunk_type == 'section_header':
                content_parts.append(f"\n\n{chunk.content}\n{'=' * len(chunk.content)}")
                current_section = chunk.section_number
            elif chunk.chunk_type == 'subsection':
                content_parts.append(f"\n\n{chunk.content}\n{'-' * len(chunk.content)}")
            else:
                content_parts.append(f"\n{chunk.content}")
        
        return "\n".join(content_parts)
    
    def _chunk_to_dict(self, chunk: Any) -> Dict[str, Any]:
        """Convert chunk object to dictionary"""
        return {
            'content': chunk.content,
            'chunk_type': chunk.chunk_type,
            'section_number': chunk.section_number,
            'section_title': chunk.section_title,
            'page_numbers': chunk.page_numbers,
            'bbox': chunk.bbox,
            'metadata': chunk.metadata,
            'confidence': chunk.confidence,
            'word_count': len(chunk.content.split()),
            'char_count': len(chunk.content)
        }
    
    def _calculate_quality_metrics(self, structure: Dict[str, Any], 
                                 tables: List[Dict[str, Any]], 
                                 chunks: List[Any]) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics"""
        
        metrics = {
            'structure_quality': self._assess_structure_quality(structure),
            'table_quality': self._assess_table_quality(tables),
            'chunk_quality': self._assess_chunk_quality(chunks),
            'coverage_quality': self._assess_coverage_quality(structure, chunks),
            'overall_score': 0.0
        }
        
        # Calculate weighted overall score
        weights = {
            'structure_quality': 0.3,
            'table_quality': 0.25,
            'chunk_quality': 0.25,
            'coverage_quality': 0.2
        }
        
        overall_score = sum(
            metrics[metric] * weight 
            for metric, weight in weights.items()
        )
        
        metrics['overall_score'] = overall_score
        
        return metrics
    
    def _assess_structure_quality(self, structure: Dict[str, Any]) -> float:
        """Assess structure detection quality"""
        score = 0.0
        
        # Check section detection
        sections = structure.get('sections', [])
        if len(sections) >= 5:  # Expect at least 5 sections in Chapter 4
            score += 0.4
        elif len(sections) >= 3:
            score += 0.2
        
        # Check text block quality
        text_blocks = structure.get('text_blocks', [])
        if len(text_blocks) >= 50:  # Expect substantial text blocks
            score += 0.3
        elif len(text_blocks) >= 20:
            score += 0.15
        
        # Check page coverage
        page_layouts = structure.get('page_layouts', [])
        expected_pages = 21  # Pages 63-83
        if len(page_layouts) >= expected_pages * 0.8:
            score += 0.3
        elif len(page_layouts) >= expected_pages * 0.5:
            score += 0.15
        
        return min(1.0, score)
    
    def _assess_table_quality(self, tables: List[Dict[str, Any]]) -> float:
        """Assess table extraction quality"""
        if not tables:
            return 0.0
        
        score = 0.0
        total_quality = sum(table.get('quality_score', 0) for table in tables)
        avg_quality = total_quality / len(tables)
        
        score += avg_quality * 0.6  # Weight by extraction quality
        
        # Bonus for finding expected number of tables
        if len(tables) >= 3:  # Expect at least 3 tables in Chapter 4
            score += 0.2
        elif len(tables) >= 1:
            score += 0.1
        
        # Bonus for table diversity
        table_types = set(table.get('table_type', 'unknown') for table in tables)
        if len(table_types) > 1:
            score += 0.2
        
        return min(1.0, score)
    
    def _assess_chunk_quality(self, chunks: List[Any]) -> float:
        """Assess chunk creation quality"""
        if not chunks:
            return 0.0
        
        score = 0.0
        
        # Average chunk confidence
        avg_confidence = sum(chunk.confidence for chunk in chunks) / len(chunks)
        score += avg_confidence * 0.4
        
        # Chunk type diversity
        chunk_types = set(chunk.chunk_type for chunk in chunks)
        if len(chunk_types) >= 4:
            score += 0.3
        elif len(chunk_types) >= 2:
            score += 0.15
        
        # Reasonable chunk sizes
        reasonable_chunks = sum(
            1 for chunk in chunks 
            if 50 <= len(chunk.content.split()) <= 500
        )
        if len(chunks) > 0:
            size_score = reasonable_chunks / len(chunks)
            score += size_score * 0.3
        
        return min(1.0, score)
    
    def _assess_coverage_quality(self, structure: Dict[str, Any], chunks: List[Any]) -> float:
        """Assess how well chunks cover the document"""
        score = 0.0
        
        # Page coverage
        expected_pages = set(range(63, 84))  # Pages 63-83
        covered_pages = set()
        
        for chunk in chunks:
            covered_pages.update(chunk.page_numbers)
        
        page_coverage = len(covered_pages & expected_pages) / len(expected_pages)
        score += page_coverage * 0.5
        
        # Section coverage
        sections = structure.get('sections', [])
        section_numbers = set(section['number'] for section in sections)
        
        chunk_sections = set(chunk.section_number for chunk in chunks)
        if section_numbers:
            section_coverage = len(chunk_sections & section_numbers) / len(section_numbers)
            score += section_coverage * 0.5
        
        return min(1.0, score)
    
    def _generate_processing_report(self, structure: Dict[str, Any], 
                                  tables: List[Dict[str, Any]], 
                                  chunks: List[Any], 
                                  quality_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive processing report"""
        
        return {
            'processing_summary': {
                'total_pages_processed': len(structure.get('page_layouts', [])),
                'sections_detected': len(structure.get('sections', [])),
                'text_blocks_extracted': len(structure.get('text_blocks', [])),
                'tables_extracted': len(tables),
                'chunks_created': len(chunks),
                'processing_time': datetime.now().isoformat()
            },
            'quality_summary': {
                'overall_score': quality_metrics['overall_score'],
                'structure_score': quality_metrics['structure_quality'],
                'table_score': quality_metrics['table_quality'],
                'chunk_score': quality_metrics['chunk_quality'],
                'coverage_score': quality_metrics['coverage_quality']
            },
            'content_analysis': {
                'section_titles': [
                    f"{s['number']} {s['title']}" 
                    for s in structure.get('sections', [])
                ],
                'table_types': [
                    table.get('table_type', 'unknown') 
                    for table in tables
                ],
                'chunk_types': {
                    chunk_type: len([c for c in chunks if c.chunk_type == chunk_type])
                    for chunk_type in set(chunk.chunk_type for chunk in chunks)
                }
            },
            'recommendations': self._generate_recommendations(quality_metrics)
        }
    
    def _generate_recommendations(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality metrics"""
        recommendations = []
        
        overall_score = quality_metrics['overall_score']
        
        if overall_score >= 0.85:
            recommendations.append("Excellent processing quality - proceed with RAG system development")
        elif overall_score >= 0.75:
            recommendations.append("Good processing quality - suitable for RAG with minor refinements")
        elif overall_score >= 0.65:
            recommendations.append("Moderate quality - review and validate extracted content")
        else:
            recommendations.append("Low quality - consider manual review or alternative processing")
        
        # Specific recommendations
        if quality_metrics['structure_quality'] < 0.7:
            recommendations.append("Consider manual validation of section detection")
        
        if quality_metrics['table_quality'] < 0.7:
            recommendations.append("Review table extraction results and consider manual correction")
        
        if quality_metrics['chunk_quality'] < 0.7:
            recommendations.append("Adjust chunking parameters for better content organization")
        
        if quality_metrics['coverage_quality'] < 0.8:
            recommendations.append("Verify that all relevant content has been captured")
        
        return recommendations
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'success': False,
            'error': error_message,
            'processing_method': 'advanced_structure_aware',
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_structure(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document structure (compatibility method)"""
        return content.get('structure', {})
    
    def extract_tables(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tables (compatibility method)"""
        return content.get('tables', [])
    
    def extract_examples(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract examples from chunks"""
        examples = []
        chunks = content.get('chunks', [])
        
        for chunk in chunks:
            if chunk.get('chunk_type') in ['example', 'illustration']:
                examples.append({
                    'content': chunk.get('content', ''),
                    'type': chunk.get('chunk_type'),
                    'section': chunk.get('section_number'),
                    'page': chunk.get('page_numbers', [0])[0] if chunk.get('page_numbers') else 0,
                    'confidence': chunk.get('confidence', 0.0)
                })
        
        return examples