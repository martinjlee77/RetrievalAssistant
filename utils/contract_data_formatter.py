"""
Contract Data Formatter
Converts ContractData objects into comprehensive prompt context
"""

from typing import Dict, Any, Optional
from core.models import ContractData

def format_contract_data_for_prompt(contract_data: ContractData) -> str:
    """
    Convert complete ContractData object into structured prompt context.
    This ensures ALL user inputs are included in the LLM analysis.
    """
    
    context = f"""
**COMPLETE CONTRACT INFORMATION:**

**Basic Details:**
• Analysis Title: {contract_data.analysis_title}
• Customer: {contract_data.customer_name}
• Contract Period: {contract_data.contract_start} to {contract_data.contract_end}
• Currency: {contract_data.currency}
• Document Types: {', '.join(contract_data.contract_types)}
• File: {contract_data.uploaded_file_name}
"""
    
    # Optional arrangement description
    if contract_data.arrangement_description:
        context += f"""
• Arrangement Summary: {contract_data.arrangement_description}
"""
    
    context += f"""

**MANAGEMENT ASSESSMENTS:**
• Collectibility: {'Probable' if contract_data.collectibility else 'Not Probable'}
• Combined Contract: {'Yes' if contract_data.is_combined_contract else 'No'}
• Contract Modification: {'Yes' if contract_data.is_modification else 'No'}
"""
    
    # Modification details
    if contract_data.is_modification and contract_data.original_contract_uploaded is not None:
        context += f"""
• Original Contract Uploaded: {'Yes' if contract_data.original_contract_uploaded else 'No'}
"""
    
    # Analysis areas requiring attention
    analysis_areas = []
    
    if contract_data.principal_agent_involved:
        details = contract_data.principal_agent_details or "Analysis required - details not provided"
        analysis_areas.append(f"Principal vs Agent: {details}")
    
    if contract_data.variable_consideration_involved:
        details = contract_data.variable_consideration_details or "Present - details not provided"
        analysis_areas.append(f"Variable Consideration: {details}")
    
    if contract_data.financing_component_involved:
        details = contract_data.financing_component_details or "Present - details not provided"
        analysis_areas.append(f"Significant Financing Component: {details}")
    
    if contract_data.noncash_consideration_involved:
        details = contract_data.noncash_consideration_details or "Present - details not provided"
        analysis_areas.append(f"Noncash Consideration: {details}")
    
    if contract_data.consideration_payable_involved:
        details = contract_data.consideration_payable_details or "Present - details not provided"
        analysis_areas.append(f"Consideration Payable to Customer: {details}")
    
    if analysis_areas:
        context += f"""

**KEY ANALYSIS AREAS:**
{chr(10).join(f"• {area}" for area in analysis_areas)}
"""
    
    # Pricing and revenue recognition
    context += f"""

**PRICING & RECOGNITION:**
• Contract Prices Represent SSP: {'Yes' if contract_data.ssp_represents_contract_price else 'No'}
"""
    
    if contract_data.revenue_recognition_timing_details:
        context += f"""
• Revenue Recognition Timing: {contract_data.revenue_recognition_timing_details}
"""
    
    # Analysis steering (most important for LLM guidance)
    if contract_data.key_focus_areas:
        context += f"""

**SPECIFIC FOCUS AREAS (HIGH PRIORITY):**
{contract_data.key_focus_areas}

IMPORTANT: Pay special attention to these questions/clauses/risks and provide detailed analysis with supporting citations.
"""
    
    # Memo specifications
    context += f"""

**MEMO SPECIFICATIONS:**
• Target Audience: {contract_data.memo_audience}
"""
    
    if contract_data.materiality_threshold:
        context += f"""
• Materiality Threshold: {contract_data.materiality_threshold:,} {contract_data.currency}
"""
    
    # Add specific guidance based on audience
    if contract_data.memo_audience == 'Management Review':
        context += """

**AUDIENCE GUIDANCE:** Focus on key judgments, financial impact, and business implications. Use less technical jargon and emphasize the "so what" for decision-makers.
"""
    elif contract_data.memo_audience == 'Deal Desk / Sales Team':
        context += """

**AUDIENCE GUIDANCE:** Focus on explaining revenue recognition impact of specific contract terms. Translate complex accounting rules into practical guidance for deal structuring.
"""
    else:  # Technical Accounting Team / Audit File
        context += """

**AUDIENCE GUIDANCE:** Provide deep technical compliance and audit readiness with detailed step-by-step reasoning and precise ASC 606 citations.
"""
    
    return context