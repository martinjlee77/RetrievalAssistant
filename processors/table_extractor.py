import camelot
import tabula
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
import io
import tempfile
import os

class TableExtractor:
    """Specialized table extraction using Camelot and Tabula-py"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_tables_from_pdf(self, pdf_path: str, table_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tables using specialized tools"""
        extracted_tables = []
        
        for region in table_regions:
            page_num = region['page_number']
            bbox = region['bbox']
            
            # Try Camelot first (better for born-digital PDFs)
            camelot_table = self._extract_with_camelot(pdf_path, page_num, bbox)
            if camelot_table:
                extracted_tables.append(camelot_table)
                continue
            
            # Fallback to Tabula
            tabula_table = self._extract_with_tabula(pdf_path, page_num, bbox)
            if tabula_table:
                extracted_tables.append(tabula_table)
        
        return extracted_tables
    
    def _extract_with_camelot(self, pdf_path: str, page_num: int, bbox: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Extract table using Camelot"""
        try:
            # Camelot parameters for better extraction
            camelot_kwargs = {
                'pages': str(page_num),
                'flavor': 'lattice',  # Try lattice first for tables with clear borders
                'line_scale': 40,
                'copy_text': ['v'],
                'split_text': True
            }
            
            # If we have bbox, use table_areas parameter
            if bbox:
                # Convert bbox to Camelot format (x1,y1,x2,y2)
                x1, y1, x2, y2 = bbox
                camelot_kwargs['table_areas'] = [f"{x1},{y1},{x2},{y2}"]
            
            # Try lattice method first
            tables = camelot.read_pdf(pdf_path, **camelot_kwargs)
            
            # If lattice fails, try stream method
            if not tables or len(tables) == 0:
                camelot_kwargs['flavor'] = 'stream'
                camelot_kwargs.pop('line_scale', None)  # Not applicable for stream
                tables = camelot.read_pdf(pdf_path, **camelot_kwargs)
            
            if tables and len(tables) > 0:
                table = tables[0]  # Take first table
                
                # Convert to structured format
                df = table.df
                
                # Clean the dataframe
                df = self._clean_dataframe(df)
                
                table_data = {
                    'data': df.to_dict('records'),
                    'headers': df.columns.tolist(),
                    'rows': len(df),
                    'columns': len(df.columns),
                    'page': page_num,
                    'bbox': bbox,
                    'extraction_method': 'camelot',
                    'accuracy': table.accuracy if hasattr(table, 'accuracy') else 0.0,
                    'quality_score': self._calculate_table_quality(df),
                    'caption': None,  # Will be filled from layout analysis
                    'table_type': self._classify_table_type(df)
                }
                
                return table_data
                
        except Exception as e:
            self.logger.warning(f"Camelot extraction failed for page {page_num}: {str(e)}")
            return None
    
    def _extract_with_tabula(self, pdf_path: str, page_num: int, bbox: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Extract table using Tabula-py"""
        try:
            # Tabula parameters
            tabula_kwargs = {
                'pages': page_num,
                'multiple_tables': True,
                'pandas_options': {'header': 0}
            }
            
            # If we have bbox, use area parameter
            if bbox:
                # Convert bbox to Tabula format (top,left,bottom,right)
                x1, y1, x2, y2 = bbox
                tabula_kwargs['area'] = [y1, x1, y2, x2]
            
            # Extract tables
            tables = tabula.read_pdf(pdf_path, **tabula_kwargs)
            
            if tables and len(tables) > 0:
                df = tables[0]  # Take first table
                
                # Clean the dataframe
                df = self._clean_dataframe(df)
                
                table_data = {
                    'data': df.to_dict('records'),
                    'headers': df.columns.tolist(),
                    'rows': len(df),
                    'columns': len(df.columns),
                    'page': page_num,
                    'bbox': bbox,
                    'extraction_method': 'tabula',
                    'accuracy': 0.0,  # Tabula doesn't provide accuracy
                    'quality_score': self._calculate_table_quality(df),
                    'caption': None,
                    'table_type': self._classify_table_type(df)
                }
                
                return table_data
                
        except Exception as e:
            self.logger.warning(f"Tabula extraction failed for page {page_num}: {str(e)}")
            return None
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean extracted dataframe"""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Replace NaN with empty string
        df = df.fillna('')
        
        # Clean whitespace
        df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
        
        # Remove rows that are mostly empty
        df = df[df.astype(str).ne('').sum(axis=1) > len(df.columns) * 0.3]
        
        return df
    
    def _calculate_table_quality(self, df: pd.DataFrame) -> float:
        """Calculate quality score for extracted table"""
        if df.empty:
            return 0.0
        
        score = 0.0
        
        # Check for reasonable dimensions
        if 2 <= len(df) <= 50 and 2 <= len(df.columns) <= 10:
            score += 0.3
        
        # Check for non-empty cells
        total_cells = len(df) * len(df.columns)
        non_empty_cells = df.astype(str).ne('').sum().sum()
        if total_cells > 0:
            fill_rate = non_empty_cells / total_cells
            score += fill_rate * 0.4
        
        # Check for consistent data types in columns
        for col in df.columns:
            if df[col].dtype in ['object', 'string']:
                # Check if column has mostly numeric data
                numeric_count = df[col].apply(lambda x: str(x).replace('.', '').replace('-', '').isdigit()).sum()
                if numeric_count / len(df) > 0.7:
                    score += 0.1
        
        # Check for header row
        if len(df.columns) > 0 and any(str(col).strip() for col in df.columns):
            score += 0.2
        
        return min(1.0, score)
    
    def _classify_table_type(self, df: pd.DataFrame) -> str:
        """Classify table type based on content"""
        if df.empty:
            return 'empty'
        
        # Check column headers for patterns
        headers = [str(col).lower() for col in df.columns]
        
        # Financial/accounting table
        if any(keyword in ' '.join(headers) for keyword in ['revenue', 'cost', 'amount', 'price', 'total']):
            return 'financial'
        
        # Example/illustration table
        if any(keyword in ' '.join(headers) for keyword in ['example', 'illustration', 'scenario']):
            return 'example'
        
        # Comparison table
        if any(keyword in ' '.join(headers) for keyword in ['before', 'after', 'comparison', 'vs']):
            return 'comparison'
        
        # Reference table
        if any(keyword in ' '.join(headers) for keyword in ['reference', 'section', 'paragraph']):
            return 'reference'
        
        # Check content for patterns
        content_text = ' '.join(df.astype(str).values.flatten()).lower()
        
        # Step-by-step guidance
        if any(keyword in content_text for keyword in ['step 1', 'step 2', 'first', 'second', 'then']):
            return 'guidance'
        
        return 'general'
    
    def extract_table_captions(self, text_blocks: List[Dict[str, Any]], table_regions: List[Dict[str, Any]]) -> Dict[int, str]:
        """Match table captions with table regions"""
        captions = {}
        
        for region in table_regions:
            page_num = region['page_number']
            table_bbox = region['bbox']
            
            # Find caption blocks near this table
            page_blocks = [block for block in text_blocks if block.page_number == page_num]
            
            for block in page_blocks:
                if block.block_type == 'table_caption':
                    # Check if caption is near table
                    caption_bbox = block.bbox
                    
                    # Calculate distance between caption and table
                    distance = self._calculate_bbox_distance(caption_bbox, table_bbox)
                    
                    if distance < 100:  # Within 100 pixels
                        captions[id(region)] = block.text
                        break
        
        return captions
    
    def _calculate_bbox_distance(self, bbox1: tuple, bbox2: tuple) -> float:
        """Calculate distance between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate center points
        center1 = ((x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2)
        center2 = ((x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2)
        
        # Euclidean distance
        distance = ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5
        return distance
    
    def save_table_as_formats(self, table_data: Dict[str, Any], output_dir: str, table_index: int) -> Dict[str, str]:
        """Save table in multiple formats"""
        saved_files = {}
        
        try:
            df = pd.DataFrame(table_data['data'])
            
            # Save as CSV
            csv_path = os.path.join(output_dir, f"table_{table_index}_page_{table_data['page']}.csv")
            df.to_csv(csv_path, index=False)
            saved_files['csv'] = csv_path
            
            # Save as Excel
            excel_path = os.path.join(output_dir, f"table_{table_index}_page_{table_data['page']}.xlsx")
            df.to_excel(excel_path, index=False)
            saved_files['excel'] = excel_path
            
            # Save as JSON
            json_path = os.path.join(output_dir, f"table_{table_index}_page_{table_data['page']}.json")
            df.to_json(json_path, orient='records', indent=2)
            saved_files['json'] = json_path
            
            # Save as markdown
            markdown_path = os.path.join(output_dir, f"table_{table_index}_page_{table_data['page']}.md")
            with open(markdown_path, 'w') as f:
                f.write(df.to_markdown(index=False))
            saved_files['markdown'] = markdown_path
            
        except Exception as e:
            self.logger.error(f"Error saving table {table_index}: {str(e)}")
        
        return saved_files