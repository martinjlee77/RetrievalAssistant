"""
Centralized Data Models for Multi-Standard Platform
"""

from pydantic import BaseModel, ValidationError, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

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

class ASC606Analysis(BaseModel):
    """Clean, consolidated ASC 606 analysis results with step-by-step architecture"""
    
    # Core analysis results - single source of truth
    professional_memo: str = ""  # Final comprehensive memo
    step_by_step_details: Dict[str, Any] = Field(default_factory=dict)  # Detailed step analysis
    
    # Analysis metadata
    source_quality: str = "General Knowledge"
    relevant_chunks: int = 0
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Analysis overview
    contract_overview: Dict[str, Any] = Field(default_factory=dict)
    citations: List[str] = Field(default_factory=list)
    implementation_guidance: List[str] = Field(default_factory=list)
    
    # Legacy compatibility methods
    @property
    def step1_contract_identification(self) -> Dict[str, Any]:
        """Derive step 1 data from step_by_step_details"""
        return self.step_by_step_details.get("step_1", {})
    
    @property
    def step2_performance_obligations(self) -> Dict[str, Any]:
        """Derive step 2 data from step_by_step_details"""
        return self.step_by_step_details.get("step_2", {})
    
    @property
    def step3_transaction_price(self) -> Dict[str, Any]:
        """Derive step 3 data from step_by_step_details"""
        return self.step_by_step_details.get("step_3", {})
    
    @property
    def step4_price_allocation(self) -> Dict[str, Any]:
        """Derive step 4 data from step_by_step_details"""
        return self.step_by_step_details.get("step_4", {})
    
    @property
    def step5_revenue_recognition(self) -> Dict[str, Any]:
        """Derive step 5 data from step_by_step_details"""
        return self.step_by_step_details.get("step_5", {})

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