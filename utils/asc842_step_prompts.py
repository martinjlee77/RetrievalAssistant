#!/usr/bin/env python3
"""
ASC 842 Lease Accounting Step Prompts
Modular prompt system for lease classification, measurement, and journal entries
"""

from typing import Dict, Any
from core.models import ASC842Analysis, LeaseClassificationData


class ASC842StepPrompts:
    """ASC 842 step-by-step prompt templates with knowledge hierarchy"""
    
    # Memo header configuration
    MEMO_HEADER = "# LEASE ACCOUNTING MEMORANDUM"
    
    @staticmethod
    def get_classification_system_prompt() -> str:
        """System prompt for lease classification analysis"""
        return """You are an expert lease accounting analyst specializing in ASC 842 lease classification. Your task is to analyze lease contracts and determine whether they should be classified as operating or finance leases.

KNOWLEDGE HIERARCHY FOR ANALYSIS:
1. Contract Text → Primary source of lease terms and conditions
2. ASC 842 Authoritative Guidance → Official FASB standards (paragraphs 842-XX-XX-X)
3. EY Interpretative Guidance → Professional implementation guidance and examples

FIVE CLASSIFICATION TESTS (ASC 842-10-25-2):
A lease is classified as a finance lease if it meets ANY ONE of these criteria:

1. OWNERSHIP TRANSFER: The lease transfers ownership of the underlying asset to the lessee by the end of the lease term.

2. PURCHASE OPTION: The lease grants the lessee an option to purchase the underlying asset that the lessee is reasonably certain to exercise.

3. LEASE TERM: The lease term is for the major part of the remaining economic life of the underlying asset. However, if the commencement date falls at or near the end of the economic life of the underlying asset, this criterion shall not be used for lease classification.

4. PRESENT VALUE: The present value of the sum of the lease payments and any residual value guaranteed by the lessee that is not already reflected in the lease payments equals or exceeds substantially all of the fair value of the underlying asset.

5. ALTERNATIVE USE: The underlying asset is of such a specialized nature that it is expected to have no alternative use to the lessor at the end of the lease term.

ANALYSIS REQUIREMENTS:
- Apply each test systematically with specific contract evidence
- Use authoritative guidance for technical interpretations
- Cite specific ASC 842 paragraphs for regulatory support
- Provide clear reasoning for each test conclusion
- Make definitive classification recommendation

If ANY test is met → FINANCE LEASE
If NO tests are met → OPERATING LEASE"""

    @staticmethod
    def get_classification_user_prompt(
        contract_text: str, 
        lease_data: LeaseClassificationData,
        rag_context: str
    ) -> str:
        """User prompt for classification analysis with contract and data"""
        return f"""Analyze this lease contract for ASC 842 classification:

=== LEASE CONTRACT ===
{contract_text}

=== LEASE DATA SUMMARY ===
Asset Type: {lease_data.asset_type}
Lease Term: {lease_data.lease_term_months} months
Annual Payments: ${lease_data.annual_lease_payment:,.2f}
Asset Fair Value: ${lease_data.asset_fair_value:,.2f} (if provided)
Discount Rate: {lease_data.discount_rate}%
Purchase Option: {lease_data.purchase_option_exists}
Ownership Transfer: {lease_data.ownership_transfer}
Economic Life: {lease_data.asset_economic_life_years} years (if provided)

{rag_context}

=== CLASSIFICATION ANALYSIS REQUIRED ===

Apply each of the 5 classification tests systematically:

**TEST 1 - OWNERSHIP TRANSFER**
- Contract Evidence: [Quote specific contract language]
- ASC 842 Analysis: [Apply authoritative guidance]
- Conclusion: [Met/Not Met with reasoning]

**TEST 2 - PURCHASE OPTION** 
- Contract Evidence: [Quote purchase option terms if any]
- Reasonably Certain Analysis: [Evaluate likelihood of exercise]
- ASC 842 Analysis: [Apply guidance on reasonably certain determination]
- Conclusion: [Met/Not Met with reasoning]

**TEST 3 - LEASE TERM vs ECONOMIC LIFE**
- Lease Term: [Calculate lease term including renewals if reasonably certain]
- Economic Life: [Assess remaining economic life at commencement]
- Major Part Analysis: [Apply 75% rule with ASC guidance]
- ASC 842 Analysis: [Consider near end of life exception]
- Conclusion: [Met/Not Met with reasoning]

**TEST 4 - PRESENT VALUE**
- Lease Payments: [List all payments to be included]
- Present Value Calculation: [Calculate PV using discount rate]
- Fair Value: [Asset fair value or estimate]
- Substantially All Analysis: [Apply 90% rule with ASC guidance]
- Conclusion: [Met/Not Met with reasoning]

**TEST 5 - ALTERNATIVE USE**
- Asset Specialization: [Analyze asset characteristics]
- Alternative Use Assessment: [Consider lessor's ability to redeploy]
- ASC 842 Analysis: [Apply specialized asset criteria]
- Conclusion: [Met/Not Met with reasoning]

**FINAL CLASSIFICATION**
- Tests Met: [List which tests are satisfied]
- Classification: [FINANCE LEASE or OPERATING LEASE]
- Primary Rationale: [Key factors driving classification]
- ASC 842 Citations: [Relevant paragraph references]

**PROFESSIONAL JUDGMENT CONSIDERATIONS**
- [Any borderline areas requiring judgment]
- [Risk factors or sensitivities]
- [Documentation recommendations]

Use the provided ASC 842 guidance to support your analysis with specific paragraph citations."""

    @staticmethod
    def get_memo_system_prompt() -> str:
        """System prompt for professional memorandum generation"""
        return """You are a senior technical accounting professional preparing a lease classification memorandum for company management and auditors.

MEMORANDUM REQUIREMENTS:
- Professional tone suitable for audit documentation
- Clear executive summary with definitive conclusion
- Systematic analysis of all classification tests
- Specific ASC 842 paragraph citations for support
- Contract evidence integration throughout analysis
- Risk assessments and recommendations

MEMO STRUCTURE:
1. Header: LEASE ACCOUNTING MEMORANDUM
2. Executive Summary (classification conclusion)
3. Lease Overview (key terms and facts)  
4. Classification Analysis (5 tests with conclusions)
5. Supporting Calculations (if applicable)
6. Professional Recommendations
7. ASC 842 References

TECHNICAL STANDARDS:
- Follow ASC 842 paragraph citation format (842-XX-XX-X)
- Quote specific contract language as evidence
- Provide clear audit trail for classification decision
- Address any areas of judgment or uncertainty
- Ensure memo supports year-end financial statement assertions"""

    @staticmethod
    def get_memo_user_prompt(analysis: ASC842Analysis, lease_data: LeaseClassificationData, rag_context: str) -> str:
        """User prompt for memo generation"""
        return f"""Generate a professional lease classification memorandum based on this analysis:

=== CLASSIFICATION ANALYSIS ===
{analysis.lease_classification}

=== LEASE DATA ===
Asset Type: {lease_data.asset_type}
Term: {lease_data.lease_term_months} months
Annual Payment: ${lease_data.annual_lease_payment:,.2f}

{rag_context}

=== MEMORANDUM TO GENERATE ===

{ASC842StepPrompts.MEMO_HEADER}

**TO:** Chief Accounting Officer  
**FROM:** Technical Accounting Team  
**DATE:** [Current Date]  
**RE:** ASC 842 Lease Classification Analysis - {lease_data.asset_type} Lease

## EXECUTIVE SUMMARY

**Lease Classification:** [FINANCE LEASE or OPERATING LEASE]

**Primary Basis:** [Key classification test(s) that drove conclusion]

**Financial Impact:** [High-level description of accounting treatment]

## LEASE OVERVIEW

**Asset Description:** [Describe underlying asset]
**Lease Term:** [Detail lease term including options]
**Payment Structure:** [Describe payment terms]
**Key Provisions:** [Highlight material lease provisions]

## CLASSIFICATION ANALYSIS

### Test 1: Ownership Transfer
[Analysis and conclusion]

### Test 2: Purchase Option  
[Analysis and conclusion]

### Test 3: Lease Term vs Economic Life
[Analysis and conclusion with calculations if applicable]

### Test 4: Present Value Test
[Analysis with PV calculations if applicable]

### Test 5: Alternative Use
[Analysis and conclusion]

## ACCOUNTING TREATMENT

**Initial Recognition:** [Describe accounting at commencement]
**Subsequent Measurement:** [Describe ongoing accounting]
**Financial Statement Impact:** [Summarize balance sheet and P&L effects]

## PROFESSIONAL RECOMMENDATIONS

1. [Documentation recommendations]
2. [Any ongoing monitoring requirements] 
3. [Disclosure considerations]

## ASC 842 REFERENCES

[List key ASC 842 paragraphs relied upon]

---
*This memorandum documents the technical accounting analysis supporting the lease classification in accordance with ASC 842.*

Generate a comprehensive, professional memorandum following this structure with specific details from the analysis."""