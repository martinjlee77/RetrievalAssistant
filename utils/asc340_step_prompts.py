"""
ASC 340-40 Contract Costs prompt templates following the proven ASC 606 architecture.
Implements 4-step framework for accounting policy documentation.
"""

import json
from typing import Dict, List, Any, Optional


class ASC340StepPrompts:
    """
    ASC 340-40 Contract Costs prompt templates following the proven ASC 606 architecture.
    Implements 4-step framework for accounting policy documentation.
    """

    @staticmethod
    def get_step_info() -> dict:
        """Returns information about each ASC 340-40 step"""
        return {
            1: {"title": "Scope Assessment", "primary_guidance": "ASC 340-40-15-2 through 15-3"},
            2: {"title": "Cost Classification", "primary_guidance": "ASC 340-40-25-1 through 25-8"},
            3: {"title": "Measurement & Amortization Policy", "primary_guidance": "ASC 340-40-35-1 through 35-6"},
            4: {"title": "Illustrative Financial Impact", "primary_guidance": "ASC 340-40-50-1 through 50-4"}
        }

    @staticmethod
    def get_system_prompt() -> str:
        """
        Core system prompt for ASC 340-40 contract costs policy analysis.
        Defines AI persona and universal rules.
        """
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 340-40 Contract Costs. Your analysis must be audit-ready, understandable, precise, and focused on accounting policy documentation.

<UNIVERSAL_RULES>
1. **JSON Output Only:** You MUST return your response as a single, well-formed JSON object. Do not add any text or explanations before or after the JSON.
2. **Knowledge Hierarchy:** Your analysis MUST be based on the following hierarchy of sources, in order of priority:
   a. **Contract Text:** The specific terms from the `<CONTRACT_TEXT>` are the primary evidence.
   b. **Authoritative Guidance:** The retrieved guidance from `<AUTHORITATIVE_CONTEXT>` (e.g., ASC 340-40) is the primary basis for your conclusions.
   c. **Interpretative Guidance:** Retrieved guidance from other sources (e.g., EY) should be used to support your analysis.
3. **Evidence Formatting:** Every quote in the `evidence_quotes` array MUST include the source document name, formatted as: 'Quote text... (Source: [Document Name])'.
4. **Policy Focus:** This analysis is for accounting policy documentation, not transaction-level analysis. Focus on establishing consistent application principles.
</UNIVERSAL_RULES>"""

    @staticmethod
    def get_user_prompt_for_step(step_number: int, contract_text: str, rag_context: str, contract_data=None) -> str:
        """
        Builds the dynamic, task-specific user prompt for ASC 340-40 step analysis.
        """
        step_info = ASC340StepPrompts.get_step_info()[step_number]
        step_schema = ASC340StepPrompts._get_schema_for_step(step_number)
        
        # Build context information
        company_name = getattr(contract_data, 'company_name', 'the Company') if contract_data else 'the Company'
        # contract_types_in_scope now contains cost categories
        cost_categories = getattr(contract_data, 'contract_types_in_scope', []) if contract_data else []
        cost_type = getattr(contract_data, 'cost_type', 'Incremental Cost of Obtaining') if contract_data else 'Incremental Cost of Obtaining'
        recovery_probable = getattr(contract_data, 'recovery_probable', True) if contract_data else True
        standard_amortization_period = getattr(contract_data, 'standard_amortization_period', 36) if contract_data else 36
        practical_expedient = getattr(contract_data, 'practical_expedient', False) if contract_data else False
        
        # Step-specific instructions
        step_instructions = ASC340StepPrompts._get_step_instructions(step_number)
        
        return f"""### ASC 340-40 STEP {step_number}: {step_info['title']} ###

<CONTRACT_TEXT>
{contract_text}
</CONTRACT_TEXT>

<AUTHORITATIVE_CONTEXT>
{rag_context}
</AUTHORITATIVE_CONTEXT>

