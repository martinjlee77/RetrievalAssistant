import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class Chunk:
    """Represents a processed chunk of content"""
    content: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]
    
class ChunkProcessor:
    """Intelligent chunking processor for ASC 606 documents"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_chunks(self, content: Dict[str, Any], chunk_size: int, overlap_percentage: int) -> List[Dict[str, Any]]:
        """Create semantic chunks from document content"""
        try:
            text = content.get('text', '')
            if not text:
                return []
            
            # Calculate overlap size
            overlap_size = int(chunk_size * overlap_percentage / 100)
            
            # Apply semantic chunking strategy
            chunks = self._semantic_chunking(text, chunk_size, overlap_size)
            
            # Enhance chunks with metadata
            enhanced_chunks = self._enhance_chunks(chunks, content)
            
            return enhanced_chunks
            
        except Exception as e:
            self.logger.error(f"Error creating chunks: {str(e)}")
            return []
    
    def _semantic_chunking(self, text: str, chunk_size: int, overlap_size: int) -> List[Chunk]:
        """Perform semantic chunking respecting document boundaries"""
        chunks = []
        
        # Split text into semantic units
        semantic_units = self._split_into_semantic_units(text)
        
        current_chunk = ""
        current_start = 0
        
        for i, unit in enumerate(semantic_units):
            # Check if adding this unit would exceed chunk size
            if len(current_chunk) + len(unit) > chunk_size and current_chunk:
                # Create chunk
                chunk = Chunk(
                    content=current_chunk.strip(),
                    start_pos=current_start,
                    end_pos=current_start + len(current_chunk),
                    metadata={}
                )
                chunks.append(chunk)
                
                # Calculate overlap for next chunk
                overlap_text = self._get_overlap_text(current_chunk, overlap_size)
                current_chunk = overlap_text + unit
                current_start = current_start + len(current_chunk) - len(overlap_text)
            else:
                if not current_chunk:
                    current_start = text.find(unit)
                current_chunk += unit
        
        # Add final chunk
        if current_chunk.strip():
            chunk = Chunk(
                content=current_chunk.strip(),
                start_pos=current_start,
                end_pos=current_start + len(current_chunk),
                metadata={}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_semantic_units(self, text: str) -> List[str]:
        """Split text into semantic units (paragraphs, sections, etc.)"""
        units = []
        
        # Split by section headers first
        section_pattern = r'(^4\.[\d.]+\s+.+?$)'
        sections = re.split(section_pattern, text, flags=re.MULTILINE)
        
        for section in sections:
            if not section.strip():
                continue
                
            # If it's a section header, keep it as one unit
            if re.match(r'^4\.[\d.]+\s+', section):
                units.append(section + '\n')
            else:
                # Split into paragraphs
                paragraphs = re.split(r'\n\s*\n', section)
                for paragraph in paragraphs:
                    if paragraph.strip():
                        units.append(paragraph + '\n\n')
        
        return units
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from the end of current chunk"""
        if len(text) <= overlap_size:
            return text
        
        # Try to find a good sentence boundary for overlap
        sentences = re.split(r'[.!?]\s+', text)
        if len(sentences) > 1:
            # Take the last few sentences that fit in overlap size
            overlap_text = ""
            for sentence in reversed(sentences[:-1]):  # Exclude the last incomplete sentence
                if len(overlap_text) + len(sentence) <= overlap_size:
                    overlap_text = sentence + ". " + overlap_text
                else:
                    break
            
            if overlap_text:
                return overlap_text
        
        # Fallback: take last N characters
        return text[-overlap_size:]
    
    def _enhance_chunks(self, chunks: List[Chunk], content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance chunks with rich metadata"""
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            # Determine section
            section = self._determine_section(chunk.content)
            
            # Determine page
            page = self._determine_page(chunk.start_pos, content)
            
            # Determine content type
            content_type = self._determine_content_type(chunk.content)
            
            # Create enhanced chunk
            enhanced_chunk = {
                'id': f"chunk_{i+1}",
                'content': chunk.content,
                'start_pos': chunk.start_pos,
                'end_pos': chunk.end_pos,
                'size': len(chunk.content),
                'word_count': len(chunk.content.split()),
                'metadata': {
                    'section': section,
                    'page': page,
                    'content_type': content_type,
                    'chapter': 4,
                    'has_examples': 'example' in chunk.content.lower(),
                    'has_tables': self._has_table_content(chunk.content),
                    'has_references': 'ASC 606' in chunk.content,
                    'complexity_score': self._calculate_complexity_score(chunk.content),
                    'key_terms': self._extract_key_terms(chunk.content)
                }
            }
            
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def _determine_section(self, content: str) -> str:
        """Determine the section for a chunk"""
        # Look for section headers in content
        section_match = re.search(r'(4\.[\d.]+)\s+(.+?)(?=\n|$)', content, re.MULTILINE)
        if section_match:
            return f"{section_match.group(1)} {section_match.group(2)}"
        
        # Look for section references
        section_patterns = [
            r'4\.1\.1\s+Promised goods or services that are immaterial',
            r'4\.1\.2\s+Shipping and handling activities',
            r'4\.2\.1\s+Determination of distinct',
            r'4\.2\.2\s+Series of distinct goods or services',
            r'4\.2\.3\s+Examples of identifying performance obligations',
            r'4\.3\s+Promised goods and services that are not distinct',
            r'4\.4\s+Principal versus agent considerations',
            r'4\.5\s+Consignment arrangements',
            r'4\.6\s+Customer options for additional goods or services',
            r'4\.7\s+Sale of products with a right of return'
        ]
        
        for pattern in section_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                match = re.search(pattern, content, re.IGNORECASE)
                return match.group(0)
        
        return "4.0 General"
    
    def _determine_page(self, start_pos: int, content: Dict[str, Any]) -> int:
        """Determine page number for a chunk"""
        # Look for page markers in the text
        text = content.get('text', '')
        text_before = text[:start_pos]
        
        # Find page markers
        page_markers = re.findall(r'--- Page (\d+) ---', text_before)
        if page_markers:
            return int(page_markers[-1])
        
        # Use pages metadata if available
        pages = content.get('pages', [])
        if pages:
            # Estimate based on text length
            chars_per_page = len(text) / len(pages)
            estimated_page_index = int(start_pos / chars_per_page)
            if 0 <= estimated_page_index < len(pages):
                return pages[estimated_page_index]['page_number']
        
        # Fallback: estimate based on position
        return max(63, min(83, 63 + start_pos // 3000))
    
    def _determine_content_type(self, content: str) -> str:
        """Determine the type of content in a chunk"""
        content_lower = content.lower()
        
        # Check for specific content types
        if 'example' in content_lower or 'illustration' in content_lower:
            return 'example'
        
        if re.search(r'(table|column|row)', content_lower):
            return 'table'
        
        if re.search(r'^4\.[\d.]+\s+', content):
            return 'section_header'
        
        if re.search(r'(^[a-z]\.|^\d+\.)', content, re.MULTILINE):
            return 'list'
        
        if 'note:' in content_lower or 'important:' in content_lower:
            return 'note'
        
        return 'paragraph'
    
    def _has_table_content(self, content: str) -> bool:
        """Check if content contains table-like structures"""
        # Look for table indicators
        table_indicators = [
            r'\|.*\|',  # Pipe-separated columns
            r'^\s*\w+\s+\w+\s+\w+',  # Multiple columns
            r'(column|row|table)',  # Table terminology
            r'^\s*\d+\s+\w+\s+\w+',  # Numbered rows
        ]
        
        for indicator in table_indicators:
            if re.search(indicator, content, re.MULTILINE | re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_complexity_score(self, content: str) -> float:
        """Calculate complexity score for content"""
        score = 0.0
        
        # Length factor
        score += min(50.0, len(content) / 100)
        
        # Technical terms
        technical_terms = [
            'performance obligation', 'revenue recognition', 'transaction price',
            'standalone selling price', 'contract modification', 'distinct goods',
            'principal', 'agent', 'consignment', 'variable consideration'
        ]
        
        for term in technical_terms:
            if term in content.lower():
                score += 5.0
        
        # Sentence complexity
        sentences = re.split(r'[.!?]', content)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        score += min(20.0, avg_sentence_length / 2)
        
        # References and citations
        if 'ASC 606' in content:
            score += 10.0
        
        return min(100.0, score)
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key accounting terms from content"""
        key_terms = []
        
        # Define important ASC 606 terms
        important_terms = [
            'performance obligation', 'revenue recognition', 'transaction price',
            'standalone selling price', 'contract modification', 'distinct goods',
            'distinct services', 'principal', 'agent', 'consignment',
            'variable consideration', 'customer', 'contract', 'control',
            'transfer', 'satisfied', 'entity', 'promised goods',
            'promised services', 'output method', 'input method'
        ]
        
        content_lower = content.lower()
        for term in important_terms:
            if term in content_lower:
                key_terms.append(term)
        
        # Remove duplicates and sort
        key_terms = sorted(list(set(key_terms)))
        
        return key_terms[:10]  # Return top 10 key terms
