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
    """Contract data model including preliminary assessment fields"""
    # Basic Contract Information
    analysis_title: str
    customer_name: str
    arrangement_description: str
    contract_start: date
    contract_end: date
    currency: str
    uploaded_file_name: str
    contract_types: Optional[List[str]] = None
    
    # Analysis Configuration
    analysis_depth: str = "Standard Analysis"
    output_format: str = "Professional Memo"
    include_citations: bool = True
    include_examples: bool = False
    additional_notes: Optional[str] = ""
    
    # Preliminary Assessment Fields
    is_modification: bool = False
    performance_obligations: List[Dict[str, Any]] = []
    fixed_consideration: float = 0.0
    variable_consideration: Optional[Dict[str, Any]] = None
    financing_component: bool = False
    material_rights: bool = False
    customer_options: bool = False
    collectibility_assessment: str = "Probable"
    has_consideration_payable: bool = False
    consideration_payable_amount: float = 0.0

@dataclass
class ASC606Analysis:
    """Structure for ASC 606 analysis results"""
    reconciliation_analysis: Dict[str, List[Dict[str, Any]]]
    contract_overview: Dict[str, Any]
    step1_contract_identification: Dict[str, Any]
    step2_performance_obligations: Dict[str, Any]
    step3_transaction_price: Dict[str, Any]
    step4_price_allocation: Dict[str, Any]
    step5_revenue_recognition: Dict[str, Any]
    professional_memo: str
    implementation_guidance: List[str]
    citations: List[str]
    not_applicable_items: List[str]

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