<ANALYSIS_CONTEXT>
Company: {company_name}
Cost Categories in Scope: {', '.join(cost_categories) if cost_categories else 'General contract costs'}
Cost Type Focus: {cost_type}
Recovery Probable: {recovery_probable}
Standard Amortization Period: {standard_amortization_period} months
Practical Expedient Applied: {practical_expedient}
Primary Guidance: {step_info['primary_guidance']}
</ANALYSIS_CONTEXT>

### SPECIFIC INSTRUCTIONS ###
{step_instructions}

### REQUIRED OUTPUT FORMAT ###
You must return a JSON object with this exact structure:
{step_schema}

### CRITICAL_REQUIREMENTS ###
**YOUR ANALYSIS MUST INCLUDE:**

a. **Evidence:** Direct quotes from the <CONTRACT_TEXT> above. You MUST quote specific language, rates, amounts, definitions, and terms from the uploaded document.

b. **Specific References:** You MUST reference actual percentages (like "5% commission rate"), dollar amounts, timing provisions, and defined terms found in the contract text.

c. **Document Grounding:** Every policy recommendation must be tied to specific contract language. You cannot provide generic advice.

d. **Concrete Examples:** Use the actual terms from the contract (commission rates, TCV definitions, eligibility criteria) in your analysis.

**MANDATORY:** If the contract contains specific rates, amounts, or definitions, you MUST quote them verbatim and build your entire analysis around these actual terms. Generic or hypothetical examples are not acceptable.

