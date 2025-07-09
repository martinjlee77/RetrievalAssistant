from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
import logging

@dataclass
class StructureChunk:
    """Represents a structure-aware chunk"""
    content: str
    chunk_type: str  # 'section', 'subsection', 'paragraph', 'table', 'example'
    section_number: str
    section_title: str
    page_numbers: List[int]
    bbox: Optional[Tuple[float, float, float, float]]
    metadata: Dict[str, Any]
    confidence: float

class StructureAwareChunker:
    """Creates chunks based on document structure, not arbitrary size limits"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def create_structure_chunks(self, 
                              text_blocks: List[Any], 
                              sections: List[Dict[str, Any]], 
                              tables: List[Dict[str, Any]],
                              page_layouts: List[Dict[str, Any]]) -> List[StructureChunk]:
        """Create chunks based on document structure"""
        
        chunks = []
        
        # Sort sections by page and position
        sorted_sections = sorted(sections, key=lambda x: (x['page'], x['bbox'][1]))
        
        # Process each section
        for i, section in enumerate(sorted_sections):
            section_chunks = self._process_section(
                section, 
                text_blocks, 
                tables, 
                page_layouts,
                next_section=sorted_sections[i+1] if i+1 < len(sorted_sections) else None
            )
            chunks.extend(section_chunks)
        
        # Add orphaned content (text not belonging to any section)
        orphaned_chunks = self._process_orphaned_content(text_blocks, sections, tables)
        chunks.extend(orphaned_chunks)
        
        return chunks
    
    def _process_section(self, 
                        section: Dict[str, Any], 
                        text_blocks: List[Any], 
                        tables: List[Dict[str, Any]],
                        page_layouts: List[Dict[str, Any]],
                        next_section: Optional[Dict[str, Any]] = None) -> List[StructureChunk]:
        """Process a single section into chunks"""
        
        chunks = []
        section_number = section['number']
        section_title = section['title']
        section_page = section['page']
        section_bbox = section['bbox']
        
        # Find text blocks belonging to this section
        section_blocks = self._find_section_blocks(
            section, text_blocks, next_section
        )
        
        # Find tables belonging to this section
        section_tables = self._find_section_tables(
            section, tables, next_section
        )
        
        # Create section header chunk
        header_chunk = StructureChunk(
            content=f"{section_number} {section_title}",
            chunk_type='section_header',
            section_number=section_number,
            section_title=section_title,
            page_numbers=[section_page],
            bbox=section_bbox,
            metadata={
                'level': section['level'],
                'confidence': section['confidence'],
                'is_header': True
            },
            confidence=section['confidence']
        )
        chunks.append(header_chunk)
        
        # Process section content
        content_chunks = self._process_section_content(
            section_blocks, section_tables, section_number, section_title
        )
        chunks.extend(content_chunks)
        
        return chunks
    
    def _find_section_blocks(self, 
                           section: Dict[str, Any], 
                           text_blocks: List[Any], 
                           next_section: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Find text blocks belonging to a section"""
        
        section_blocks = []
        section_page = section['page']
        section_y = section['bbox'][1]  # y-coordinate of section header
        
        # Define section boundary
        if next_section:
            next_section_page = next_section['page']
            next_section_y = next_section['bbox'][1]
            
            if next_section_page == section_page:
                # Same page - use y-coordinate
                boundary = (section_page, next_section_y)
            else:
                # Different page - include everything until next section page
                boundary = (next_section_page, next_section_y)
        else:
            # Last section - include everything after
            boundary = (999, 0)  # Arbitrarily large page number
        
        # Find blocks within section boundary
        for block in text_blocks:
            if block.page_number < section_page:
                continue
            
            if block.page_number == section_page and block.bbox[1] <= section_y:
                continue
            
            if block.page_number > boundary[0]:
                break
            
            if block.page_number == boundary[0] and block.bbox[1] >= boundary[1]:
                break
            
            # Skip headers and footers
            if block.block_type in ['header', 'footer']:
                continue
            
            section_blocks.append(block)
        
        return section_blocks
    
    def _find_section_tables(self, 
                           section: Dict[str, Any], 
                           tables: List[Dict[str, Any]], 
                           next_section: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find tables belonging to a section"""
        
        section_tables = []
        section_page = section['page']
        
        # Define page range for section
        if next_section:
            end_page = next_section['page']
        else:
            end_page = 999  # Arbitrarily large
        
        # Find tables within section pages
        for table in tables:
            table_page = table['page']
            
            if section_page <= table_page < end_page:
                section_tables.append(table)
        
        return section_tables
    
    def _process_section_content(self, 
                               section_blocks: List[Any], 
                               section_tables: List[Dict[str, Any]], 
                               section_number: str, 
                               section_title: str) -> List[StructureChunk]:
        """Process content within a section"""
        
        chunks = []
        
        # Group blocks by type and proximity
        block_groups = self._group_blocks_by_proximity(section_blocks)
        
        # Process each group
        for group in block_groups:
            group_chunks = self._process_block_group(
                group, section_number, section_title
            )
            chunks.extend(group_chunks)
        
        # Process tables
        for table in section_tables:
            table_chunk = self._create_table_chunk(
                table, section_number, section_title
            )
            chunks.append(table_chunk)
        
        return chunks
    
    def _group_blocks_by_proximity(self, blocks: List[Any]) -> List[List[Any]]:
        """Group text blocks by proximity and type"""
        
        if not blocks:
            return []
        
        groups = []
        current_group = [blocks[0]]
        
        for i in range(1, len(blocks)):
            prev_block = blocks[i-1]
            curr_block = blocks[i]
            
            # Check if blocks should be in same group
            if self._should_group_blocks(prev_block, curr_block):
                current_group.append(curr_block)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [curr_block]
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _should_group_blocks(self, block1: Any, block2: Any) -> bool:
        """Determine if two blocks should be grouped together"""
        
        # Same page and close proximity
        if block1.page_number == block2.page_number:
            y_distance = abs(block1.bbox[1] - block2.bbox[1])
            if y_distance < 50:  # Within 50 pixels
                return True
        
        # Consecutive pages and similar x-position
        if abs(block1.page_number - block2.page_number) == 1:
            x_distance = abs(block1.bbox[0] - block2.bbox[0])
            if x_distance < 50:  # Similar x-position
                return True
        
        # Same block type
        if block1.block_type == block2.block_type and block1.block_type == 'paragraph':
            return True
        
        return False
    
    def _process_block_group(self, 
                           group: List[Any], 
                           section_number: str, 
                           section_title: str) -> List[StructureChunk]:
        """Process a group of blocks into chunks"""
        
        chunks = []
        
        # Combine text from group
        combined_text = ""
        page_numbers = []
        bbox_list = []
        
        for block in group:
            combined_text += block.text + "\n"
            if block.page_number not in page_numbers:
                page_numbers.append(block.page_number)
            bbox_list.append(block.bbox)
        
        # Determine chunk type
        chunk_type = self._determine_chunk_type(group)
        
        # Calculate combined bbox
        combined_bbox = self._calculate_combined_bbox(bbox_list)
        
        # Create chunk
        chunk = StructureChunk(
            content=combined_text.strip(),
            chunk_type=chunk_type,
            section_number=section_number,
            section_title=section_title,
            page_numbers=sorted(page_numbers),
            bbox=combined_bbox,
            metadata={
                'block_count': len(group),
                'word_count': len(combined_text.split()),
                'char_count': len(combined_text),
                'font_sizes': [block.font_size for block in group],
                'font_names': list(set(block.font_name for block in group))
            },
            confidence=sum(block.confidence for block in group) / len(group)
        )
        
        chunks.append(chunk)
        
        return chunks
    
    def _determine_chunk_type(self, group: List[Any]) -> str:
        """Determine the type of chunk from a group of blocks"""
        
        block_types = [block.block_type for block in group]
        
        # Most common type
        type_counts = {}
        for block_type in block_types:
            type_counts[block_type] = type_counts.get(block_type, 0) + 1
        
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0]
        
        # Check for specific patterns
        combined_text = " ".join(block.text for block in group)
        
        if re.search(r'example\s+\d+', combined_text, re.IGNORECASE):
            return 'example'
        
        if re.search(r'illustration\s+\d+', combined_text, re.IGNORECASE):
            return 'illustration'
        
        if most_common_type == 'heading':
            return 'subsection'
        
        return 'content'
    
    def _calculate_combined_bbox(self, bbox_list: List[Tuple]) -> Tuple[float, float, float, float]:
        """Calculate combined bounding box from list of bboxes"""
        
        if not bbox_list:
            return (0, 0, 0, 0)
        
        min_x = min(bbox[0] for bbox in bbox_list)
        min_y = min(bbox[1] for bbox in bbox_list)
        max_x = max(bbox[2] for bbox in bbox_list)
        max_y = max(bbox[3] for bbox in bbox_list)
        
        return (min_x, min_y, max_x, max_y)
    
    def _create_table_chunk(self, 
                          table: Dict[str, Any], 
                          section_number: str, 
                          section_title: str) -> StructureChunk:
        """Create a chunk for a table"""
        
        # Convert table to text representation
        table_text = self._table_to_text(table)
        
        chunk = StructureChunk(
            content=table_text,
            chunk_type='table',
            section_number=section_number,
            section_title=section_title,
            page_numbers=[table['page']],
            bbox=table.get('bbox'),
            metadata={
                'table_type': table.get('table_type', 'unknown'),
                'rows': table.get('rows', 0),
                'columns': table.get('columns', 0),
                'extraction_method': table.get('extraction_method', 'unknown'),
                'accuracy': table.get('accuracy', 0.0),
                'quality_score': table.get('quality_score', 0.0),
                'caption': table.get('caption', ''),
                'original_data': table.get('data', [])
            },
            confidence=table.get('quality_score', 0.5)
        )
        
        return chunk
    
    def _table_to_text(self, table: Dict[str, Any]) -> str:
        """Convert table data to text representation"""
        
        text_parts = []
        
        # Add caption if available
        if table.get('caption'):
            text_parts.append(f"Caption: {table['caption']}")
        
        # Add table data
        data = table.get('data', [])
        headers = table.get('headers', [])
        
        if headers:
            text_parts.append("Headers: " + " | ".join(str(h) for h in headers))
        
        if data:
            text_parts.append("Data:")
            for i, row in enumerate(data[:10]):  # Limit to first 10 rows
                row_text = " | ".join(str(cell) for cell in row.values() if cell)
                if row_text.strip():
                    text_parts.append(f"Row {i+1}: {row_text}")
        
        # Add metadata
        text_parts.append(f"Table Type: {table.get('table_type', 'unknown')}")
        text_parts.append(f"Dimensions: {table.get('rows', 0)} rows × {table.get('columns', 0)} columns")
        
        return "\n".join(text_parts)
    
    def _process_orphaned_content(self, 
                                text_blocks: List[Any], 
                                sections: List[Dict[str, Any]], 
                                tables: List[Dict[str, Any]]) -> List[StructureChunk]:
        """Process content that doesn't belong to any section"""
        
        chunks = []
        
        # Find blocks not covered by any section
        covered_blocks = set()
        
        for section in sections:
            section_blocks = self._find_section_blocks(section, text_blocks)
            for block in section_blocks:
                covered_blocks.add(id(block))
        
        orphaned_blocks = [block for block in text_blocks if id(block) not in covered_blocks]
        
        if orphaned_blocks:
            # Group orphaned blocks
            orphaned_groups = self._group_blocks_by_proximity(orphaned_blocks)
            
            for group in orphaned_groups:
                orphaned_chunks = self._process_block_group(
                    group, "unknown", "Orphaned Content"
                )
                chunks.extend(orphaned_chunks)
        
        return chunks
    
    def validate_chunks(self, chunks: List[StructureChunk]) -> Dict[str, Any]:
        """Validate the quality of created chunks"""
        
        validation = {
            'total_chunks': len(chunks),
            'chunk_types': {},
            'average_confidence': 0.0,
            'page_coverage': set(),
            'sections_covered': set(),
            'issues': []
        }
        
        if not chunks:
            validation['issues'].append("No chunks created")
            return validation
        
        # Analyze chunk types
        for chunk in chunks:
            chunk_type = chunk.chunk_type
            validation['chunk_types'][chunk_type] = validation['chunk_types'].get(chunk_type, 0) + 1
            
            # Track coverage
            validation['page_coverage'].update(chunk.page_numbers)
            validation['sections_covered'].add(chunk.section_number)
        
        # Calculate average confidence
        total_confidence = sum(chunk.confidence for chunk in chunks)
        validation['average_confidence'] = total_confidence / len(chunks)
        
        # Check for issues
        if validation['average_confidence'] < 0.7:
            validation['issues'].append("Low average confidence")
        
        if len(validation['chunk_types']) < 2:
            validation['issues'].append("Limited chunk type diversity")
        
        # Convert sets to lists for JSON serialization
        validation['page_coverage'] = sorted(list(validation['page_coverage']))
        validation['sections_covered'] = sorted(list(validation['sections_covered']))
        
        return validation