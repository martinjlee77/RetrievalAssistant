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
    
    # Additional assessment details
    if hasattr(contract_data, 'ssp_represents_contract_price') and contract_data.ssp_represents_contract_price is not None:
        ssp_status = "Yes" if contract_data.ssp_represents_contract_price else "No"
        context += f"""

**PRICING ASSESSMENT:**
• Contract Prices Represent Standalone Selling Price: {ssp_status}
"""
    
    if hasattr(contract_data, 'revenue_recognition_timing_details') and contract_data.revenue_recognition_timing_details:
        context += f"""
• Revenue Recognition Timing Notes: {contract_data.revenue_recognition_timing_details}
"""
    
    # CRITICAL: Add the steering inputs that control LLM analysis
    steering_context = ""
    
    # Key focus areas - most important steering input
    if hasattr(contract_data, 'key_focus_areas') and contract_data.key_focus_areas:
        steering_context += f"""

**🎯 SPECIFIC FOCUS AREAS (HIGH PRIORITY):**
{contract_data.key_focus_areas}

IMPORTANT: The user has specifically requested focus on the above areas. Pay special attention to these questions/clauses/risks and provide detailed analysis with supporting citations.
"""
    
    # Audience tailoring
    if hasattr(contract_data, 'memo_audience') and contract_data.memo_audience:
        memo_audience = contract_data.memo_audience
        if memo_audience == 'Management Review':
            steering_context += """

**MEMO AUDIENCE: Management Review**
- Focus on key judgments, financial impact, and business implications
- Use less technical jargon and emphasize the "so what" for decision-makers
- Summarize critical conclusions upfront
"""
        elif memo_audience == 'Deal Desk / Sales Team':
            steering_context += """

**MEMO AUDIENCE: Deal Desk / Sales Team**
- Focus on explaining revenue recognition impact of specific contract terms
- Translate complex accounting rules into practical guidance for deal structuring
- Explain how different clauses affect revenue timing
"""
        else:  # Technical Accounting Team / Audit File (default)
            steering_context += """

**MEMO AUDIENCE: Technical Accounting Team / Audit File**
- Provide deep technical compliance and audit readiness
- Include detailed step-by-step reasoning and precise ASC 606 citations
- Use full technical detail suitable for expert accountants and auditors
"""
    
    # Materiality threshold
    if hasattr(contract_data, 'materiality_threshold') and contract_data.materiality_threshold:
        threshold = contract_data.materiality_threshold
        currency = getattr(contract_data, 'currency', 'USD')
        steering_context += f"""

**MATERIALITY THRESHOLD: {threshold:,} ({currency})**
- Focus detailed analysis on contract elements exceeding this threshold
- Note materiality of bonuses, penalties, discounts, and other variable elements
- Include materiality analysis in your conclusions and briefly mention immaterial elements (elements below threshold)
"""
    
    context += steering_context
    
    return context