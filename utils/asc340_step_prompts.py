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
        contract_types = getattr(contract_data, 'contract_types_in_scope', []) if contract_data else []
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
Contract Types in Scope: {', '.join(contract_types) if contract_types else 'General contract costs'}
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

**CRITICAL:** Your analysis must establish a policy framework for {company_name}, not analyze a single transaction. Focus on creating consistent application principles that accounting staff can follow across all similar arrangements."""

    @staticmethod
    def _get_step_instructions(step_number: int) -> str:
        """Get specific instructions for each step"""
        instructions = {
            1: """**STEP 1: SCOPE ASSESSMENT**
Your task is to establish the scope of ASC 340-40 application for the Company's contracts.

ANALYSIS REQUIREMENTS:
1. **Contract Types Assessment:** Determine which types of customer contracts fall within ASC 340-40 scope
2. **Cost Categories Identification:** Identify the categories of costs that may be subject to ASC 340-40
3. **Scope Boundaries:** Define what is included vs. excluded from the policy scope
4. **Other Standards Interaction:** Identify any costs that should be accounted for under other standards

Focus on establishing clear scope boundaries that can be consistently applied across all relevant contracts.""",

            2: """**STEP 2: COST CLASSIFICATION**
Your task is to establish the classification framework for contract costs under ASC 340-40.

ANALYSIS REQUIREMENTS:
1. **Incremental Costs Framework:** Define criteria for identifying incremental costs of obtaining contracts
2. **Fulfillment Costs Framework:** Establish the three-criteria test for capitalizing fulfillment costs
3. **Expense Recognition Criteria:** Define when costs should be immediately expensed
4. **Practical Expedient Application:** Determine approach for the one-year practical expedient

Focus on creating clear, operational definitions that accounting staff can consistently apply.""",

            3: """**STEP 3: MEASUREMENT & AMORTIZATION POLICY**
Your task is to establish the measurement and amortization policy framework.

ANALYSIS REQUIREMENTS:
1. **Initial Measurement:** Define how capitalized contract costs will be initially measured
2. **Amortization Method:** Establish the systematic amortization approach
3. **Amortization Period:** Define how to determine the appropriate amortization period
4. **Impairment Testing:** Establish the impairment assessment process and timing

Focus on establishing systematic, defensible approaches that ensure consistent application.""",

            4: """**STEP 4: ILLUSTRATIVE FINANCIAL IMPACT**
Your task is to provide illustrative examples of the policy's financial impact using placeholder amounts.

ANALYSIS REQUIREMENTS:
1. **Journal Entry Examples:** Provide template journal entries for capitalization and amortization using a placeholder amount (e.g., $10,000)
2. **Financial Statement Presentation:** Describe balance sheet and income statement presentation
3. **Disclosure Requirements:** Summarize key disclosure requirements
4. **Implementation Timeline:** Outline key implementation considerations

**IMPORTANT:** Use placeholder amounts (e.g., $10,000) for all journal entries and include a disclaimer that entries are for illustrative purposes only. Focus on demonstrating the policy methodology, not calculating specific amounts."""
        }
        return instructions.get(step_number, "")

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