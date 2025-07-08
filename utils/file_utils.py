import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

class FileUtils:
    """Utility functions for file operations"""
    
    @staticmethod
    def get_file_info(uploaded_file) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            # Get file size
            file_size = len(uploaded_file.read())
            uploaded_file.seek(0)  # Reset file pointer
            
            # Get file type
            file_type = uploaded_file.type if hasattr(uploaded_file, 'type') else 'unknown'
            
            # Get file name
            file_name = uploaded_file.name if hasattr(uploaded_file, 'name') else 'unknown'
            
            # Calculate file hash
            file_hash = FileUtils._calculate_file_hash(uploaded_file)
            
            return {
                'name': file_name,
                'size_bytes': file_size,
                'size_mb': file_size / (1024 * 1024),
                'type': file_type,
                'hash': file_hash,
                'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_pdf': file_type == 'application/pdf' or file_name.lower().endswith('.pdf')
            }
            
        except Exception as e:
            return {
                'name': 'unknown',
                'size_bytes': 0,
                'size_mb': 0.0,
                'type': 'unknown',
                'hash': 'unknown',
                'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_pdf': False,
                'error': str(e)
            }
    
    @staticmethod
    def _calculate_file_hash(uploaded_file) -> str:
        """Calculate MD5 hash of file"""
        try:
            content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            return hashlib.md5(content).hexdigest()
        except Exception:
            return 'unknown'
    
    @staticmethod
    def validate_pdf_file(uploaded_file) -> Dict[str, Any]:
        """Validate PDF file"""
        validation_result = {
            'is_valid': False,
            'file_type': 'unknown',
            'size_mb': 0.0,
            'issues': []
        }
        
        try:
            # Check file type
            file_type = uploaded_file.type if hasattr(uploaded_file, 'type') else 'unknown'
            file_name = uploaded_file.name if hasattr(uploaded_file, 'name') else 'unknown'
            
            validation_result['file_type'] = file_type
            
            # Check if it's a PDF
            if file_type != 'application/pdf' and not file_name.lower().endswith('.pdf'):
                validation_result['issues'].append('File is not a PDF')
                return validation_result
            
            # Check file size
            file_size = len(uploaded_file.read())
            uploaded_file.seek(0)  # Reset file pointer
            
            size_mb = file_size / (1024 * 1024)
            validation_result['size_mb'] = size_mb
            
            # Check size limits
            if size_mb > 100:  # 100MB limit
                validation_result['issues'].append('File size exceeds 100MB limit')
                return validation_result
            
            if size_mb < 0.1:  # 100KB minimum
                validation_result['issues'].append('File size too small (less than 100KB)')
                return validation_result
            
            # Check PDF header
            file_content = uploaded_file.read(10)
            uploaded_file.seek(0)  # Reset file pointer
            
            if not file_content.startswith(b'%PDF-'):
                validation_result['issues'].append('Invalid PDF header')
                return validation_result
            
            validation_result['is_valid'] = True
            return validation_result
            
        except Exception as e:
            validation_result['issues'].append(f'Validation error: {str(e)}')
            return validation_result
    
    @staticmethod
    def save_temp_file(uploaded_file, temp_dir: str = "/tmp") -> Optional[str]:
        """Save uploaded file to temporary location"""
        try:
            # Create temp directory if it doesn't exist
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"temp_pdf_{timestamp}.pdf"
            temp_path = os.path.join(temp_dir, filename)
            
            # Save file
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.read())
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            return temp_path
            
        except Exception as e:
            print(f"Error saving temp file: {str(e)}")
            return None
    
    @staticmethod
    def cleanup_temp_file(file_path: str) -> bool:
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def create_output_directory(base_dir: str = "output") -> str:
        """Create output directory for results"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(base_dir, f"asc606_processing_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            return output_dir
        except Exception as e:
            print(f"Error creating output directory: {str(e)}")
            return base_dir
    
    @staticmethod
    def save_processing_results(results: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """Save processing results to files"""
        saved_files = {}
        
        try:
            # Save main results
            import json
            
            # Save full results
            results_file = os.path.join(output_dir, 'processing_results.json')
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            saved_files['results'] = results_file
            
            # Save chunks separately
            if 'chunks' in results:
                chunks_file = os.path.join(output_dir, 'chunks.json')
                with open(chunks_file, 'w') as f:
                    json.dump(results['chunks'], f, indent=2, default=str)
                saved_files['chunks'] = chunks_file
            
            # Save quality report
            if 'quality_results' in results:
                quality_file = os.path.join(output_dir, 'quality_report.json')
                with open(quality_file, 'w') as f:
                    json.dump(results['quality_results'], f, indent=2, default=str)
                saved_files['quality'] = quality_file
            
            # Save text content
            if 'chapter_content' in results and 'text' in results['chapter_content']:
                text_file = os.path.join(output_dir, 'extracted_text.txt')
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(results['chapter_content']['text'])
                saved_files['text'] = text_file
            
            return saved_files
            
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            return saved_files
    
    @staticmethod
    def get_file_stats(file_path: str) -> Dict[str, Any]:
        """Get file statistics"""
        try:
            if not os.path.exists(file_path):
                return {'exists': False}
            
            stat = os.stat(file_path)
            
            return {
                'exists': True,
                'size_bytes': stat.st_size,
                'size_mb': stat.st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK)
            }
            
        except Exception as e:
            return {'exists': False, 'error': str(e)}
