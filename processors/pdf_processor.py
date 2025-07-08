import io
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.cleaners.core import clean
    from unstructured.chunking.title import chunk_by_title
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

class PDFProcessor:
    """Advanced PDF processor for ASC 606 accounting documents"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(level=logging.INFO)
        
    def extract_chapter_4(self, uploaded_file) -> Dict[str, Any]:
        """Extract Chapter 4 content from the uploaded PDF"""
        try:
            # Convert uploaded file to bytes
            file_bytes = uploaded_file.read()
            
            # Reset file pointer for subsequent reads
            uploaded_file.seek(0)
            
            # Try different extraction methods
            if UNSTRUCTURED_AVAILABLE:
                return self._extract_with_unstructured(file_bytes)
            elif PDFPLUMBER_AVAILABLE:
                return self._extract_with_pdfplumber(file_bytes)
            elif PYPDF2_AVAILABLE:
                return self._extract_with_pypdf2(file_bytes)
            else:
                raise ImportError("No PDF processing libraries available")
                
        except Exception as e:
            self.logger.error(f"Error extracting Chapter 4: {str(e)}")
            return self._create_fallback_content()
    
    def _extract_with_unstructured(self, file_bytes: bytes) -> Dict[str, Any]:
        """Extract using Unstructured.io for high-quality structure preservation"""
        try:
            # Save bytes to temporary file for unstructured
            with io.BytesIO(file_bytes) as temp_file:
                elements = partition_pdf(
                    file=temp_file,
                    strategy="hi_res",
                    include_page_breaks=True,
                    infer_table_structure=True,
                    extract_images=False,
                    model_name="yolox"
                )
            
            # Filter elements for Chapter 4 (pages 63-83)
            chapter_4_elements = self._filter_chapter_4_elements(elements)
            
            # Process elements into structured content
            return self._process_unstructured_elements(chapter_4_elements)
            
        except Exception as e:
            self.logger.error(f"Unstructured extraction failed: {str(e)}")
            raise
    
    def _extract_with_pdfplumber(self, file_bytes: bytes) -> Dict[str, Any]:
        """Extract using pdfplumber for better table handling"""
        try:
            with io.BytesIO(file_bytes) as temp_file:
                with pdfplumber.open(temp_file) as pdf:
                    # Extract pages 63-83 (0-indexed: 62-82)
                    chapter_pages = pdf.pages[62:83]
                    
                    content = {
                        'pages': [],
                        'text': '',
                        'tables': [],
                        'metadata': {
                            'total_pages': len(chapter_pages),
                            'extraction_method': 'pdfplumber',
                            'page_range': '63-83'
                        }
                    }
                    
                    for i, page in enumerate(chapter_pages):
                        page_num = i + 63  # Actual page number
                        
                        # Extract text
                        page_text = page.extract_text() or ""
                        content['text'] += f"\n--- Page {page_num} ---\n{page_text}"
                        
                        # Extract tables
                        tables = page.extract_tables()
                        for table in tables:
                            if table:
                                content['tables'].append({
                                    'page': page_num,
                                    'data': table,
                                    'rows': len(table),
                                    'columns': len(table[0]) if table else 0
                                })
                        
                        content['pages'].append({
                            'page_number': page_num,
                            'text': page_text,
                            'tables': len(tables)
                        })
                    
                    return content
                    
        except Exception as e:
            self.logger.error(f"PDFPlumber extraction failed: {str(e)}")
            raise
    
    def _extract_with_pypdf2(self, file_bytes: bytes) -> Dict[str, Any]:
        """Fallback extraction using PyPDF2"""
        try:
            with io.BytesIO(file_bytes) as temp_file:
                pdf_reader = PyPDF2.PdfReader(temp_file)
                
                # Extract pages 63-83 (0-indexed: 62-82)
                chapter_pages = pdf_reader.pages[62:83]
                
                content = {
                    'pages': [],
                    'text': '',
                    'tables': [],
                    'metadata': {
                        'total_pages': len(chapter_pages),
                        'extraction_method': 'pypdf2',
                        'page_range': '63-83'
                    }
                }
                
                for i, page in enumerate(chapter_pages):
                    page_num = i + 63
                    page_text = page.extract_text()
                    
                    content['text'] += f"\n--- Page {page_num} ---\n{page_text}"
                    content['pages'].append({
                        'page_number': page_num,
                        'text': page_text,
                        'tables': 0
                    })
                
                return content
                
        except Exception as e:
            self.logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise
    
    def _filter_chapter_4_elements(self, elements) -> List[Any]:
        """Filter elements for Chapter 4 content"""
        chapter_4_elements = []
        in_chapter_4 = False
        
        for element in elements:
            # Check if we're entering Chapter 4
            if hasattr(element, 'text') and element.text:
                text = element.text.strip()
                
                # Start of Chapter 4
                if re.search(r'4\s+Identify\s+the\s+performance\s+obligations', text, re.IGNORECASE):
                    in_chapter_4 = True
                    chapter_4_elements.append(element)
                    continue
                
                # End of Chapter 4 (start of Chapter 5)
                if re.search(r'5\s+Determine\s+the\s+transaction\s+price', text, re.IGNORECASE):
                    in_chapter_4 = False
                    break
                
                # Page-based filtering (pages 63-83)
                if hasattr(element, 'metadata') and element.metadata:
                    page_num = element.metadata.get('page_number', 0)
                    if 63 <= page_num <= 83:
                        chapter_4_elements.append(element)
                        continue
                
                # Include element if we're in Chapter 4
                if in_chapter_4:
                    chapter_4_elements.append(element)
        
        return chapter_4_elements
    
    def _process_unstructured_elements(self, elements) -> Dict[str, Any]:
        """Process unstructured elements into structured content"""
        content = {
            'pages': [],
            'text': '',
            'tables': [],
            'metadata': {
                'total_pages': 21,
                'extraction_method': 'unstructured',
                'page_range': '63-83'
            }
        }
        
        current_page = None
        page_content = []
        
        for element in elements:
            # Get page number
            page_num = getattr(element.metadata, 'page_number', 0) if hasattr(element, 'metadata') else 0
            
            # Process page break
            if current_page is not None and page_num != current_page:
                content['pages'].append({
                    'page_number': current_page,
                    'text': '\n'.join(page_content),
                    'tables': 0
                })
                page_content = []
            
            current_page = page_num
            
            # Process element based on type
            if hasattr(element, 'text') and element.text:
                text = clean(element.text, bullets=True, extra_whitespace=True)
                content['text'] += text + '\n'
                page_content.append(text)
                
                # Check for table element
                if hasattr(element, 'category') and element.category == 'Table':
                    content['tables'].append({
                        'page': page_num,
                        'text': text,
                        'data': None,
                        'rows': text.count('\n') + 1,
                        'columns': 0
                    })
        
        # Add last page
        if current_page and page_content:
            content['pages'].append({
                'page_number': current_page,
                'text': '\n'.join(page_content),
                'tables': 0
            })
        
        return content
    
    def _create_fallback_content(self) -> Dict[str, Any]:
        """Create fallback content when extraction fails"""
        return {
            'pages': [],
            'text': '',
            'tables': [],
            'metadata': {
                'total_pages': 21,
                'extraction_method': 'fallback',
                'page_range': '63-83',
                'error': 'PDF extraction failed - using fallback content'
            }
        }
    
    def analyze_structure(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document structure and hierarchy"""
        text = content.get('text', '')
        
        # Extract sections using regex patterns
        sections = self._extract_sections(text)
        
        # Analyze content distribution
        content_distribution = self._analyze_content_distribution(text)
        
        # Create page mapping
        page_mapping = self._create_page_mapping(content.get('pages', []))
        
        return {
            'sections': sections,
            'content_distribution': content_distribution,
            'page_mapping': page_mapping,
            'total_sections': len(sections),
            'hierarchy_depth': max([s['level'] for s in sections]) if sections else 0
        }
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract section hierarchy from text"""
        sections = []
        
        # Pattern for section headers (4.1, 4.2, 4.1.1, etc.)
        section_pattern = r'^(4\.[\d.]+)\s+(.+?)(?=\n|$)'
        
        for match in re.finditer(section_pattern, text, re.MULTILINE):
            section_num = match.group(1)
            section_title = match.group(2).strip()
            
            # Determine level based on number of dots
            level = section_num.count('.') + 1
            
            sections.append({
                'number': section_num,
                'title': section_title,
                'level': level,
                'full_title': f"{section_num} {section_title}"
            })
        
        return sections
    
    def _analyze_content_distribution(self, text: str) -> List[Dict[str, Any]]:
        """Analyze content type distribution"""
        return [
            {'type': 'Paragraphs', 'count': len(text.split('\n\n'))},
            {'type': 'Examples', 'count': text.lower().count('example')},
            {'type': 'References', 'count': text.count('ASC 606')},
            {'type': 'Numbered Lists', 'count': len(re.findall(r'^\d+\.', text, re.MULTILINE))},
            {'type': 'Bullet Points', 'count': text.count('•') + text.count('*')}
        ]
    
    def _create_page_mapping(self, pages: List[Dict]) -> List[Dict[str, Any]]:
        """Create page mapping information"""
        return [
            {
                'page': page['page_number'],
                'word_count': len(page['text'].split()),
                'has_tables': page.get('tables', 0) > 0,
                'section_starts': self._count_section_starts(page['text'])
            }
            for page in pages
        ]
    
    def _count_section_starts(self, text: str) -> int:
        """Count section starts in text"""
        return len(re.findall(r'^4\.[\d.]+\s+', text, re.MULTILINE))
    
    def extract_tables(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and process tables from content"""
        tables = []
        
        # Process existing tables from content
        for table in content.get('tables', []):
            processed_table = self._process_table(table)
            if processed_table:
                tables.append(processed_table)
        
        # Look for table patterns in text
        text_tables = self._extract_tables_from_text(content.get('text', ''))
        tables.extend(text_tables)
        
        return tables
    
    def _process_table(self, table: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single table"""
        try:
            return {
                'title': f"Table on page {table.get('page', 0)}",
                'page': table.get('page', 0),
                'rows': table.get('rows', 0),
                'columns': table.get('columns', 0),
                'content': table.get('data', []),
                'quality_score': self._calculate_table_quality(table),
                'type': 'extracted'
            }
        except Exception as e:
            self.logger.error(f"Error processing table: {str(e)}")
            return None
    
    def _extract_tables_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract table-like structures from text"""
        tables = []
        
        # Look for structured data patterns
        lines = text.split('\n')
        potential_tables = []
        current_table = []
        
        for line in lines:
            # Check if line looks like a table row (multiple columns separated by spaces/tabs)
            if self._is_table_row(line):
                current_table.append(line)
            else:
                if len(current_table) > 2:  # Minimum table size
                    potential_tables.append(current_table)
                current_table = []
        
        # Add final table if exists
        if len(current_table) > 2:
            potential_tables.append(current_table)
        
        # Process potential tables
        for i, table_lines in enumerate(potential_tables):
            tables.append({
                'title': f"Text Table {i+1}",
                'page': 0,  # Unknown page
                'rows': len(table_lines),
                'columns': self._estimate_columns(table_lines),
                'content': table_lines,
                'quality_score': 70.0,  # Estimated
                'type': 'text_extracted'
            })
        
        return tables
    
    def _is_table_row(self, line: str) -> bool:
        """Check if a line looks like a table row"""
        # Simple heuristic: multiple words separated by significant whitespace
        words = line.split()
        if len(words) < 2:
            return False
        
        # Check for consistent spacing patterns
        spaces = re.findall(r'\s+', line)
        return len(spaces) >= 2 and any(len(space) > 3 for space in spaces)
    
    def _estimate_columns(self, table_lines: List[str]) -> int:
        """Estimate number of columns in a text table"""
        if not table_lines:
            return 0
        
        # Use the first line to estimate columns
        first_line = table_lines[0]
        return len(re.split(r'\s{2,}', first_line))
    
    def _calculate_table_quality(self, table: Dict[str, Any]) -> float:
        """Calculate table extraction quality score"""
        score = 100.0
        
        # Penalize for missing data
        if not table.get('data'):
            score -= 50.0
        
        # Penalize for irregular structure
        if table.get('rows', 0) == 0:
            score -= 30.0
        
        if table.get('columns', 0) == 0:
            score -= 20.0
        
        return max(0.0, score)
    
    def extract_examples(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract example scenarios from content"""
        examples = []
        text = content.get('text', '')
        
        # Look for example patterns
        example_patterns = [
            r'Example\s+(\d+(?:\.\d+)?)\s*[:\-–]\s*(.+?)(?=Example|\n\n|$)',
            r'Illustration\s+(\d+(?:\.\d+)?)\s*[:\-–]\s*(.+?)(?=Illustration|\n\n|$)',
            r'Case\s+Study\s+(\d+(?:\.\d+)?)\s*[:\-–]\s*(.+?)(?=Case Study|\n\n|$)'
        ]
        
        for pattern in example_patterns:
            for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
                example_num = match.group(1)
                example_content = match.group(2).strip()
                
                examples.append({
                    'number': example_num,
                    'title': f"Example {example_num}",
                    'content': example_content,
                    'type': 'example',
                    'page': self._estimate_page(match.start(), text),
                    'completeness': self._calculate_example_completeness(example_content)
                })
        
        return examples
    
    def _estimate_page(self, position: int, text: str) -> int:
        """Estimate page number based on text position"""
        # Simple heuristic: count page markers before position
        text_before = text[:position]
        page_markers = re.findall(r'--- Page (\d+) ---', text_before)
        
        if page_markers:
            return int(page_markers[-1])
        
        # Fallback: estimate based on text length
        chars_per_page = 3000  # Rough estimate
        return max(63, min(83, 63 + position // chars_per_page))
    
    def _calculate_example_completeness(self, content: str) -> float:
        """Calculate example completeness score"""
        score = 0.0
        
        # Check for key components
        if len(content) > 100:
            score += 30.0
        
        if re.search(r'(facts|scenario|situation)', content, re.IGNORECASE):
            score += 20.0
        
        if re.search(r'(analysis|conclusion|result)', content, re.IGNORECASE):
            score += 20.0
        
        if re.search(r'(performance obligation|revenue recognition)', content, re.IGNORECASE):
            score += 30.0
        
        return min(100.0, score)
