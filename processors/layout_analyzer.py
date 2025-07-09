import fitz  # PyMuPDF
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

@dataclass
class TextBlock:
    """Represents a text block with layout information"""
    text: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    font_size: float
    font_name: str
    page_number: int
    block_type: str  # 'heading', 'paragraph', 'table_caption', 'footer', 'header'
    confidence: float

@dataclass
class TableRegion:
    """Represents a detected table region"""
    bbox: Tuple[float, float, float, float]
    page_number: int
    confidence: float
    caption: Optional[str] = None

class LayoutAnalyzer:
    """Advanced layout analysis for born-digital PDFs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_document_structure(self, pdf_path: str, page_range: Tuple[int, int]) -> Dict[str, Any]:
        """Analyze document structure using coordinate-based layout analysis"""
        try:
            doc = fitz.open(pdf_path)
            
            structure = {
                'text_blocks': [],
                'table_regions': [],
                'sections': [],
                'page_layouts': [],
                'metadata': {
                    'total_pages': len(doc),
                    'page_range': page_range,
                    'analysis_method': 'coordinate_based'
                }
            }
            
            start_page, end_page = page_range
            
            for page_num in range(start_page - 1, min(end_page, len(doc))):
                page = doc[page_num]
                
                # Analyze page layout
                page_layout = self._analyze_page_layout(page, page_num + 1)
                structure['page_layouts'].append(page_layout)
                
                # Extract text blocks with coordinates
                text_blocks = self._extract_text_blocks(page, page_num + 1)
                structure['text_blocks'].extend(text_blocks)
                
                # Detect table regions
                table_regions = self._detect_table_regions(page, page_num + 1)
                structure['table_regions'].extend(table_regions)
            
            # Analyze section hierarchy
            structure['sections'] = self._analyze_section_hierarchy(structure['text_blocks'])
            
            doc.close()
            return structure
            
        except Exception as e:
            self.logger.error(f"Layout analysis failed: {str(e)}")
            return self._create_empty_structure()
    
    def _analyze_page_layout(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """Analyze individual page layout"""
        rect = page.rect
        
        # Get all text with detailed formatting
        blocks = page.get_text("dict")
        
        # Analyze column structure
        columns = self._detect_columns(blocks)
        
        # Detect headers/footers
        header_region = self._detect_header_footer(blocks, rect, 'header')
        footer_region = self._detect_header_footer(blocks, rect, 'footer')
        
        return {
            'page_number': page_num,
            'width': rect.width,
            'height': rect.height,
            'columns': columns,
            'header_region': header_region,
            'footer_region': footer_region,
            'text_density': self._calculate_text_density(blocks, rect)
        }
    
    def _extract_text_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """Extract text blocks with layout information"""
        blocks = []
        
        # Get detailed text information
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    font_size = span.get("size", 12)
                    font_name = span.get("font", "")
                    
                    # Classify block type based on properties
                    block_type = self._classify_text_block(text, font_size, font_name, bbox, page_num)
                    
                    text_block = TextBlock(
                        text=text,
                        bbox=bbox,
                        font_size=font_size,
                        font_name=font_name,
                        page_number=page_num,
                        block_type=block_type,
                        confidence=self._calculate_block_confidence(text, font_size, font_name)
                    )
                    
                    blocks.append(text_block)
        
        return blocks
    
    def _detect_table_regions(self, page: fitz.Page, page_num: int) -> List[TableRegion]:
        """Detect table regions using layout analysis"""
        regions = []
        
        # Get text blocks
        blocks = page.get_text("dict")
        
        # Look for table-like patterns
        potential_tables = []
        
        for block in blocks.get("blocks", []):
            if "lines" not in block:
                continue
            
            # Check for table characteristics
            bbox = block.get("bbox", (0, 0, 0, 0))
            lines = block.get("lines", [])
            
            # Heuristics for table detection
            if self._is_table_like_block(lines, bbox):
                # Look for nearby caption
                caption = self._find_table_caption(blocks, bbox)
                
                table_region = TableRegion(
                    bbox=bbox,
                    page_number=page_num,
                    confidence=self._calculate_table_confidence(lines, bbox),
                    caption=caption
                )
                
                regions.append(table_region)
        
        return regions
    
    def _analyze_section_hierarchy(self, text_blocks: List[TextBlock]) -> List[Dict[str, Any]]:
        """Analyze section hierarchy from text blocks"""
        sections = []
        
        # Group blocks by page first
        pages = {}
        for block in text_blocks:
            page_num = block.page_number
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(block)
        
        # Analyze each page for section headers
        for page_num in sorted(pages.keys()):
            page_blocks = pages[page_num]
            
            # Look for section headers (4.1, 4.2, etc.)
            for block in page_blocks:
                if block.block_type == 'heading':
                    section_match = re.match(r'^(4\.[\d.]+)\s+(.+)$', block.text)
                    if section_match:
                        section_num = section_match.group(1)
                        section_title = section_match.group(2)
                        
                        section = {
                            'number': section_num,
                            'title': section_title,
                            'level': section_num.count('.'),
                            'page': page_num,
                            'bbox': block.bbox,
                            'font_size': block.font_size,
                            'confidence': block.confidence
                        }
                        
                        sections.append(section)
        
        return sections
    
    def _detect_columns(self, blocks: Dict) -> List[Dict[str, Any]]:
        """Detect column structure on page"""
        # Simple column detection based on text positioning
        columns = []
        
        # Analyze text x-positions to detect columns
        x_positions = []
        for block in blocks.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        x_positions.append(bbox[0])  # x0
        
        if x_positions:
            # Simple heuristic: if text starts at different x positions, likely columns
            unique_x = sorted(set(x_positions))
            if len(unique_x) > 1:
                columns = [{'x_start': x, 'type': 'text'} for x in unique_x[:2]]  # Max 2 columns
        
        return columns
    
    def _detect_header_footer(self, blocks: Dict, rect: fitz.Rect, region_type: str) -> Optional[Dict[str, Any]]:
        """Detect header or footer regions"""
        threshold = 50  # pixels from top/bottom
        
        if region_type == 'header':
            target_y = rect.height - threshold
            condition = lambda y: y > target_y
        else:  # footer
            target_y = threshold
            condition = lambda y: y < target_y
        
        region_text = []
        for block in blocks.get("blocks", []):
            if "lines" in block:
                bbox = block.get("bbox", (0, 0, 0, 0))
                if condition(bbox[1]):  # y0
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                region_text.append(text)
        
        if region_text:
            return {
                'text': ' '.join(region_text),
                'type': region_type,
                'bbox': (0, 0 if region_type == 'footer' else target_y, rect.width, threshold if region_type == 'footer' else rect.height)
            }
        
        return None
    
    def _classify_text_block(self, text: str, font_size: float, font_name: str, bbox: Tuple, page_num: int) -> str:
        """Classify text block type based on properties"""
        # Section header detection
        if re.match(r'^4\.[\d.]+\s+[A-Z]', text):
            return 'heading'
        
        # Large font size likely heading
        if font_size > 14:
            return 'heading'
        
        # Bold font likely heading
        if 'bold' in font_name.lower():
            return 'heading'
        
        # Table caption detection
        if re.match(r'^(Table|Figure|Exhibit)\s+\d+', text, re.IGNORECASE):
            return 'table_caption'
        
        # Footer detection (bottom of page)
        if bbox[1] < 50:  # Near bottom
            return 'footer'
        
        # Header detection (top of page)
        if bbox[1] > 750:  # Near top (assuming ~800px page height)
            return 'header'
        
        # Default to paragraph
        return 'paragraph'
    
    def _calculate_text_density(self, blocks: Dict, rect: fitz.Rect) -> float:
        """Calculate text density on page"""
        total_text_area = 0
        page_area = rect.width * rect.height
        
        for block in blocks.get("blocks", []):
            if "lines" in block:
                bbox = block.get("bbox", (0, 0, 0, 0))
                block_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                total_text_area += block_area
        
        return total_text_area / page_area if page_area > 0 else 0
    
    def _calculate_block_confidence(self, text: str, font_size: float, font_name: str) -> float:
        """Calculate confidence score for text block classification"""
        confidence = 0.7  # Base confidence
        
        # Increase confidence for clear patterns
        if re.match(r'^4\.[\d.]+\s+[A-Z]', text):
            confidence += 0.2
        
        # Consistent font size
        if 10 <= font_size <= 16:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _is_table_like_block(self, lines: List, bbox: Tuple) -> bool:
        """Check if block has table-like characteristics"""
        # Simple heuristics for table detection
        if len(lines) < 2:
            return False
        
        # Check for numeric content
        numeric_content = 0
        total_content = 0
        
        for line in lines:
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    total_content += 1
                    if re.search(r'\d+', text):
                        numeric_content += 1
        
        # If >50% numeric content, likely table
        if total_content > 0 and numeric_content / total_content > 0.5:
            return True
        
        return False
    
    def _find_table_caption(self, blocks: Dict, table_bbox: Tuple) -> Optional[str]:
        """Find caption for detected table"""
        # Look for captions near table
        for block in blocks.get("blocks", []):
            if "lines" not in block:
                continue
            
            block_bbox = block.get("bbox", (0, 0, 0, 0))
            
            # Check if block is near table (above or below)
            if (abs(block_bbox[1] - table_bbox[3]) < 20 or  # Below table
                abs(table_bbox[1] - block_bbox[3]) < 20):   # Above table
                
                # Extract text from block
                caption_text = ""
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            caption_text += text + " "
                
                # Check if it looks like a caption
                if re.match(r'^(Table|Figure|Exhibit)\s+\d+', caption_text, re.IGNORECASE):
                    return caption_text.strip()
        
        return None
    
    def _calculate_table_confidence(self, lines: List, bbox: Tuple) -> float:
        """Calculate confidence for table detection"""
        confidence = 0.5  # Base confidence
        
        # More lines = higher confidence
        if len(lines) > 3:
            confidence += 0.2
        
        # Consistent width suggests table
        widths = []
        for line in lines:
            line_bbox = line.get("bbox", (0, 0, 0, 0))
            widths.append(line_bbox[2] - line_bbox[0])
        
        if widths and max(widths) - min(widths) < 50:  # Consistent width
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _create_empty_structure(self) -> Dict[str, Any]:
        """Create empty structure for error cases"""
        return {
            'text_blocks': [],
            'table_regions': [],
            'sections': [],
            'page_layouts': [],
            'metadata': {
                'total_pages': 0,
                'page_range': (0, 0),
                'analysis_method': 'failed'
            }
        }