"""
Comprehensive ASC 606 Analysis Framework
Integrates detailed question framework with hybrid RAG guidance
"""

def get_comprehensive_analysis_prompt(contract_evidence: dict, guidance_sections: dict, contract_data: dict, contract_text: str) -> str:
    """
    Generate comprehensive analysis prompt that systematically addresses all questions
    in the contract review framework
    """
    
    return f"""
You are a "Big 4" accounting advisor with deep expertise in ASC 606. Your task is to perform a comprehensive, forensic analysis that systematically addresses every aspect of the ASC 606 framework.

**CRITICAL INSTRUCTIONS:**

**BASELINE ANALYSIS:** You must address EVERY question in the comprehensive framework below. This is your minimum requirement and establishes the floor for analysis quality.

**EMERGENT ANALYSIS:** Your analysis is NOT limited to this framework. As a "Big 4" expert, you are expected to identify and analyze any other unique, unusual, or material issues present in the contract that are not covered by the standard questions. Use your expertise to spot novel accounting issues that require professional judgment.

**EXECUTION REQUIREMENTS:**
1. Address every question in the framework systematically
2. Provide detailed analysis with specific contract evidence
3. Use the two-stage citation approach: contract quotes + ASC 606 guidance
4. If any question is not applicable, explicitly state why with reasoning
5. Identify and analyze any unique contract provisions not covered by standard questions
6. Be thorough and methodical - this is an audit-ready analysis

**EXTRACTED CONTRACT EVIDENCE (Use these verbatim quotes):**
{format_contract_evidence(contract_evidence)}

**USER'S PRELIMINARY ASSESSMENT (Hypothesis to validate):**
```json
{format_user_assessment(contract_data)}
```

**COMPREHENSIVE ASC 606 ANALYSIS FRAMEWORK:**

**STEP 1: IDENTIFY THE CONTRACT**

**1.1 Definition of a contract - Address each of the 5 criteria:**
a) Have the parties approved the contract and are committed to perform their obligations?
b) Can the entity identify each party's rights regarding goods/services to be transferred?
c) Can the entity identify the payment terms for goods/services to be transferred?
d) Does the contract have commercial substance?
e) Is it probable that the entity will collect substantially all consideration?

**1.1.1 Contract enforceability and termination clauses:**
- Does the contract have a stated duration during which neither party has a right to cancel?

**1.2 Combining contracts:**
- Was the contract entered into at or near the same time as other contracts with the same customer?

**1.3 Contract modifications:**
- Has the contract been modified since it was entered into or commenced?

**STEP 2: IDENTIFY PERFORMANCE OBLIGATIONS**

**2.1 Identify promised goods/services:**
- What are the promised goods or services in the contract?

**2.1.1 Determine whether goods/services are distinct - Apply 2-step model:**
1. Is the good/service capable of being distinct?
2. Is the good/service distinct in the context of the contract?
   a. Evaluate whether multiple promised goods/services work together to deliver a combined output

**2.1.2 Promised goods/services that are not distinct:**
- If goods/services are not distinct, combine with other promised goods/services until a distinct bundle exists

**2.2 Principal versus agent analysis:**
- Is another party involved in providing goods or services to the customer?
- Does the entity control each specified good or service before transfer?

**2.3 Service-type warranties:**
- Could any promised services be considered warranties sold separately?

**2.4 Customer options:**
- Does the contract contain options for additional goods/services that provide material rights?

**STEP 3: DETERMINE THE TRANSACTION PRICE**

**3.0 Base transaction price:**
- Is there an amount of transaction price that is not variable?

**3.1 Variable consideration:**
- Is any consideration variable or uncertain?
- Apply expected value or most likely amount method

**3.1.2 Constraint on revenue recognized:**
- Evaluate likelihood of significant revenue reversal
- Quantify magnitude of possible revenue reversal

**3.3 Significant financing component:**
- Does timing of payments provide significant financing benefit?

**3.4 Noncash consideration:**
- Is the entity entitled to any noncash consideration?

**3.5 Consideration payable to customer:**
- Is there consideration payable to customer not in exchange for distinct goods/services?

**STEP 4: ALLOCATE THE TRANSACTION PRICE**

**4.0 Allocation of transaction price:**
- Are there multiple performance obligations?

**4.1 Allocating attributable variable consideration:**
- Is variable consideration attributable to specific performance obligations?

**4.2 Allocating a discount:**
- Does the contract contain a discount?

**4.3 Standalone selling price:**
- How was standalone selling price determined for each performance obligation?

**STEP 5: SATISFACTION OF PERFORMANCE OBLIGATIONS**

**5.0 Transfer of control:**
- Do performance obligations meet criteria for transfer of control over time?
  a) Customer simultaneously receives and consumes benefits
  b) Entity's performance creates/enhances asset customer controls
  c) No alternative use and enforceable right to payment

**5.1 Control transferred at point in time:**
- If not over time, when does control transfer at a point in time?

**5.6 Customer acceptance:**
- If contract contains acceptance provisions, when has control transferred?

**5.7 Revenue recognition pattern:**
- For over-time obligations, which measure of progress best depicts transfer of control?

**HYBRID RAG GUIDANCE LIBRARY:**

**Step 1 - Contract Identification:**
{format_guidance_sections({'contract_guidance': guidance_sections.get('contract_guidance', [])})}

**Step 2 - Performance Obligations:**
{format_guidance_sections({'obligations_guidance': guidance_sections.get('obligations_guidance', [])})}

**Step 3 - Transaction Price:**
{format_guidance_sections({'price_guidance': guidance_sections.get('price_guidance', [])})}

**Step 4 - Price Allocation:**
{format_guidance_sections({'allocation_guidance': guidance_sections.get('allocation_guidance', [])})}

**Step 5 - Revenue Recognition:**
{format_guidance_sections({'recognition_guidance': guidance_sections.get('recognition_guidance', [])})}

**CONTRACT DOCUMENT TEXT (For reference):**
{contract_text[:8000]}...

**REQUIRED JSON OUTPUT STRUCTURE:**
{{
    "contract_overview": {{
        "analysis_summary": "Executive summary of key findings",
        "complexity_assessment": "Simple/Moderate/Complex",
        "key_judgments": ["List of critical accounting judgments made"]
    }},
    "step1_contract_identification": {{
        "conclusion": "Clear conclusion on contract validity",
        "detailed_analysis": {{
            "parties_approved": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "rights_identified": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "payment_terms_identified": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "commercial_substance": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "collection_probable": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}}
        }},
        "contract_enforceability": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "contract_combinations": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "contract_modifications": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "additional_considerations": [
            {{
                "issue_identified": "Description of any unique, unusual, or material issue not covered by standard questions",
                "rationale": "Why this issue is significant and requires attention",
                "contractual_quote": "Relevant verbatim quote from the contract",
                "authoritative_citation": "Applicable ASC 606 guidance or principle"
            }}
        ]
    }},
    "step2_performance_obligations": {{
        "conclusion": "Summary of identified performance obligations",
        "promised_goods_services": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "distinct_analysis": {{
            "capable_of_being_distinct": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "distinct_in_context": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "combined_output_evaluation": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}}
        }},
        "principal_agent_analysis": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "warranties_analysis": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "customer_options": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "additional_considerations": [
            {{
                "issue_identified": "Description of any unique, unusual, or material issue not covered by standard questions",
                "rationale": "Why this issue is significant and requires attention",
                "contractual_quote": "Relevant verbatim quote from the contract",
                "authoritative_citation": "Applicable ASC 606 guidance or principle"
            }}
        ]
    }},
    "step3_transaction_price": {{
        "conclusion": "Summary of transaction price determination",
        "base_transaction_price": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "variable_consideration": {{
            "existence": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "estimation_method": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "constraint_analysis": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}}
        }},
        "financing_component": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "noncash_consideration": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "consideration_payable_to_customer": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "additional_considerations": [
            {{
                "issue_identified": "Description of any unique, unusual, or material issue not covered by standard questions",
                "rationale": "Why this issue is significant and requires attention",
                "contractual_quote": "Relevant verbatim quote from the contract",
                "authoritative_citation": "Applicable ASC 606 guidance or principle"
            }}
        ]
    }},
    "step4_price_allocation": {{
        "conclusion": "Summary of price allocation approach",
        "multiple_performance_obligations": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "variable_consideration_allocation": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "discount_allocation": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "standalone_selling_price": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "additional_considerations": [
            {{
                "issue_identified": "Description of any unique, unusual, or material issue not covered by standard questions",
                "rationale": "Why this issue is significant and requires attention",
                "contractual_quote": "Relevant verbatim quote from the contract",
                "authoritative_citation": "Applicable ASC 606 guidance or principle"
            }}
        ]
    }},
    "step5_revenue_recognition": {{
        "conclusion": "Summary of revenue recognition approach",
        "control_transfer_analysis": {{
            "over_time_criteria": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
            "point_in_time_analysis": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}}
        }},
        "customer_acceptance": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "recognition_pattern": {{"conclusion": "", "rationale": "", "contractual_quote": "", "authoritative_citation": ""}},
        "additional_considerations": [
            {{
                "issue_identified": "Description of any unique, unusual, or material issue not covered by standard questions",
                "rationale": "Why this issue is significant and requires attention",
                "contractual_quote": "Relevant verbatim quote from the contract",
                "authoritative_citation": "Applicable ASC 606 guidance or principle"
            }}
        ]
    }}
}}

**FINAL INSTRUCTIONS:**
1. Address every question in the framework systematically - this is your baseline requirement
2. For each step, populate the `additional_considerations` array with any unique, unusual, or material issues you identify that are not covered by the standard questions
3. If no additional considerations are identified for a step, return an empty array: `"additional_considerations": []`
4. Your expertise should shine through in identifying novel accounting issues that require professional judgment
5. Do not skip any elements - if not applicable, state why with reasoning

**REMEMBER:** The framework is your minimum standard, not your maximum capability. Use your expertise to identify issues that would concern a Big 4 audit partner.
"""

def format_contract_evidence(evidence: dict) -> str:
    """Format contract evidence for the prompt"""
    formatted = ""
    for step, quotes in evidence.items():
        formatted += f"\n**{step.upper()}:**\n"
        if quotes:
            for i, quote in enumerate(quotes, 1):
                formatted += f"{i}. \"{quote}\"\n"
        else:
            formatted += "No specific quotes extracted for this step.\n"
    return formatted

def format_user_assessment(contract_data) -> str:
    """Format user assessment data"""
    try:
        import json
        return json.dumps(contract_data.model_dump(), indent=2, default=str)
    except:
        return str(contract_data)

def format_guidance_sections(guidance_sections: dict) -> str:
    """Format guidance sections with source transparency"""
    formatted = ""
    for section_name, guidance_list in guidance_sections.items():
        formatted += f"\n**{section_name.upper()}:**\n"
        for i, guidance in enumerate(guidance_list, 1):
            source_type = guidance.get('source_type', 'unknown')
            source_indicator = "🏛️ [AUTHORITATIVE]" if source_type == 'authoritative' else "🏢 [INTERPRETATIVE]"
            formatted += f"{i}. {source_indicator} {guidance.get('text', '')} (Source: {guidance.get('source_file', 'unknown')})\n"
    return formatted