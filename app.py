import streamlit as st
import os
import json
import time
from pathlib import Path
import pandas as pd
from datetime import datetime

from processors.advanced_pdf_processor import AdvancedPDFProcessor
from processors.chunk_processor import ChunkProcessor
from processors.quality_validator import QualityValidator
from utils.file_utils import FileUtils
from utils.metadata_enricher import MetadataEnricher
from config.settings import Settings

# Configure page
st.set_page_config(
    page_title="ASC 606 PDF Processing PoC",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'results' not in st.session_state:
    st.session_state.results = None
if 'checkpoints' not in st.session_state:
    st.session_state.checkpoints = {}

class ASC606ProcessingApp:
    def __init__(self):
        self.settings = Settings()
        self.pdf_processor = AdvancedPDFProcessor()
        self.chunk_processor = ChunkProcessor()
        self.quality_validator = QualityValidator()
        self.file_utils = FileUtils()
        self.metadata_enricher = MetadataEnricher()
        
    def run(self):
        st.title("🔍 ASC 606 PDF Processing Proof of Concept")
        st.markdown("**Validating PDF processing feasibility for EY's Chapter 4: Performance Obligations**")
        
        # Sidebar configuration
        self.render_sidebar()
        
        # Main content area
        if not st.session_state.processing_complete:
            self.render_processing_interface()
        else:
            self.render_results_interface()
    
    def render_sidebar(self):
        st.sidebar.header("📋 Configuration")
        
        # Processing options
        st.sidebar.subheader("Processing Options")
        
        self.chunk_size = st.sidebar.slider(
            "Chunk Size (tokens)", 
            min_value=200, 
            max_value=2000, 
            value=800, 
            step=100
        )
        
        self.chunk_overlap = st.sidebar.slider(
            "Chunk Overlap (%)", 
            min_value=10, 
            max_value=30, 
            value=20, 
            step=5
        )
        
        self.quality_threshold = st.sidebar.slider(
            "Quality Threshold (%)", 
            min_value=70, 
            max_value=95, 
            value=85, 
            step=5
        )
        
        # Target pages
        st.sidebar.subheader("Target Section")
        st.sidebar.info("**Chapter 4: Performance Obligations**\nPages 63-83 from EY ASC 606 Guide")
        
        # Processing status
        if st.session_state.checkpoints:
            st.sidebar.subheader("🔄 Processing Status")
            for checkpoint, status in st.session_state.checkpoints.items():
                if status == "completed":
                    st.sidebar.success(f"✅ {checkpoint}")
                elif status == "in_progress":
                    st.sidebar.info(f"⏳ {checkpoint}")
                elif status == "failed":
                    st.sidebar.error(f"❌ {checkpoint}")
    
    def render_processing_interface(self):
        st.header("🚀 Start Processing")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload EY ASC 606 PDF",
            type=['pdf'],
            help="Upload the EY ASC 606 comprehensive guide PDF"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_info = self.file_utils.get_file_info(uploaded_file)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{file_info['size_mb']:.2f} MB")
            with col2:
                st.metric("File Type", file_info['type'])
            with col3:
                st.metric("Upload Time", file_info['upload_time'])
            
            # Processing button
            if st.button("🔄 Start Processing Chapter 4", type="primary"):
                self.process_document(uploaded_file)
        
        # Show sample expected output
        self.show_expected_output()
    
    def process_document(self, uploaded_file):
        """Advanced processing pipeline using structure-aware approach"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Record start time
            start_time = time.time()
            
            # Step 1: Advanced PDF Processing
            status_text.text("Step 1/3: Advanced PDF processing with layout analysis...")
            st.session_state.checkpoints["Advanced Processing"] = "in_progress"
            
            # Use the new advanced processor
            processing_result = self.pdf_processor.extract_chapter_4(uploaded_file)
            
            if not processing_result.get('success', False):
                st.error(f"Processing failed: {processing_result.get('error', 'Unknown error')}")
                return
            
            st.session_state.checkpoints["Advanced Processing"] = "completed"
            progress_bar.progress(50)
            
            # Step 2: Extract structured data
            status_text.text("Step 2/3: Extracting structured data...")
            st.session_state.checkpoints["Data Extraction"] = "in_progress"
            
            chapter_content = processing_result.get('chapter_content', {})
            quality_metrics = processing_result.get('quality_metrics', {})
            processing_report = processing_result.get('processing_report', {})
            
            st.session_state.checkpoints["Data Extraction"] = "completed"
            progress_bar.progress(75)
            
            # Step 3: Legacy compatibility processing
            status_text.text("Step 3/3: Finalizing results...")
            st.session_state.checkpoints["Finalization"] = "in_progress"
            
            # Extract components for compatibility with existing UI
            chunks = chapter_content.get('chunks', [])
            tables = chapter_content.get('tables', [])
            examples = self.pdf_processor.extract_examples(chapter_content)
            structure_analysis = chapter_content.get('structure', {})
            
            # Create quality results in expected format
            quality_results = {
                'overall_score': quality_metrics.get('overall_score', 0.0) * 100,  # Convert to percentage
                'text_quality': quality_metrics.get('structure_quality', 0.0) * 100,
                'structure_quality': quality_metrics.get('structure_quality', 0.0) * 100,
                'table_quality': quality_metrics.get('table_quality', 0.0) * 100,
                'example_quality': quality_metrics.get('chunk_quality', 0.0) * 100,
                'coverage_quality': quality_metrics.get('coverage_quality', 0.0) * 100,
                'issues': self._extract_issues_from_report(processing_report),
                'recommendations': processing_report.get('recommendations', []),
                'passed_threshold': quality_metrics.get('overall_score', 0.0) >= (self.quality_threshold / 100),
                'timestamp': datetime.now().isoformat()
            }
            
            st.session_state.checkpoints["Finalization"] = "completed"
            progress_bar.progress(100)
            
            # Store results
            st.session_state.results = {
                'chapter_content': chapter_content,
                'structure_analysis': structure_analysis,
                'tables': tables,
                'examples': examples,
                'chunks': chunks,
                'quality_results': quality_results,
                'processing_report': processing_report,
                'quality_metrics': quality_metrics,
                'processing_time': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }
            
            st.session_state.processing_complete = True
            status_text.text("✅ Advanced processing completed successfully!")
            
            # Auto-refresh to show results
            time.sleep(2)
            st.rerun()
            
        except Exception as e:
            st.error(f"Processing failed: {str(e)}")
            st.session_state.checkpoints["Processing"] = "failed"
            
    def _extract_issues_from_report(self, processing_report: Dict[str, Any]) -> List[str]:
        """Extract issues from processing report"""
        issues = []
        
        quality_summary = processing_report.get('quality_summary', {})
        overall_score = quality_summary.get('overall_score', 0.0)
        
        if overall_score < 0.7:
            issues.append("Overall quality below threshold")
        
        if quality_summary.get('structure_score', 0.0) < 0.7:
            issues.append("Insufficient section headers detected - structure may be incomplete")
        
        if quality_summary.get('table_score', 0.0) < 0.7:
            issues.append("Missing critical sections - may need manual section identification")
        
        if quality_summary.get('coverage_score', 0.0) < 0.8:
            issues.append("Incomplete page coverage - some content may be missing")
        
        return issues
    
    def render_results_interface(self):
        """Display processing results and analysis"""
        st.header("📊 Processing Results")
        
        if st.session_state.results is None:
            st.error("No results available. Please process a document first.")
            return
        
        results = st.session_state.results
        
        # Key metrics
        self.display_key_metrics(results)
        
        # Detailed analysis tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔍 Quality Analysis", 
            "📄 Structure Analysis", 
            "📊 Table Extraction", 
            "💡 Examples", 
            "🧩 Chunks & Metadata"
        ])
        
        with tab1:
            self.display_quality_analysis(results['quality_results'])
        
        with tab2:
            self.display_structure_analysis(results['structure_analysis'])
        
        with tab3:
            self.display_table_analysis(results['tables'])
        
        with tab4:
            self.display_examples_analysis(results['examples'])
        
        with tab5:
            self.display_chunks_analysis(results['chunks'])
        
        # Export options
        self.render_export_options(results)
        
        # Reset button
        if st.button("🔄 Process Another Document"):
            st.session_state.processing_complete = False
            st.session_state.results = None
            st.session_state.checkpoints = {}
            st.rerun()
    
    def display_key_metrics(self, results):
        """Display key processing metrics"""
        quality_score = results['quality_results']['overall_score']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Overall Quality Score", 
                f"{quality_score:.1f}%",
                delta=f"{quality_score - self.quality_threshold:.1f}%"
            )
        
        with col2:
            st.metric(
                "Processing Time", 
                f"{results['processing_time']:.1f}s"
            )
        
        with col3:
            st.metric(
                "Total Chunks", 
                len(results['chunks'])
            )
        
        with col4:
            st.metric(
                "Tables Extracted", 
                len(results['tables'])
            )
        
        # Success/failure indicators
        if quality_score >= self.quality_threshold:
            st.success("✅ Quality threshold met - Processing validation successful!")
        else:
            st.warning(f"⚠️ Quality score below threshold ({self.quality_threshold}%) - Review required")
    
    def display_quality_analysis(self, quality_results):
        """Display detailed quality analysis"""
        st.subheader("Quality Assessment Results")
        
        # Overall assessment
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Text Extraction Quality", f"{quality_results['text_quality']:.1f}%")
            st.metric("Structure Preservation", f"{quality_results['structure_quality']:.1f}%")
        
        with col2:
            st.metric("Table Quality", f"{quality_results['table_quality']:.1f}%")
            st.metric("Example Completeness", f"{quality_results['example_quality']:.1f}%")
        
        # Detailed breakdown
        st.subheader("Detailed Quality Metrics")
        
        quality_df = pd.DataFrame([
            {"Metric": "Character Accuracy", "Score": quality_results['character_accuracy'], "Threshold": 95},
            {"Metric": "Section Hierarchy", "Score": quality_results['section_hierarchy'], "Threshold": 90},
            {"Metric": "Cross-references", "Score": quality_results['cross_references'], "Threshold": 85},
            {"Metric": "Table Formatting", "Score": quality_results['table_formatting'], "Threshold": 80},
            {"Metric": "Example Integrity", "Score": quality_results['example_integrity'], "Threshold": 90}
        ])
        
        st.dataframe(quality_df, use_container_width=True)
        
        # Issues and recommendations
        if quality_results['issues']:
            st.subheader("⚠️ Issues Identified")
            for issue in quality_results['issues']:
                st.warning(f"• {issue}")
        
        if quality_results['recommendations']:
            st.subheader("💡 Recommendations")
            for rec in quality_results['recommendations']:
                st.info(f"• {rec}")
    
    def display_structure_analysis(self, structure_analysis):
        """Display structure analysis results"""
        st.subheader("Document Structure Analysis")
        
        # Hierarchy preservation
        st.write("**Section Hierarchy:**")
        for section in structure_analysis['sections']:
            indent = "  " * (section['level'] - 1)
            st.write(f"{indent}• {section['title']} (Level {section['level']})")
        
        # Content distribution
        st.subheader("Content Distribution")
        content_df = pd.DataFrame(structure_analysis['content_distribution'])
        st.bar_chart(content_df.set_index('type')['count'])
        
        # Page mapping
        st.subheader("Page Mapping")
        page_df = pd.DataFrame(structure_analysis['page_mapping'])
        st.dataframe(page_df, use_container_width=True)
    
    def display_table_analysis(self, tables):
        """Display table extraction analysis"""
        st.subheader("Table Extraction Results")
        
        if not tables:
            st.info("No tables found in Chapter 4")
            return
        
        st.write(f"**Total Tables Extracted: {len(tables)}**")
        
        for i, table in enumerate(tables):
            with st.expander(f"Table {i+1}: {table['title']}"):
                st.write(f"**Location:** Page {table['page']}")
                st.write(f"**Rows:** {table['rows']}, **Columns:** {table['columns']}")
                st.write(f"**Quality Score:** {table['quality_score']:.1f}%")
                
                # Display table content
                if table['content']:
                    st.dataframe(pd.DataFrame(table['content']), use_container_width=True)
                else:
                    st.write("Table content extraction failed")
    
    def display_examples_analysis(self, examples):
        """Display example scenarios analysis"""
        st.subheader("Example Scenarios Analysis")
        
        if not examples:
            st.info("No example scenarios found in Chapter 4")
            return
        
        st.write(f"**Total Examples Extracted: {len(examples)}**")
        
        for i, example in enumerate(examples):
            with st.expander(f"Example {i+1}: {example['title']}"):
                st.write(f"**Location:** Page {example['page']}")
                st.write(f"**Type:** {example['type']}")
                st.write(f"**Completeness:** {example['completeness']:.1f}%")
                
                # Display example content
                st.text_area(
                    "Content", 
                    example['content'], 
                    height=200,
                    key=f"example_{i}"
                )
    
    def display_chunks_analysis(self, chunks):
        """Display chunking and metadata analysis"""
        st.subheader("Chunks and Metadata Analysis")
        
        # Chunk statistics
        chunk_stats = {
            'total_chunks': len(chunks),
            'avg_size': sum(len(c['content']) for c in chunks) / len(chunks),
            'metadata_fields': len(chunks[0]['metadata']) if chunks else 0
        }
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Chunks", chunk_stats['total_chunks'])
        with col2:
            st.metric("Average Size", f"{chunk_stats['avg_size']:.0f} chars")
        with col3:
            st.metric("Metadata Fields", chunk_stats['metadata_fields'])
        
        # Sample chunks
        st.subheader("Sample Chunks")
        
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            with st.expander(f"Chunk {i+1}: {chunk['metadata']['section']}"):
                st.write(f"**Section:** {chunk['metadata']['section']}")
                st.write(f"**Page:** {chunk['metadata']['page']}")
                st.write(f"**Content Type:** {chunk['metadata']['content_type']}")
                st.write(f"**Size:** {len(chunk['content'])} characters")
                
                st.text_area(
                    "Content", 
                    chunk['content'][:500] + "..." if len(chunk['content']) > 500 else chunk['content'],
                    height=150,
                    key=f"chunk_{i}"
                )
                
                # Metadata
                st.json(chunk['metadata'])
    
    def render_export_options(self, results):
        """Render export options"""
        st.header("📤 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export Full Report"):
                report_data = self.generate_full_report(results)
                st.download_button(
                    label="Download Report",
                    data=report_data,
                    file_name=f"asc606_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("🧩 Export Chunks"):
                chunks_data = json.dumps(results['chunks'], indent=2)
                st.download_button(
                    label="Download Chunks",
                    data=chunks_data,
                    file_name=f"asc606_chunks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("📊 Export Quality Report"):
                quality_data = json.dumps(results['quality_results'], indent=2)
                st.download_button(
                    label="Download Quality Report",
                    data=quality_data,
                    file_name=f"asc606_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    def generate_full_report(self, results):
        """Generate comprehensive processing report"""
        report = {
            'timestamp': results['timestamp'],
            'processing_time': results['processing_time'],
            'configuration': {
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
                'quality_threshold': self.quality_threshold
            },
            'results': results,
            'summary': {
                'total_pages': 21,  # Pages 63-83
                'total_chunks': len(results['chunks']),
                'total_tables': len(results['tables']),
                'total_examples': len(results['examples']),
                'overall_quality': results['quality_results']['overall_score']
            }
        }
        
        return json.dumps(report, indent=2)
    
    def show_expected_output(self):
        """Show expected output format"""
        st.header("📋 Expected Output Format")
        
        with st.expander("Expected Chapter 4 Sections"):
            st.write("""
            **4.1 Identifying the promised goods and services in the contract**
            - 4.1.1 Promised goods or services that are immaterial
            - 4.1.2 Shipping and handling activities
            
            **4.2 Determining when promises are performance obligations**
            - 4.2.1 Determination of distinct
            - 4.2.2 Series of distinct goods or services
            - 4.2.3 Examples of identifying performance obligations
            
            **4.3 Promised goods and services that are not distinct**
            
            **4.4 Principal versus agent considerations**
            - 4.4.1 Identifying the specified good or service
            - 4.4.2 Control of the specified good or service
            - 4.4.3 Recognizing revenue as a principal or agent
            - 4.4.4 Examples
            
            **4.5 Consignment arrangements**
            
            **4.6 Customer options for additional goods or services**
            
            **4.7 Sale of products with a right of return**
            """)

# Run the application
if __name__ == "__main__":
    app = ASC606ProcessingApp()
    app.run()
