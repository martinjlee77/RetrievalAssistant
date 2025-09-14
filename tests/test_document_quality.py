"""
Basic tests for the document quality feedback system.
Tests the 3-tier quality detection (Good/Degraded/Blocked).
"""

import unittest
from unittest.mock import Mock, patch
import io
from utils.document_extractor import DocumentExtractor


class TestDocumentQuality(unittest.TestCase):
    """Test document quality detection and feedback system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = DocumentExtractor()
    
    def test_quality_state_determination(self):
        """Test the 3-tier quality state determination logic."""
        
        # Test blocked state - extreme issues
        extreme_issues = ["Severely broken text patterns (200.0 per 1000 chars)"]
        normal_reasons = []
        metrics = {'broken_pattern_rate': 200, 'non_ascii_ratio': 0.1}
        
        state = self.extractor._determine_quality_state(extreme_issues, normal_reasons, metrics)
        self.assertEqual(state, "blocked")
        
        # Test blocked state - multiple normal issues
        extreme_issues = []
        normal_reasons = ["Low text density", "High digit mix"]
        metrics = {'broken_pattern_rate': 40, 'non_ascii_ratio': 0.05}
        
        state = self.extractor._determine_quality_state(extreme_issues, normal_reasons, metrics)
        self.assertEqual(state, "blocked")
        
        # Test degraded state - single normal issue
        extreme_issues = []
        normal_reasons = ["Low text density"]
        metrics = {'broken_pattern_rate': 40, 'non_ascii_ratio': 0.05}
        
        state = self.extractor._determine_quality_state(extreme_issues, normal_reasons, metrics)
        self.assertEqual(state, "degraded")
        
        # Test degraded state - moderate thresholds
        extreme_issues = []
        normal_reasons = []
        metrics = {'broken_pattern_rate': 130, 'non_ascii_ratio': 0.15}  # Below extreme but above moderate
        
        state = self.extractor._determine_quality_state(extreme_issues, normal_reasons, metrics)
        self.assertEqual(state, "degraded")
        
        # Test good state - clean document
        extreme_issues = []
        normal_reasons = []
        metrics = {'broken_pattern_rate': 5, 'non_ascii_ratio': 0.01, 'avg_chars_per_page': 800}
        
        state = self.extractor._determine_quality_state(extreme_issues, normal_reasons, metrics)
        self.assertEqual(state, "good")
    
    def test_text_quality_analysis(self):
        """Test text quality analysis with sample texts."""
        
        # Good quality text
        good_text = """
        This is a well-formatted document with proper text structure.
        It contains complete sentences and normal punctuation.
        The content is readable and professionally formatted.
        This document has sufficient character density and clean text patterns.
        """ * 10  # Make it longer to meet density requirements
        
        analysis = self.extractor._analyze_text_quality(good_text, pages=1)
        self.assertEqual(analysis['quality_state'], 'good')
        self.assertFalse(analysis['is_likely_scanned'])
        
        # Degraded quality text (simulating OCR artifacts)
        degraded_text = """
        Th is do cu ment ha s so me O CR ar ti facts.
        The text den sity is rea son able but the re are
        bro ken word pat terns through out the docu ment.
        Some cha rac ters may be mis sing or incor rect.
        """ * 20  # Longer text with consistent artifacts
        
        analysis = self.extractor._analyze_text_quality(degraded_text, pages=1)
        self.assertIn(analysis['quality_state'], ['degraded', 'blocked'])  # Could be either depending on severity
        
        # Blocked quality text (severe OCR corruption)
        blocked_text = """
        ~!@#$%^&*()_+ th~i~ ~s~ v~e~r~y b~a~d O~C~R
        !!!@@@ bro ken wo rds ever ywhe re ###$$$
        m~u~l~t~i~p~l~e~ ~s~p~a~c~e~ ~r~u~n~s~
        """ * 30  # Lots of severely corrupted text
        
        analysis = self.extractor._analyze_text_quality(blocked_text, pages=1)
        # Should be blocked due to extreme artifacts
        self.assertTrue(analysis['is_likely_scanned'])
    
    def test_invoice_like_document(self):
        """Test that invoice-like documents (short, lots of numbers) are handled correctly."""
        
        # Simulate Netflix invoice content
        invoice_text = """
        Netflix, Inc.
        121 Albright Way
        Los Gatos, CA 95032, USA
        
        martinjlee@outlook.com
        
        Invoice # E355F-92FF9-F6069-07497
        
        Date           Description                  Service Period     Amount      Tax    Total
        9/26/24        Streaming Service            9/26/24—10/25/24    $15.49   $1.03   $16.52
        
        SUBTOTAL       $15.49
        TAX TOTAL        $1.03
        TOTAL       $16.52
        
        Payment Method:              •••• •••• •••• 0459
        """
        
        analysis = self.extractor._analyze_text_quality(invoice_text, pages=1)
        
        # Invoice should not be blocked despite short length and many numbers
        self.assertFalse(analysis['is_likely_scanned'])
        # Quality state should be good or degraded, not blocked
        self.assertIn(analysis['quality_state'], ['good', 'degraded'])
    
    def test_terms_document(self):
        """Test that terms of service documents are handled correctly."""
        
        # Simulate Netflix terms content with some OCR artifacts
        terms_text = """
        Netflix Terms of Use
        Netflix provides a personalized subscription service that allows our members to access
        entertainment content over the Internet on certain Internet-connected devices.
        
        The Netflix service is provided to you by Netflix Inc. You have accepted these Terms of Use, which
        govern your use of our service. As used in these Terms of Use, "Netflix service", "our service" or
        "the service" means the personalized service provided by Netflix for discovering and accessing
        Netflix content.
        
        1. Membership
        
        1.1. Your Netflix membership will continue and automatically renew until terminated. To use the
        Netflix service you must have Internet access and a Netflix ready device and provide us with
        one or more Payment Methods.
        """ * 5  # Repeat to make longer
        
        analysis = self.extractor._analyze_text_quality(terms_text, pages=1)
        
        # Terms document should process successfully
        self.assertFalse(analysis['is_likely_scanned'])
        self.assertIn(analysis['quality_state'], ['good', 'degraded'])


class TestDocumentQualityFeedbackUI(unittest.TestCase):
    """Test the quality feedback UI components."""
    
    def test_quality_icon_mapping(self):
        """Test that quality states map to correct icons."""
        from shared.ui_components import SharedUIComponents
        
        self.assertEqual(SharedUIComponents.get_quality_icon('good'), '✅')
        self.assertEqual(SharedUIComponents.get_quality_icon('degraded'), '⚠️')
        self.assertEqual(SharedUIComponents.get_quality_icon('blocked'), '❌')
        self.assertEqual(SharedUIComponents.get_quality_icon('unknown'), '❓')
    
    @patch('streamlit.success')
    @patch('streamlit.write')
    def test_display_good_quality_files(self, mock_write, mock_success):
        """Test display of files with good quality."""
        from shared.ui_components import SharedUIComponents
        
        file_results = [
            {
                'filename': 'contract.pdf',
                'quality_state': 'good',
                'word_count': 5000,
                'detection_reasons': []
            }
        ]
        
        SharedUIComponents.display_document_quality_feedback(file_results)
        
        # Should show success message
        mock_success.assert_called_once()
        # Should display file with good quality indicator
        mock_write.assert_called()
    
    @patch('streamlit.warning')
    @patch('streamlit.write')
    @patch('streamlit.expander')
    def test_display_degraded_quality_files(self, mock_expander, mock_write, mock_warning):
        """Test display of files with degraded quality."""
        from shared.ui_components import SharedUIComponents
        
        file_results = [
            {
                'filename': 'invoice.pdf',
                'quality_state': 'degraded',
                'word_count': 300,
                'detection_reasons': ['Low text density (305 chars/page < 600)']
            }
        ]
        
        SharedUIComponents.display_document_quality_feedback(file_results)
        
        # Should show warning message
        mock_warning.assert_called_once()
        # Should create expander for quality details
        mock_expander.assert_called()


if __name__ == '__main__':
    # Run tests
    unittest.main()