**FAILURE TO FOLLOW:** Any response that doesn't quote specific contract terms or uses generic examples instead of actual document content will be rejected."""

    @staticmethod
    def _get_step_instructions(step_number: int) -> str:
        """Get specific instructions for each step"""
        instructions = {
            1: """**MANDATORY IAC FRAMEWORK - STEP 1: SCOPE ASSESSMENT**

You MUST use the Issue-Analysis-Conclusion (IAC) framework for EVERY cost category analysis.

**FOR EACH COST CATEGORY IN THE CONTRACT:**

**ISSUE:** What specific cost is described in the contract?
- Quote EXACT language: rates, amounts, calculation methods, terms
- Example: "The contract states '[EXACT QUOTE FROM CONTRACT]'"
- NO generic examples - use ACTUAL contract language only

**ANALYSIS:** How does this specific contract term apply to ASC 340-40 scope?
- Connect the EXACT contract language to ASC 340-40-15 requirements
- Reference the specific rates/amounts from the contract in your analysis
- Use authoritative guidance to evaluate the specific terms

**CONCLUSION:** Does this specific cost qualify for ASC 340-40?
- State definitive determination based on actual contract terms
- Reference the specific amounts/rates that drive the conclusion
- Establish clear policy boundaries using actual contract language

**ABSOLUTE REQUIREMENT:** Every sentence must reference specific contract terms. Generic industry analysis will be rejected.

**ENFORCEMENT:** If you provide generic analysis without quoting actual contract terms, the analysis will be deemed inadequate.</CRITICAL_INSTRUCTION>""",

            2: """**MANDATORY IAC FRAMEWORK - STEP 2: COST CLASSIFICATION**

You MUST use the Issue-Analysis-Conclusion (IAC) framework for EVERY cost type evaluation.

**FOR EACH COST TYPE IN THE CONTRACT:**

**ISSUE:** What is the specific cost structure described in the contract?
- Quote EXACT commission rates, payment triggers, calculation methods
- Example: "The contract specifies '[EXACT QUOTE FROM CONTRACT]'"
- Reference specific percentages, thresholds, eligibility criteria from the document

**ANALYSIS:** How does this specific cost structure meet ASC 340-40 classification criteria?
- Apply ASC 340-40-25 tests to the ACTUAL contract terms
- Connect specific contract language to incremental vs. fulfillment cost criteria
- Use authoritative guidance to evaluate the specific terms and conditions

**CONCLUSION:** How should this specific cost be classified under ASC 340-40?
- State definitive classification based on actual contract terms
- Reference the specific rates/conditions that drive the classification
- Establish clear policy framework using actual contract structure

**ABSOLUTE REQUIREMENT:** Every classification must be based on quoted contract terms. Generic cost classification guidance without specific contract evidence is inadequate.

**ENFORCEMENT:** Analysis must reference actual commission rates, payment conditions, and eligibility criteria from the contract.</CRITICAL_INSTRUCTION>""",

            3: """**MANDATORY IAC FRAMEWORK - STEP 3: MEASUREMENT & AMORTIZATION POLICY**

You MUST use the Issue-Analysis-Conclusion (IAC) framework for policy development.

**FOR EACH MEASUREMENT AND AMORTIZATION DECISION:**

**ISSUE:** What specific contract terms affect measurement and amortization?
- Quote EXACT contract language about renewal periods, customer terms, contract duration
- Example: "The contract states '[EXACT QUOTE FROM CONTRACT]'"
- Reference specific commission amounts, timing provisions, renewal clauses

**ANALYSIS:** How do these specific contract terms impact ASC 340-40 measurement and amortization?
- Apply ASC 340-40-35 requirements to the ACTUAL contract terms
- Connect specific contract provisions to amortization period determination
- Use authoritative guidance to evaluate the specific business model described

**CONCLUSION:** What measurement and amortization policy should be established?
- State definitive policy framework based on actual contract terms
- Reference the specific contract provisions that drive the policy
- Establish clear amortization approach using actual business model

**ABSOLUTE REQUIREMENT:** Every policy decision must be grounded in quoted contract terms. Generic amortization guidance without specific contract evidence is inadequate.

**ENFORCEMENT:** Analysis must reference actual contract durations, renewal terms, and commission structures from the document.</CRITICAL_INSTRUCTION>""",

            4: """**MANDATORY IAC FRAMEWORK - STEP 4: ILLUSTRATIVE FINANCIAL IMPACT**

You MUST use the Issue-Analysis-Conclusion (IAC) framework for financial impact analysis.

**FOR EACH FINANCIAL IMPACT SCENARIO:**

**ISSUE:** What specific contract terms drive the financial impact?
- Quote EXACT commission rates, payment terms, calculation methods from contract
- Example: "Based on the contract rate of '[EXACT QUOTE FROM CONTRACT]'"
- Reference specific amounts, percentages, thresholds that affect accounting

**ANALYSIS:** How do these specific contract terms translate to financial impact under ASC 340-40?
- Use ACTUAL commission rates and structures from the contract in calculations
- Apply the specific business model described in the document to journal entries
- Connect contract terms to balance sheet and income statement presentation

**CONCLUSION:** What is the illustrative financial impact using actual contract terms?
- Present journal entries using the specific commission structure from the contract
- Reference the actual rates and amounts that drive the accounting treatment
- Demonstrate financial statement impact based on the actual business model

**ABSOLUTE REQUIREMENT:** Every financial example must use quoted contract terms. Generic illustrative amounts without contract-specific rates and structures are inadequate.

**ENFORCEMENT:** Journal entries must reflect the actual commission rates, payment triggers, and business model described in the contract.</CRITICAL_INSTRUCTION>"""
        }
        return instructions.get(step_number, "")

    @staticmethod
    def get_memo_generation_system_prompt() -> str:
        """System prompt for generating professional ASC 340-40 policy memorandums"""
        return """You are a senior technical accounting specialist generating professional accounting policy memorandums for ASC 340-40 Contract Costs.

Your task is to synthesize the step analysis results into a comprehensive, Big 4-quality accounting policy memorandum that establishes consistent application principles for the organization.

CRITICAL REQUIREMENTS:
1. **Professional Format**: Generate a formal accounting policy memorandum suitable for technical accounting teams
2. **Evidence Integration**: Include specific contract terms, rates, and conditions from the source documents
3. **Policy Framework**: Create actionable policy guidance that staff can consistently apply
4. **Authoritative Support**: Reference ASC 340-40 guidance and interpretative sources appropriately

OUTPUT FORMAT: Return plain text markdown suitable for professional presentation."""

    @staticmethod
    def get_memo_generation_user_prompt(analysis, rag_context: str) -> str:
        """User prompt for generating complete ASC 340-40 policy memorandum"""
        
        # Extract contract data
        contract_data = analysis.contract_data
        company_name = contract_data.company_name
        analysis_title = contract_data.analysis_title
        policy_date = contract_data.policy_effective_date.strftime("%B %d, %Y")
        
        # Extract step results
        step1 = analysis.step1_scope_assessment
        step2 = analysis.step2_cost_classification  
        step3 = analysis.step3_measurement_policy
        step4 = analysis.step4_illustrative_impact
        
        return f"""Generate a comprehensive ASC 340-40 accounting policy memorandum based on the completed step analysis.

### MEMO CONTEXT ###
Company: {company_name}
Policy Title: {analysis_title}
Effective Date: {policy_date}
Audience: Technical Accounting Team

### ANALYSIS RESULTS ###

**STEP 1 - SCOPE ASSESSMENT:**
{step1}

**STEP 2 - COST CLASSIFICATION:**
{step2}

**STEP 3 - MEASUREMENT & AMORTIZATION POLICY:**
{step3}

**STEP 4 - ILLUSTRATIVE FINANCIAL IMPACT:**
{step4}

### AUTHORITATIVE CONTEXT ###
{rag_context}

### REQUIRED OUTPUT FORMAT ###

Generate a professional accounting policy memorandum with the following structure:

# ACCOUNTING POLICY MEMORANDUM

**TO:** Chief Accounting Officer  
**FROM:** Technical Accounting Team  
**DATE:** {policy_date}  
**RE:** {analysis_title}

## EXECUTIVE SUMMARY
[Concise overview of policy framework and key determinations]

## 1. SCOPE ASSESSMENT
[Policy scope based on Step 1 analysis with specific contract terms]

## 2. COST CLASSIFICATION FRAMEWORK  
[Classification criteria based on Step 2 analysis with contract evidence]

## 3. MEASUREMENT & AMORTIZATION POLICY
[Policy framework based on Step 3 analysis with specific terms]

## 4. ILLUSTRATIVE FINANCIAL IMPACT
[Examples based on Step 4 analysis using actual contract structure]

## CONCLUSION
[Summary of policy framework and implementation guidance]

**CRITICAL:** Ensure the memorandum includes specific contract terms, rates, and conditions from the underlying analysis. Reference actual percentages, amounts, and contractual language throughout the policy framework."""

    @staticmethod
    def _get_schema_for_step(step_number: int) -> str:
        """Get JSON schema for each step"""
        schemas = {
            1: """{
  "step1_analysis": {
    "scope_determination": [
      {
        "cost_category": "Name of cost category (e.g., 'Sales Commissions', 'Contract Setup Costs')",
        "in_scope_assessment": "Yes / No / Conditional",
        "rationale": "Clear explanation based on ASC 340-40 scope requirements",
        "other_standards_consideration": "Note any other GAAP standards that may apply"
      }
    ],
    "policy_boundaries": {
      "included_contract_types": "List the types of customer contracts included in scope",
      "excluded_items": "List items explicitly excluded from the policy",
      "materiality_considerations": "Note any materiality thresholds or considerations"
    },
    "step1_conclusion": "Clear summary of scope determination for the Company's policy"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-15-2)"
  ]
}""",

            2: """{
  "step2_analysis": {
    "incremental_costs_framework": {
      "definition": "Clear definition of incremental costs for the Company",
      "identification_criteria": "Specific criteria for identifying incremental costs",
      "common_examples": "Examples of costs that typically qualify as incremental",
      "common_exclusions": "Examples of costs that typically do NOT qualify"
    },
    "fulfillment_costs_framework": {
      "three_criteria_application": "How the Company will apply the three criteria in ASC 340-40-25-5",
      "direct_relationship_test": "How to assess if costs relate directly to a contract",
      "resource_enhancement_test": "How to assess if costs generate/enhance resources",
      "recoverability_test": "How to assess cost recoverability"
    },
    "practical_expedient_policy": {
      "one_year_expedient": "The Company's approach to the one-year practical expedient",
      "application_criteria": "When the expedient will be applied"
    },
    "step2_conclusion": "Summary of the Company's cost classification policy framework"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-25-1)"
  ]
}""",

            3: """{
  "step3_analysis": {
    "measurement_policy": {
      "initial_measurement": "How the Company will initially measure capitalized contract costs",
      "cost_components": "What components are included in the capitalized amount"
    },
    "amortization_framework": {
      "amortization_method": "The systematic method the Company will use (e.g., straight-line, proportional)",
      "amortization_period_determination": "How the Company will determine amortization periods",
      "contract_renewal_consideration": "How renewals affect amortization periods"
    },
    "impairment_policy": {
      "impairment_assessment_timing": "When the Company will assess for impairment",
      "impairment_calculation_method": "How impairment will be calculated per ASC 340-40-35-3"
    },
    "step3_conclusion": "Summary of the Company's measurement and amortization policy"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-35-1)"
  ]
}""",

            4: """{
  "step4_analysis": {
    "illustrative_examples": [
      {
        "scenario_description": "Description of the illustrative scenario",
        "journal_entries": [
          {
            "description": "Journal entry description",
            "debit_account": "Account name",
            "debit_amount": "Amount (use placeholders like $10,000)",
            "credit_account": "Account name", 
            "credit_amount": "Amount (use placeholders like $10,000)"
          }
        ]
      }
    ],
    "financial_statement_presentation": {
      "balance_sheet_presentation": "How contract costs will appear on the balance sheet",
      "income_statement_presentation": "How amortization will appear on the income statement"
    },
    "disclosure_requirements": {
      "required_disclosures": "Key disclosure requirements under ASC 340-40",
      "policy_disclosure": "Accounting policy disclosure requirements"
    },
    "implementation_considerations": {
      "system_requirements": "Key system or process considerations for implementation",
      "timeline_considerations": "Implementation timeline factors"
    },
    "step4_conclusion": "Summary of financial impact and implementation approach"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-50-1)"
  ]
}"""
        }
        return schemas.get(step_number, "{}")

    @staticmethod
    def _get_schema_for_step(step_number: int) -> str:
        """Get JSON schema for each step"""
        schemas = {
            1: """{
  "step1_analysis": {
    "scope_determination": [
      {
        "cost_category": "Name of cost category (e.g., 'Sales Commissions', 'Contract Setup Costs')",
        "in_scope_assessment": "Yes / No / Conditional",
        "rationale": "Clear explanation based on ASC 340-40 scope requirements",
        "other_standards_consideration": "Note any other GAAP standards that may apply"
      }
    ],
    "policy_boundaries": {
      "included_contract_types": "List the types of customer contracts included in scope",
      "excluded_items": "List items explicitly excluded from the policy",
      "materiality_considerations": "Note any materiality thresholds or considerations"
    },
    "step1_conclusion": "Clear summary of scope determination for the Company's policy"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-15-2)"
  ]
}""",

            2: """{
  "step2_analysis": {
    "incremental_costs_framework": {
      "definition": "Clear definition of incremental costs for the Company",
      "identification_criteria": "Specific criteria for identifying incremental costs",
      "common_examples": "Examples of costs that typically qualify as incremental",
      "common_exclusions": "Examples of costs that typically do NOT qualify"
    },
    "fulfillment_costs_framework": {
      "three_criteria_application": "How the Company will apply the three criteria in ASC 340-40-25-5",
      "direct_relationship_test": "How to assess if costs relate directly to a contract",
      "resource_enhancement_test": "How to assess if costs generate/enhance resources",
      "recoverability_test": "How to assess cost recoverability"
    },
    "practical_expedient_policy": {
      "one_year_expedient": "The Company's approach to the one-year practical expedient",
      "application_criteria": "When the expedient will be applied"
    },
    "step2_conclusion": "Summary of the Company's cost classification policy framework"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-25-1)"
  ]
}""",

            3: """{
  "step3_analysis": {
    "measurement_policy": {
      "initial_measurement": "How the Company will initially measure capitalized contract costs",
      "cost_components": "What components are included in the capitalized amount"
    },
    "amortization_framework": {
      "amortization_method": "The systematic method the Company will use (e.g., straight-line, proportional)",
      "amortization_period_determination": "How the Company will determine amortization periods",
      "contract_renewal_consideration": "How renewals affect amortization periods"
    },
    "impairment_policy": {
      "impairment_assessment_timing": "When the Company will assess for impairment",
      "impairment_calculation_method": "How impairment will be calculated per ASC 340-40-35-3",
      "recovery_probability": "No reversal of impairment losses per ASC 340-40-35-6"
    },
    "step3_conclusion": "Summary of the Company's measurement and amortization policy"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-35-1)"
  ]
}""",

            4: """{
  "step4_analysis": {
    "journal_entry_examples": [
      {
        "scenario": "Example scenario (e.g., 'Capitalization of sales commission')",
        "debit_account": "Account to be debited",
        "credit_account": "Account to be credited",
        "description": "Clear description of the entry"
      }
    ],
    "financial_statement_presentation": {
      "balance_sheet_presentation": "How capitalized costs will be presented on balance sheet",
      "income_statement_presentation": "How amortization will be presented on income statement",
      "separate_presentation_requirement": "Note requirement to present separately from contract assets/liabilities"
    },
    "disclosure_requirements": {
      "required_disclosures": "Summary of key disclosure requirements per ASC 340-40-50",
      "quantitative_disclosures": "Required quantitative information",
      "qualitative_disclosures": "Required qualitative information"
    },
    "step4_conclusion": "Summary of financial impact and implementation considerations"
  },
  "evidence_quotes": [
    "Direct quote from authoritative guidance... (Source: ASC 340-40-50-1)"
  ]
}"""
        }
        return schemas.get(step_number, "{}")

    @staticmethod
    def get_memo_generation_system_prompt() -> str:
        """System prompt for generating complete ASC 340-40 policy memorandum"""
        return """You are an expert technical accounting manager preparing an accounting policy memorandum for ASC 340-40 Contract Costs. Your memo must be professional, comprehensive, and suitable for audit file documentation.

<MEMO_REQUIREMENTS>
1. **Professional Format:** Use proper business memo format with clear sections
2. **Policy Focus:** This is a policy memorandum, not transaction analysis
3. **Implementation Guidance:** Include practical implementation considerations
4. **Audit Readiness:** Ensure all conclusions are well-supported and defensible
</MEMO_REQUIREMENTS>"""

    @staticmethod
    def get_memo_generation_user_prompt(analysis, rag_context: str) -> str:
        """User prompt for generating complete ASC 340-40 policy memorandum"""
        company_name = analysis.contract_data.company_name
        analysis_title = analysis.contract_data.analysis_title
        
        return f"""Generate a comprehensive ASC 340-40 Contract Costs Accounting Policy Memorandum based on the analysis provided.

<ANALYSIS_DATA>
Step 1 - Scope Assessment: {analysis.step1_scope_assessment}
Step 2 - Cost Classification: {analysis.step2_cost_classification}
Step 3 - Measurement & Amortization: {analysis.step3_measurement_policy}
Step 4 - Financial Impact: {analysis.step4_illustrative_impact}
</ANALYSIS_DATA>

<ADDITIONAL_CONTEXT>
{rag_context}
</ADDITIONAL_CONTEXT>

**MEMORANDUM STRUCTURE:**

**TO:** Chief Accounting Officer  
**FROM:** Technical Accounting Team  
**DATE:** [Current Date]  
**RE:** ASC 340-40 Contract Costs Accounting Policy - {analysis_title}

**1. EXECUTIVE SUMMARY**
Brief overview of the policy framework and key determinations.

**2. SCOPE ASSESSMENT**  
[Based on Step 1 analysis]

**3. COST CLASSIFICATION POLICY**  
[Based on Step 2 analysis]

**4. MEASUREMENT & AMORTIZATION POLICY**  
[Based on Step 3 analysis]

**5. FINANCIAL STATEMENT IMPACT & IMPLEMENTATION**  
[Based on Step 4 analysis]

**6. CONCLUSION**  
Summary of established policy framework.

Write the complete memorandum focusing on practical policy implementation for {company_name}."""

    @staticmethod
    def get_memo_generation_system_prompt() -> str:
        """System prompt for generating the complete ASC 340-40 policy memorandum"""
        return """You are an expert technical accountant specializing in ASC 340-40 Contract Costs. Generate a comprehensive accounting policy memorandum that combines the 4-step analysis into a cohesive professional document.

<MEMO_GENERATION_RULES>
1. **Professional Format:** Use formal business memorandum structure with proper headers and sections.
2. **Document-Specific Analysis:** Reference and analyze specific terms, rates, and conditions from the uploaded contract documents.
3. **Policy Focus:** This is an accounting policy memo, not transaction analysis. Focus on establishing consistent application principles.
4. **Evidence Integration:** Incorporate authoritative guidance citations to support policy positions.
5. **Practical Implementation:** Include specific guidance for accounting staff on how to apply the policy.
</MEMO_GENERATION_RULES>"""

    @staticmethod
    def get_memo_generation_user_prompt(analysis, rag_context: str) -> str:
        """User prompt for generating the complete ASC 340-40 policy memorandum"""
        
        # Extract contract data
        contract_data = analysis.contract_data
        company_name = getattr(contract_data, 'company_name', 'the Company')
        analysis_title = getattr(contract_data, 'analysis_title', 'Contract_Costs_Policy')
        
        # Extract step results
        step1 = analysis.step1_scope_assessment
        step2 = analysis.step2_cost_classification  
        step3 = analysis.step3_measurement_policy
        step4 = analysis.step4_illustrative_impact
        
        return f"""Generate a comprehensive ASC 340-40 accounting policy memorandum based on the following analysis:

<COMPANY_CONTEXT>
Company: {company_name}
Policy Title: {analysis_title}
</COMPANY_CONTEXT>

<ANALYSIS_RESULTS>
Step 1 - Scope Assessment:
{step1}

Step 2 - Cost Classification:
{step2}

Step 3 - Measurement & Amortization Policy:
{step3}

Step 4 - Illustrative Financial Impact:
{step4}
</ANALYSIS_RESULTS>

<AUTHORITATIVE_GUIDANCE>
{rag_context}
</AUTHORITATIVE_GUIDANCE>

Create a complete memorandum following this structure:

**TO:** Chief Accounting Officer  
**FROM:** Technical Accounting Team  
**DATE:** [Current Date]  
**RE:** ASC 340-40 Contract Costs Accounting Policy - {analysis_title}

**1. EXECUTIVE SUMMARY**
Brief overview of the policy framework and key determinations.

**2. SCOPE ASSESSMENT**  
[Based on Step 1 analysis]

**3. COST CLASSIFICATION POLICY**  
[Based on Step 2 analysis]

**4. MEASUREMENT & AMORTIZATION POLICY**  
[Based on Step 3 analysis]

**5. FINANCIAL STATEMENT IMPACT & IMPLEMENTATION**  
[Based on Step 4 analysis]

**6. CONCLUSION**  
Summary of established policy framework.

Focus on practical policy implementation for {company_name} and reference specific document terms analyzed."""