"""
Centralized Data Models for Multi-Standard Platform
"""

from pydantic import BaseModel, ValidationError
from typing import Optional, List, Dict, Any
from datetime import date
from dataclasses import dataclass

# ==================== ASC 606 MODELS ====================

class PerformanceObligation(BaseModel):
    name: str
    type: str  # License, Service, Good, etc.
    timing: str  # Point in Time, Over Time
    ssp: float  # Standalone selling price

class VariableConsideration(BaseModel):
    type: str  # Performance Bonus, Penalty, etc.
    estimated_amount: float

class ContractData(BaseModel):
    """Contract data model matching the new UI structure with toggles"""
    # Basic Contract Information  
    analysis_title: str
    customer_name: str
    arrangement_description: Optional[str] = None  # Now optional per UI changes
    contract_start: date
    contract_end: date
    currency: str
    uploaded_file_name: str
    contract_types: List[str]
    
    # New steering fields from Tab 3
    key_focus_areas: Optional[str] = None
    memo_audience: str = "Technical Accounting Team / Audit File"
    materiality_threshold: Optional[int] = None
    
    # All fields below correspond to the new UI toggles and text areas
    collectibility: bool
    is_combined_contract: bool
    is_modification: bool
    original_contract_uploaded: Optional[bool] = None
    principal_agent_involved: bool
    principal_agent_details: Optional[str] = None
    variable_consideration_involved: bool
    variable_consideration_details: Optional[str] = None
    financing_component_involved: bool
    financing_component_details: Optional[str] = None
    noncash_consideration_involved: bool
    noncash_consideration_details: Optional[str] = None
    consideration_payable_involved: bool
    consideration_payable_details: Optional[str] = None
    ssp_represents_contract_price: bool
    revenue_recognition_timing_details: Optional[str] = None

@dataclass
class ASC606Analysis:
    """Structure for ASC 606 analysis results with step-by-step architecture support"""
    # New comprehensive analysis fields
    five_step_analysis: str = ""  # Final comprehensive memo
    step_by_step_details: Dict[str, Any] = None  # Detailed step analysis
    
    # Analysis metadata
    source_quality: str = "General Knowledge"
    relevant_chunks: int = 0
    analysis_timestamp: str = ""
    
    # Legacy fields for backwards compatibility
    reconciliation_analysis: Optional[Dict[str, List[Dict[str, Any]]]] = None
    contract_overview: Optional[Dict[str, Any]] = None
    step1_contract_identification: Optional[Dict[str, Any]] = None
    step2_performance_obligations: Optional[Dict[str, Any]] = None
    step3_transaction_price: Optional[Dict[str, Any]] = None
    step4_price_allocation: Optional[Dict[str, Any]] = None
    step5_revenue_recognition: Optional[Dict[str, Any]] = None
    professional_memo: str = ""
    implementation_guidance: Optional[List[str]] = None
    citations: Optional[List[str]] = None
    not_applicable_items: Optional[List[str]] = None
    
    def __post_init__(self):
        """Initialize None fields with empty defaults"""
        if self.step_by_step_details is None:
            self.step_by_step_details = {}
        if self.reconciliation_analysis is None:
            self.reconciliation_analysis = {"confirmations": [], "discrepancies": []}
        if self.contract_overview is None:
            self.contract_overview = {}
        if self.step1_contract_identification is None:
            self.step1_contract_identification = {}
        if self.step2_performance_obligations is None:
            self.step2_performance_obligations = {}
        if self.step3_transaction_price is None:
            self.step3_transaction_price = {}
        if self.step4_price_allocation is None:
            self.step4_price_allocation = {}
        if self.step5_revenue_recognition is None:
            self.step5_revenue_recognition = {}
        if self.implementation_guidance is None:
            self.implementation_guidance = []
        if self.citations is None:
            self.citations = []
        if self.not_applicable_items is None:
            self.not_applicable_items = []

# ==================== ASC 842 MODELS ====================

class LeasePayment(BaseModel):
    payment_date: date
    amount: float
    payment_type: str  # Base, Variable, etc.

class LeaseData(BaseModel):
    """Data model for lease analysis"""
    analysis_title: str
    lessor_name: str
    lessee_name: str
    asset_description: str
    lease_commencement: date
    lease_end: date
    lease_term_months: int
    discount_rate: float
    payments: List[LeasePayment]
    uploaded_file_name: str
    
    # Analysis Configuration
    analysis_depth: str = "Standard Analysis"
    output_format: str = "Professional Memo"
    include_citations: bool = True
    include_examples: bool = False
    additional_notes: Optional[str] = ""

@dataclass
class ASC842Analysis:
    """Structure for ASC 842 analysis results"""
    lease_classification: Dict[str, Any]
    initial_measurement: Dict[str, Any]
    subsequent_measurement: Dict[str, Any]
    presentation_disclosure: Dict[str, Any]
    professional_memo: str
    implementation_guidance: List[str]
    citations: List[str]
    not_applicable_items: List[str]

# ==================== GENERIC MODELS ====================

class AnalysisResult(BaseModel):
    """Generic analysis result wrapper"""
    standard: str
    analysis_data: Dict[str, Any]
    memo: str
    metadata: Dict[str, Any]

class StandardConfig(BaseModel):
    """Configuration for each accounting standard"""
    code: str
    name: str
    description: str
    status: str
    analyzer_class: str
    knowledge_base_collection: str
    prompt_framework: str