"""
Centralized Data Models for Multi-Standard Platform
"""

from pydantic import BaseModel, ValidationError, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
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
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    currency: str = "USD"
    uploaded_file_name: str = ""
    document_names: List[str] = Field(default_factory=list)  # List of uploaded document filenames
    contract_types: List[str] = Field(default_factory=list)
    
    # New steering fields from Tab 3
    key_focus_areas: Optional[str] = None
    memo_audience: str = "Technical Accounting Team / Audit File"
    materiality_threshold: Optional[int] = None
    
    # All fields below correspond to the new UI toggles and text areas
    collectibility: Optional[bool] = None
    is_combined_contract: Optional[bool] = None
    is_modification: Optional[bool] = None
    original_contract_uploaded: Optional[bool] = None
    principal_agent_involved: Optional[bool] = None
    principal_agent_details: Optional[str] = None
    variable_consideration_involved: Optional[bool] = None
    variable_consideration_details: Optional[str] = None
    financing_component_involved: Optional[bool] = None
    financing_component_details: Optional[str] = None
    noncash_consideration_involved: Optional[bool] = None
    noncash_consideration_details: Optional[str] = None
    consideration_payable_involved: Optional[bool] = None
    consideration_payable_details: Optional[str] = None
    ssp_represents_contract_price: Optional[bool] = None
    revenue_recognition_timing_details: Optional[str] = None

class ASC606Analysis(BaseModel):
    """Clean, consolidated ASC 606 analysis results with step-by-step architecture"""
    
    # Core analysis results - single source of truth
    professional_memo: str = ""  # Final comprehensive memo
    step_by_step_details: Dict[str, Any] = Field(default_factory=dict)  # Detailed step analysis
    
    # Analysis metadata
    source_quality: str = "General Knowledge"
    relevant_chunks: int = 0
    analysis_complexity: str = "Simple"  # Simple, Medium, Complex
    analysis_duration_seconds: int = 0
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Analysis overview
    contract_overview: Dict[str, Any] = Field(default_factory=dict)
    citations: List[str] = Field(default_factory=list)
    implementation_guidance: List[str] = Field(default_factory=list)


# ==================== ASC 340-40 MODELS ====================

class ContractCostsData(BaseModel):
    """Contract costs data model for ASC 340-40 analysis - V2 Simplified"""
    # Basic Information
    analysis_title: str
    company_name: str
    policy_effective_date: Optional[date] = None
    contract_types_in_scope: List[str] = Field(default_factory=list)  # Now primary cost categories
    cost_timing: str = "All Periods"  # Fixed value since removed from UI
    
    # Optional Context
    arrangement_description: Optional[str] = None
    
    # Simplified policy-specific fields
    cost_type: str = "Incremental Cost of Obtaining"  # Default since simplified
    recovery_probable: bool = True
    standard_amortization_period: int = 36
    practical_expedient: bool = False
    contract_type_scope: Optional[List[str]] = None
    
    # Hard-coded values as per requirements
    memo_audience: str = "Technical Accounting Team"  # Hard-coded as requested
    
    # Document information (now required)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    document_names: List[str] = Field(default_factory=list)


class ASC340Analysis(BaseModel):
    """ASC 340-40 Contract Costs analysis results"""
    
    # Core contract data
    contract_data: ContractCostsData
    
    # 4-Step Analysis Results
    step1_scope_assessment: Dict[str, Any] = Field(default_factory=dict)
    step2_cost_classification: Dict[str, Any] = Field(default_factory=dict)
    step3_measurement_policy: Dict[str, Any] = Field(default_factory=dict)
    step4_illustrative_impact: Dict[str, Any] = Field(default_factory=dict)
    
    # Generated Outputs
    professional_memo: str = ""  # Final comprehensive memo
    policy_summary: str = ""
    
    # Analysis Metadata
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    analyzer_version: str = "ASC340_v1.0"


# ==================== ASC 842 MODELS ====================

class LeaseClassificationData(BaseModel):
    """Lease data model for ASC 842 classification analysis"""
    # Basic Information
    analysis_title: str
    company_name: str
    lease_description: str
    lease_commencement_date: Optional[date] = None
    
    # Classification Criteria (5 tests)
    ownership_transfer: Optional[bool] = None
    ownership_transfer_details: Optional[str] = None
    
    purchase_option: Optional[bool] = None
    purchase_option_details: Optional[str] = None
    
    lease_term_major_part: Optional[bool] = None
    lease_term_details: Optional[str] = None
    economic_life_years: Optional[int] = None
    lease_term_years: Optional[int] = None
    
    present_value_substantially_all: Optional[bool] = None
    present_value_details: Optional[str] = None
    fair_value: Optional[float] = None
    present_value_payments: Optional[float] = None
    
    alternative_use: Optional[bool] = None
    alternative_use_details: Optional[str] = None
    
    # Document Information
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    document_names: List[str] = Field(default_factory=list)
    
    # Analysis Context
    memo_audience: str = "Technical Accounting Team"
    materiality_threshold: Optional[str] = None


class LeaseMeasurementData(BaseModel):
    """Lease measurement data for calculation purposes"""
    # Basic Information
    analysis_title: str
    lease_classification: str  # "Operating" or "Finance"
    
    # Financial Terms
    monthly_payment: float
    lease_term_months: int
    discount_rate: float  # As percentage (e.g., 5.0 for 5%)
    
    # Optional Components
    initial_direct_costs: Optional[float] = 0.0
    prepaid_rent: Optional[float] = 0.0
    lease_incentives: Optional[float] = 0.0
    
    # Calculated Values (populated by calculator)
    present_value_payments: Optional[float] = None
    initial_rou_asset: Optional[float] = None
    initial_lease_liability: Optional[float] = None
    
    # Import Source
    imported_from_classification: bool = False
    classification_analysis_id: Optional[str] = None


class LeaseJournalData(BaseModel):
    """Journal entry data for lease accounting"""
    # Basic Information
    analysis_title: str
    lease_classification: str
    
    # Schedule Information
    total_periods: int
    monthly_payment: float
    discount_rate: float
    
    # Export Preferences
    export_format: str = "CSV"  # CSV or JSON
    erp_system: Optional[str] = None
    include_headers: bool = True
    
    # Import Source
    imported_from_calculator: bool = False
    measurement_analysis_id: Optional[str] = None


class ASC842Analysis(BaseModel):
    """Complete ASC 842 lease analysis results"""
    
    # Analysis Type and Data
    analysis_type: str  # "classification", "measurement", "journal_entries"
    
    # Core Data (optional based on analysis type)
    classification_data: Optional[LeaseClassificationData] = None
    measurement_data: Optional[LeaseMeasurementData] = None
    journal_data: Optional[LeaseJournalData] = None
    
    # Analysis Results
    classification_memo: str = ""  # For Module 1
    amortization_schedule: List[Dict[str, Any]] = Field(default_factory=list)  # For Module 2
    journal_entries: List[Dict[str, Any]] = Field(default_factory=list)  # For Module 3
    
    # Analysis Metadata
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    analyzer_version: str = "ASC842_v1.0"
    
    # Data Flow Between Modules
    module_1_complete: bool = False
    module_2_complete: bool = False
    module_3_complete: bool = False
    
    # Export Capabilities
    export_data: Dict[str, Any] = Field(default_factory=dict)
    relevant_chunks: int = 0
    analysis_duration_seconds: int = 0
    
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