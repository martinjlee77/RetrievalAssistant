"""
Refactored ASC 606 prompt templates using System/User architecture for improved LLM adherence.
This approach separates the AI's core instructions (System Prompt) from the
dynamic task-specific instructions (User Prompt).
"""

import json
from typing import Dict, List, Any, Optional


class StepPrompts:
    """
    Refactored prompts using a modular, System/User architecture to improve LLM adherence.
    This approach separates the AI's core instructions (System Prompt) from the
    dynamic task-specific instructions (User Prompt).
    """

    @staticmethod
    def get_step_info() -> dict:
        """Returns information about each ASC 606 step. (No changes needed here)"""
        return {
            1: {"title": "Identify the Contract", "primary_guidance": "ASC 606-10-25-1 through 25-8"},
            2: {"title": "Identify Performance Obligations", "primary_guidance": "ASC 606-10-25-14 through 25-22"},
            3: {"title": "Determine the Transaction Price", "primary_guidance": "ASC 606-10-32-2 through 32-27"},
            4: {"title": "Allocate the Transaction Price", "primary_guidance": "ASC 606-10-32-28 through 32-41"},
            5: {"title": "Recognize Revenue", "primary_guidance": "ASC 606-10-25-23 through 25-37"}
        }

    # --- NEW: Core Prompt Architecture ---

    @staticmethod
    def get_system_prompt() -> str:
        """
        Defines the AI's core persona, universal rules, and mandatory output format.
        This is static and sent with every step-analysis call.
        """
        return """You are an expert technical accountant specializing in ASC 606. Your analysis must be audit-ready, understandable, precise, and objective. You must follow all instructions and formatting rules precisely.

<OUTPUT_FORMAT_RULE>
You MUST return your response as a single, well-formed JSON object. Do not add any text, explanations, or markdown formatting before or after the JSON object. Your entire response must be only the JSON.

The JSON object MUST contain these top-level keys: "executive_conclusion", the relevant "step_X_analysis" block, "professional_judgments", and "analysis_points".
</OUTPUT_FORMAT_RULE>

<EVIDENCE_RULE>
Every quote from the contract provided in the `evidence_quotes` array MUST include the source document name, formatted exactly as: 'Quote text... (Source: [Document Name])'.
</EVIDENCE_RULE>

<ANALYSIS_RULE>
Your analysis must be thorough. Weave in specific citations to support your conclusions.
- When citing the official standard, reference its **authoritative** source (e.g., ASC 606-10-25-1).
- Where helpful, you may also cite **interpretative** guidance (e.g., from an EY source) to add practical context.
</ANALYSIS_RULE>
"""
   
    @staticmethod
    def get_user_prompt_for_step(step_number: int, contract_text: str, rag_context: str, contract_data=None, debug_config=None) -> str:
        """
        Builds the dynamic, task-specific user prompt for a single step analysis.
        This is the new replacement for the old get_step_specific_analysis_prompt.
        """
        step_info = StepPrompts.get_step_info()[step_number]
        step_schema_name = f"step{step_number}_analysis"
        step_schema_definition = StepPrompts._get_schema_for_step(step_number)
        critical_rules = StepPrompts._get_critical_rules_for_step(step_number, contract_text)

        # Assemble the concise user prompt
        prompt_parts = [
            f"Your task is to analyze a contract for Step {step_number}: {step_info['title']}.",
            f"PRIMARY GUIDANCE FOR THIS STEP: {step_info['primary_guidance']}",
            f"<AUTHORITATIVE_CONTEXT>\n{rag_context}\n</AUTHORITATIVE_CONTEXT>",
            f"<CONTRACT_TEXT>\n{contract_text}\n</CONTRACT_TEXT>",
            f"<CONTRACT_DATA>\nCustomer: {getattr(contract_data, 'customer_name', 'N/A')}\nAnalysis Focus: {getattr(contract_data, 'key_focus_areas', 'General ASC 606 compliance')}\n</CONTRACT_DATA>",
            "---",
            "CRITICAL TASK: Analyze the contract based on the context provided. Populate the JSON structure below with your complete analysis. Adhere to all rules.",
            "```json",
            "{",
            f'  "executive_conclusion": "A clear, one-to-three sentence conclusion for this entire step. This is the \'bottom line\'.",',
            f'  "{step_schema_name}": {step_schema_definition},',
            '  "professional_judgments": [ "A list of strings describing conclusions that required significant professional judgment for this step. If none, return an empty list []." ],',
            '  "analysis_points": [ { "topic_title": "...", "analysis_text": "...", "evidence_quotes": ["..."] } ]',
            "}",
            "```",
            """<ANALYSIS_STRUCTURE_RULE>
For each `analysis_point`, your `analysis_text` MUST be a professional, narrative paragraph that follows this 3-part "IAC" structure:
1.  **Issue:** Clearly state the accounting question being addressed (e.g., "Is the contract enforceable?", "Are the services distinct?").
2.  **Analysis:** This is the most critical part. Your analysis must be robust.
    - First, identify and quote the most relevant terms or clauses from the provided contract evidence.
    - Next, cite the specific, applicable guidance (e.g., ASC 606-10-25-21).
    - **Crucially, you must then explicitly connect the contract language to the accounting guidance.** Explain *how* the specific words in the contract cause the arrangement to either meet or fail the criteria in the guidance. Do not just state the facts and the rule; explain the reasoning that links them.
3.  **Conclusion:** Provide a definitive answer to the issue raised.

Weave these three parts into a seamless, easy-to-understand narrative. Follow the depth and pattern of the example below.

**META-EXAMPLE OF STRUCTURE (Follow this structural pattern and depth, but use the actual facts from the contract):**
"The primary accounting question is [state the specific issue, e.g., 'whether the professional services are distinct from the main product'] (Issue). The contract includes specific language stating, '[Quote the relevant key phrase or sentence from the contract source text]'. The authoritative guidance in ASC XXX-XX-XX-X requires that [paraphrase the relevant accounting rule or criteria]. In this case, the quoted contract language directly impacts this assessment because [explain the reasoning that connects the quote to the rule; for instance, 'the service is described as being integral to the product's core function']. This indicates that the two promises are highly interrelated and not separately identifiable in the context of the contract (Analysis). Therefore, based on this analysis, we conclude that [state the definitive conclusion, e.g., 'the professional services and the product must be accounted for as a single performance obligation'] (Conclusion)."


**For Steps 2 & 5:** Your analysis should also briefly explain *why an alternative accounting treatment, if any, was rejected*.
</ANALYSIS_STRUCTURE_RULE>

<ALTERNATIVE_TREATMENT_RULE>
**FOR STEP 2 AND STEP 5 ONLY:** After your main analysis paragraph, you MUST add a short, separate paragraph addressing why a potential alternative was rejected. For example: "An alternative view might be to treat the implementation as distinct, as the customer could use another vendor. However, this was rejected because the evidence suggests the core utility of the SaaS license is not realized without the proprietary configuration included in the service."
</ALTERNATIVE_TREATMENT_RULE>

""",
            critical_rules
        ]
        return "\n\n".join(prompt_parts)
      
    # --- NEW: Modular Helper Functions ---

    @staticmethod
    def _filter_genuine_judgments(judgments: list) -> list:
        """
        Applies consistent filtering logic to remove standard ASC 606 application 
        that doesn't represent genuine professional judgment.
        
        Returns only judgments that involve significant estimation, choice between 
        viable alternatives, or genuine uncertainty.
        """
        filtered_judgments = []
        for judgment in judgments:
            judgment_lower = judgment.lower()
            # Filter out standard ASC 606 application
            is_standard_application = (
                "single performance obligation" in judgment_lower or
                "over time" in judgment_lower or 
                "point in time" in judgment_lower or
                "distinct" in judgment_lower or
                "revenue is recognized" in judgment_lower or
                "subscription service" in judgment_lower
            )
            if not is_standard_application:
                filtered_judgments.append(judgment)
        return filtered_judgments

    @staticmethod
    def _get_schema_for_step(step_number: int) -> str:
        """Helper to route to the correct, existing schema definition."""
        if step_number == 1: return StepPrompts.get_step1_schema()
        if step_number == 2: return StepPrompts.get_step2_schema()
        if step_number == 3: return StepPrompts.get_step3_schema()
        if step_number == 4: return StepPrompts.get_step4_schema()
        if step_number == 5: return StepPrompts.get_step5_schema()
        return "{}"

    @staticmethod
    def _get_critical_rules_for_step(step_number: int, contract_text: str) -> str:
        """Returns a concise block of the most critical, non-negotiable rules for a given step."""
        rules = {
            1: """<CRITICAL_INSTRUCTION>
- You MUST evaluate ALL FIVE criteria from ASC 606-10-25-1(a) through (e) within the `contract_criteria_assessment` array. No shortcuts.
- You MUST create a corresponding `analysis_points` entry for each of the five criteria.
</CRITICAL_INSTRUCTION>""",
            2: """<CRITICAL_INSTRUCTION>
- If no distinct performance obligations are found, `performance_obligations` MUST be an empty list `[]`, and you must explain why in the `analysis_points`. But an genuine ASC 606 contract should have at least one performance obligation.
- For simple contracts with one obvious performance obligation, keep the analysis concise but complete.
- Focus on the "separately identifiable" (also called "distinct within the context of the contract") criterion, as it is often the most decisive factor.
</CRITICAL_INSTRUCTION>
""",
            3: """<CRITICAL_INSTRUCTION>
- Your primary analysis MUST occur within the `transaction_price_components` JSON structure.
- Only use `analysis_points` for truly separate or unusual considerations not already covered by the standard components.
</CRITICAL_INSTRUCTION>""",
            4: """<CRITICAL_INSTRUCTION>
- If there is only one performance obligation identified in Step 2, the `analysis_points` array MUST be empty `[]`. The `step4_overall_conclusion` is sufficient.
- Do NOT re-identify or re-analyze performance obligations or the transaction price in this step. Simply reference the POs from Step 2.
</CRITICAL_INSTRUCTION>""",
            5: """<CRITICAL_INSTRUCTION>
- You MUST provide detailed analysis in both the `revenue_recognition_plan` and `analysis_points`. Do not use shortcuts like "No additional analysis required".
- The `revenue_recognition_plan` must include a specific `recognition_justification` for each PO, citing which ASC 606-10-25-27 criterion is met for 'Over Time' recognition.
- You must include a `measure_of_progress_analysis` explaining the method used (e.g., straight-line, input/output).
</CRITICAL_INSTRUCTION>"""
        }

        # Special logic for Step 3 to prevent hallucination
        if step_number == 3:
            contract_lower = contract_text.lower()
            is_simple_contract = "subscription" in contract_lower or "fixed fee" in contract_lower
            is_complex_contract = "bonus" in contract_lower or "royalty" in contract_lower or "variable" in contract_lower

            if is_simple_contract and not is_complex_contract:
                return rules[3] + """
<CRITICAL_OVERRIDE>
This appears to be a simple, fixed-price contract. You MUST follow these rules:
- In the `transaction_price_components` JSON, set `variable_consideration` to "N/A".
- The `professional_judgments` array MUST be an empty list `[]`.
- Do NOT invent complexity where none exists.
</CRITICAL_OVERRIDE>"""

        return rules.get(step_number, "")

    # --- EXISTING FUNCTIONS ---

    @staticmethod
    def get_financial_impact_prompt(s1: dict,
                                    s2: dict,
                                    s3: dict,
                                    s4: dict,
                                    s5: dict,
                                    customer_name: str,
                                    memo_audience: str,
                                    contract_data=None) -> str:
        """Generates proportional financial impact prompt based on structured data analysis."""
        import json

        # Extract structured data from each step

        # Step 1: Contract validity - FIXED to access nested structure
        contract_valid = "Valid"
        if s1_analysis := s1.get('step1_analysis'):
            if s1_criteria := s1_analysis.get('contract_criteria_assessment'):
                failed_criteria = [
                    c for c in s1_criteria if c.get('status') == 'Not Met'
                ]
                if failed_criteria:
                    contract_valid = f"Invalid - Failed: {', '.join([c.get('criterion', 'Unknown') for c in failed_criteria])}"

        # Step 2: Performance obligations - FIXED to access nested structure
        performance_obligations = []
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                performance_obligations = [
                    po.get('po_description', 'Unknown PO') for po in s2_pos
                ]
        po_summary = f"{len(performance_obligations)} distinct performance obligation{'s' if len(performance_obligations) != 1 else ''}: {', '.join(performance_obligations)}" if performance_obligations else "Performance obligations not clearly identified"

        # Step 3: Transaction price components - FIXED to access nested structure
        transaction_price_data = {}
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                transaction_price_data = {
                    'total_price':
                    s3_price.get('total_transaction_price', 'Not specified'),
                    'fixed_consideration':
                    s3_price.get('fixed_consideration', 'Not specified'),
                    'variable_consideration':
                    s3_price.get('variable_consideration', []),
                    'financing_component':
                    s3_price.get('financing_component_analysis', 'None identified')
                }

        # Extract tax amount from Step 3 analysis for journal entries
        tax_amount_str = "Not specified"
        if s3_analysis := s3.get('step3_analysis'):
            # Search in other_considerations_analysis or similar fields
            other_considerations = s3_analysis.get('other_considerations_analysis', '')
            # Also search in the analysis_points of step 3
            for point in s3.get('analysis_points', []):
                if 'tax' in point.get('topic_title', '').lower():
                    # Find a dollar amount in the analysis text
                    import re
                    match = re.search(r'\$?(\d+\.\d{2})', point.get('analysis_text', ''))
                    if match:
                        tax_amount_str = f"${match.group(1)}"
                        break

        # Step 4: Allocation details - FIXED to access nested structure
        allocation_data = {}
        if s4_analysis := s4.get('step4_analysis'):
            allocation_data = s4_analysis.get('allocation_details', {})

        # Step 5: Revenue recognition plan - FIXED to access nested structure
        recognition_methods = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                recognition_methods = [(po.get('performance_obligation',
                                               'Unknown'),
                                        po.get('recognition_method', 'Unknown'),
                                        po.get('measure_of_progress', 'Unknown'))
                                       for po in s5_plan]

        # --- Enhanced Complexity Scoring System ---
        complexity_score = 0
        complexity_reasons = []

        # Criterion 1: Multiple POs with different timing
        po_methods = [method[1] for method in recognition_methods]
        if len(po_methods) > 2:
            complexity_score += 1
            complexity_reasons.append("More than two performance obligations")
        if len(set(po_methods)) > 1:
            complexity_score += 1
            complexity_reasons.append(
                "Mixed revenue recognition timing (Over Time and Point in Time)"
            )

        # Criterion 2: Variable Consideration (high-judgment area)
        var_consideration = transaction_price_data.get("variable_consideration")
        has_variable_consideration = False
        if var_consideration:
            var_str = str(var_consideration).strip().lower()
            has_variable_consideration = (
                var_str not in ["n/a", "not applicable", "none", "none identified", ""]
                and len(var_str) > 10
                and "variable" in var_str
            )
        if has_variable_consideration:
            complexity_score += 2
            complexity_reasons.append("Contains variable consideration")

        # Criterion 3: Significant Financing Component (high-judgment area)
        financing_analysis = transaction_price_data.get(
            'financing_component', '')
        if 'significant financing component' in financing_analysis.lower():
            complexity_score += 2
            complexity_reasons.append(
                "Contains a significant financing component")

        # Criterion 4: Complex Allocation (requires SSP estimation)
        if s4_details := s4.get('allocation_details'):
            if allocations := s4_details.get('allocations'):
                for alloc in allocations:
                    ssp_info = alloc.get('standalone_selling_price',
                                         '').lower()
                    if "method" in ssp_info and "observable" not in ssp_info:
                        complexity_score += 1
                        complexity_reasons.append(
                            "Requires estimation of Standalone Selling Price")
                        break

        # Criterion 5: Other High-Judgment Factors (from contract data)
        if contract_data:
            if getattr(contract_data, 'is_modification', False):
                complexity_score += 2
                complexity_reasons.append("Is a contract modification")
            if getattr(contract_data, 'principal_agent_involved', False):
                complexity_score += 2
                complexity_reasons.append(
                    "Involves Principal vs. Agent analysis")

        # Final determination: Score of 2 or more is complex
        is_complex = complexity_score >= 2
        complexity_summary = f"Score: {complexity_score}/10 ({'Complex' if is_complex else 'Simple'})"
        if complexity_reasons:
            complexity_summary += f" - Reasons: {'; '.join(complexity_reasons)}"
        # --- End Enhanced Complexity Logic ---

        return f"""You are a corporate controller writing the "Financial Impact" section of an ASC 606 memo. Your response must be concise and proportional to the complexity of the transaction.

STRUCTURED ANALYSIS DATA:
- Contract Status: {contract_valid}
- Performance Obligations: {po_summary}
- Transaction Price: {transaction_price_data.get('total_price', 'Not specified')}
- Variable Consideration: {json.dumps(transaction_price_data.get('variable_consideration', []), indent=2) if transaction_price_data.get('variable_consideration') else 'None'}
- Allocation Details: {json.dumps(allocation_data, indent=2) if allocation_data else 'Not specified'}
- Revenue Recognition Methods: {recognition_methods}
- Transaction Complexity: {complexity_summary}

YOUR TASK:
Write a concise financial impact analysis.

**CRITICAL TAX RULE: Any sales tax collected from the customer generally is NOT revenue or deferred revenue.** It must be recorded as a separate liability (e.g., 'Sales Tax Payable'). The journal entry should show a debit to Cash or Accounts Receivable for the sales tax amount and a separate credit to Sales Tax Payable.

**CRITICAL RULE: Be Proportional.**
- **For SIMPLE transactions** (like a standard, single-element subscription): Provide a very brief, 1-2 sentence summary of the accounting treatment and one summary journal entry. DO NOT write a lengthy narrative or explain basic accounting principles.
- ** For COMPLEX transactions**, follow this structure:**

1.  **Financial Statement Impact:** In a narrative paragraph, describe the expected impact on the income statement and balance sheet (e.g., creation of contract assets or deferred revenue liabilities).

2.  **Illustrative Journal Entries:** Provide key journal entries in a clear, tabular Markdown format. Use standard account names.
**Focus on the most critical events, such as:**
- **The journal entry upon contract signing/initial invoicing.**
- **The journal entry to recognize the first period of revenue for 'Over Time' obligations.**
- **The journal entry to recognize revenue for a 'Point in Time' obligation.**

    | Date       | Account                          | Debit     | Credit    |
    |------------|----------------------------------|-----------|-----------|
    | [date]     | [asset] or [liability]           | $[amount] |           |
    |            |   [liability] or [revenue]       |           | $[amount] |
    |            | *To record [include the purpose] |           |           |


3.  **Internal Control & Process Considerations:** Briefly mention any internal controls over financial reportin (ICFR) considerations required for accurate accounting and effective control environment (e.g., the need to track usage for variable revenue, or new processes to monitor the satisfaction of performance obligations over time).

---

Begin writing the financial impact section, strictly adhering to the proportionality rule.
"""

    @staticmethod
    def get_conclusion_prompt(s1: dict,
                              s2: dict,
                              s3: dict,
                              s4: dict,
                              s5: dict,
                              customer_name: str,
                              memo_audience: str,
                              contract_data=None) -> str:
        """Generates a proportional and meaningful conclusion prompt using structured data."""

        # Extract structured data for conclusion

        # Performance obligations and recognition methods - FIXED to access nested structure
        performance_obligations = []
        recognition_methods = []
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                performance_obligations = [
                    po.get('po_description', 'Unknown PO') for po in s2_pos
                ]
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                recognition_methods = [(po.get('performance_obligation',
                                               'Unknown'),
                                        po.get('recognition_method', 'Unknown'),
                                        po.get('measure_of_progress', 'Unknown'))
                                       for po in s5_plan]

        # Transaction price components - FIXED to access nested structure
        transaction_price_data = {}
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                transaction_price_data = {
                    'variable_consideration':
                    s3_price.get('variable_consideration', []),
                    'financing_component':
                    s3_price.get('financing_component_analysis', 'None identified')
                }

        # --- Enhanced Complexity Scoring System (Same as Financial Impact) ---
        complexity_score = 0
        complexity_reasons = []

        # Criterion 1: Multiple POs with different timing
        po_methods = [method[1] for method in recognition_methods]
        if len(po_methods) > 2:
            complexity_score += 1
            complexity_reasons.append("More than two performance obligations")
        # Criterion 2: Variable Consideration (high-judgment area)
        var_consideration = transaction_price_data.get("variable_consideration")
        has_variable_consideration = False
        if var_consideration:
            var_str = str(var_consideration).strip().lower()
            has_variable_consideration = (
                var_str not in ["n/a", "not applicable", "none", "none identified", ""]
                and len(var_str) > 10
                and "variable" in var_str
            )
        if has_variable_consideration:
            complexity_score += 2
            complexity_reasons.append("Contains variable consideration")

        # Criterion 3: Significant Financing Component (high-judgment area)
        financing_analysis = transaction_price_data.get(
            'financing_component', '')
        if 'significant financing component' in financing_analysis.lower():
            complexity_score += 2
            complexity_reasons.append(
                "Contains a significant financing component")

        # Criterion 4: Complex Allocation (requires SSP estimation)
        if s4_details := s4.get('allocation_details'):
            if allocations := s4_details.get('allocations'):
                for alloc in allocations:
                    ssp_info = alloc.get('standalone_selling_price',
                                         '').lower()
                    if "method" in ssp_info and "observable" not in ssp_info:
                        complexity_score += 1
                        complexity_reasons.append(
                            "Requires estimation of Standalone Selling Price")
                        break

        # Criterion 5: Other High-Judgment Factors (from contract data)
        if contract_data:
            if getattr(contract_data, 'is_modification', False):
                complexity_score += 2
                complexity_reasons.append("Is a contract modification")
            if getattr(contract_data, 'principal_agent_involved', False):
                complexity_score += 2
                complexity_reasons.append(
                    "Involves Principal vs. Agent analysis")

        # Final determination: Score of 2 or more is complex
        is_complex = complexity_score >= 2
        complexity_summary = f"Score: {complexity_score}/10 ({'Complex' if is_complex else 'Simple'})"
        if complexity_reasons:
            complexity_summary += f" - Reasons: {'; '.join(complexity_reasons)}"

        # Simple contract detection logic - FIXED to use nested data paths
        is_simple_contract = True

        # Correctly get PO count from nested structure
        po_count = 0
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                po_count = len(s2_pos) if s2_pos else 0

        # Correctly check for variable consideration and financing from nested structure
        has_variable_consideration = False
        has_financing_component = False
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                var_consideration = s3_price.get('variable_consideration')
                if var_consideration:
                    var_str = str(var_consideration).strip().lower()
                    # Only treat as variable consideration if it's substantial and not N/A
                    has_variable_consideration = (
                        var_str not in ['n/a', 'not applicable', 'none', 'none identified', '']
                        and len(var_str) > 10
                        and 'variable' in var_str
                    )
                financing_analysis = s3_price.get('financing_component_analysis', '')
                has_financing_component = 'significant financing component' in str(financing_analysis).lower()

        # Professional judgments from all steps - apply consistent filtering
        all_judgments = []
        for step in [s1, s2, s3, s4, s5]:
            judgments = step.get('professional_judgments', [])
            if judgments:
                # Apply consistent filtering using shared function
                filtered = StepPrompts._filter_genuine_judgments(judgments)
                all_judgments.extend(filtered)

        # Mark as complex if any complexity indicators present
        if po_count > 1 or has_variable_consideration or has_financing_component or len(all_judgments) > 0:
            is_simple_contract = False

        # For simple contracts, return standard conclusion directly
        if is_simple_contract:
            return "RETURN_DIRECT_TEXT: The accounting treatment for this straightforward arrangement is appropriate and in accordance with ASC 606. Revenue will be recognized as described in the analysis above."

        # --- End Enhanced Complexity Logic ---

        return f"""You are an accounting senior manager writing the final "Conclusion" section of an ASC 606 memo. Your response must be professional, decisive, and proportional to the complexity of the transaction.

**CRITICAL CONTRACT CLASSIFICATION:**
This contract has been classified as: {"SIMPLE" if is_simple_contract else "COMPLEX"}


STRUCTURED ANALYSIS DATA:
- Performance Obligations Count: {len(performance_obligations)}
- Performance Obligations: {', '.join(performance_obligations) if performance_obligations else 'None identified'}
- Has Variable Consideration: {"Yes" if has_variable_consideration else "No"}
- Has Financing Component: {"Yes" if 'significant financing component' in financing_analysis.lower() else "No"}
- Recognition Methods: {[method[1] for method in recognition_methods]}
- Transaction Complexity: {complexity_summary}

YOUR TASK:
Write a final concluding section for the memo, strictly adhering to the proportionality rule below.

**CRITICAL RULE: Be Proportional and Avoid Generic Boilerplate.**

---
**IF THE TRANSACTION or Contract IS COMPLEX, follow this structure:**

### Conclusion
Write one comprehensive conclusion paragraph that:
1. States that the accounting treatment outlined in the memo is appropriate and in accordance with ASC 606
2. Summarizes the key revenue recognition approach
3. Based on the provided list of judgments, {json.dumps(all_judgments)}, summarize the key judgments. If the list is empty, you MUST state that 'no significant professional judgments were required'.
4. Only mention ongoing monitoring if the contract has variable elements or complex terms that require it
---

Begin writing the "Conclusion" section. Do not add any other text, summaries, or boilerplate language.
"""

    @staticmethod
    def get_enhanced_executive_summary_prompt(s1: dict, s2: dict, s3: dict,
                                              s4: dict, s5: dict,
                                              analysis_title: str,
                                              customer_name: str) -> str:
        """Generates enhanced executive summary using structured data from all steps."""
        import json

        # Extract structured data for executive summary

        # Step 1: Contract validity - FIXED to access nested structure
        contract_status = "Valid"
        failed_criteria = []
        if s1_analysis := s1.get('step1_analysis'):
            if s1_criteria := s1_analysis.get('contract_criteria_assessment'):
                failed_criteria = [
                    c.get('criterion', 'Unknown') for c in s1_criteria
                    if c.get('status') == 'Not Met'
                ]
                if failed_criteria:
                    contract_status = f"Invalid - Failed criteria: {', '.join(failed_criteria)}"

        # Step 2: Performance obligations summary - FIXED to access nested structure
        po_count = 0
        po_descriptions = []
        # First, get the nested analysis dictionary
        if s2_analysis := s2.get('step2_analysis'):
            # Then, get the performance obligations from inside it
            if s2_pos := s2_analysis.get('performance_obligations'):
                po_count = len(s2_pos) if s2_pos else 0
                po_descriptions = [
                    po.get('po_description', 'Unnamed PO') for po in s2_pos
                ]

        # Step 3: Transaction price details - FIXED to access nested structure
        total_price = "Not specified"
        has_variable_consideration = False
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                total_price = s3_price.get('total_transaction_price',
                                           'Not specified')
                var_consideration = s3_price.get('variable_consideration')
                if var_consideration:
                    var_str = str(var_consideration).strip().lower()
                    # Only treat as variable consideration if it's substantial and not N/A
                    has_variable_consideration = (
                        var_str not in ['n/a', 'not applicable', 'none', 'none identified', '']
                        and len(var_str) > 10
                        and 'variable' in var_str
                    )

        # Step 4: Allocation summary - FIXED to access nested structure
        allocation_summary = "Not applicable (single performance obligation)."
        if s4_analysis := s4.get('step4_analysis'):
            if s4_details := s4_analysis.get('allocation_details'):
                if allocations := s4_details.get('allocations'):
                    if len(allocations) > 1:
                        allocation_summary = f"Price allocated across {len(allocations)} POs based on standalone selling prices."

        # Step 5: Revenue recognition methods - FIXED to access nested structure
        recognition_summary = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                for po_plan in s5_plan:
                    method = po_plan.get('recognition_method', 'Unknown')
                    po_name = po_plan.get('performance_obligation', 'Unknown PO')
                    recognition_summary.append(f"{po_name}: {method}")

        # Extract actual critical judgments from step analyses (no defaults)  
        all_step_judgments = []
        for step_result in [s1, s2, s3, s4, s5]:
            if judgments := step_result.get('professional_judgments'):
                all_step_judgments.extend(judgments)
        
        # Apply consistent filtering using shared function
        critical_judgments = StepPrompts._filter_genuine_judgments(all_step_judgments)

        return f"""Write a professional executive summary for an ASC 606 technical accounting memo using a structured dashboard format.

STRUCTURED ANALYSIS DATA:
- Analysis: {analysis_title}
- Customer: {customer_name}
- Contract Status: {contract_status}
- Performance Obligations Count: {po_count}
- Performance Obligations: {po_descriptions}
- Total Transaction Price: {total_price}
- Has Variable Consideration: {"Yes" if has_variable_consideration else "No"}
- Allocation Method: {allocation_summary}
- Revenue Recognition Methods: {recognition_summary}
- Key Judgment Areas: {critical_judgments}

Create an executive summary using this professional structure:

**OVERALL CONCLUSION**
[Single paragraph stating the **concluded accounting treatment** for the contract under ASC 606, including the overall revenue recognition approach, based on the structured data above.]

**KEY FINDINGS**
• Contract Status: {contract_status}
• Performance Obligations: {po_count} distinct obligation{'s' if po_count != 1 else ''}{(' - ' + ', '.join(po_descriptions[:3])) if po_descriptions else ''}{'...' if len(po_descriptions) > 3 else ''}
• Transaction Price: {total_price}{' (includes variable consideration)' if has_variable_consideration else ''}
• Allocation: {allocation_summary}
• Revenue Recognition: {', '.join(recognition_summary[:2]) if recognition_summary else 'No revenue recognition methods applicable due to lack of performance obligations'}{'...' if len(recognition_summary) > 2 else ''}
• Critical Judgments: {', '.join(critical_judgments) if critical_judgments else 'None identified'}

Keep this professional, concise, and focused on executive-level insights."""

    @staticmethod
    def get_step1_schema() -> str:
        """Returns a comprehensive, structured JSON schema for the entirety of Step 1 analysis."""
        # Note: Formatted with \n newlines for consistency with existing file style.
        return '"step1_analysis": {\n' \
               '    "contract_criteria_assessment": [\n' \
               '      {\n' \
               '        "criterion": "Approval and Commitment",\n' \
               '        "status": "Met/Not Met",\n' \
               '        "justification": "Analysis based on ASC 606-10-25-1(a)..."\n' \
               '      },\n' \
               '      {\n' \
               '        "criterion": "Identification of Rights",\n' \
               '        "status": "Met/Not Met",\n' \
               '        "justification": "Analysis based on ASC 606-10-25-1(b)..."\n' \
               '      },\n' \
               '      {\n' \
               '        "criterion": "Identification of Payment Terms",\n' \
               '        "status": "Met/Not Met",\n' \
               '        "justification": "Analysis based on ASC 606-10-25-1(c)..."\n' \
               '      },\n' \
               '      {\n' \
               '        "criterion": "Commercial Substance",\n' \
               '        "status": "Met/Not Met",\n' \
               '        "justification": "Analysis based on ASC 606-10-25-1(d)..."\n' \
               '      },\n' \
               '      {\n' \
               '        "criterion": "Collectibility",\n' \
               '        "status": "Met/Not Met",\n' \
               '        "justification": "Analysis based on ASC 606-10-25-1(e)..."\n' \
               '      }\n' \
               '    ],\n' \
               '    "contract_combination_analysis": "Based on ASC 606-10-25-9, analyze if multiple contracts should be combined into a single accounting contract. Conclude with a clear Yes or No and justification, or state \'N/A\' if only one document was provided.",\n' \
               '    "contract_modification_analysis": "Analyze if the arrangement represents a modification of a pre-existing contract. If so, analyze if it should be accounted for as a separate contract or as a change to the original. State \'N/A\' if this is a new contract arrangement.",\n' \
               '    "step1_overall_conclusion": "Provide a single, definitive summary statement for all of Step 1."\n' \
               '  }\n'

    @staticmethod
    def get_step2_schema() -> str:
        """Returns a comprehensive, structured JSON schema for the entirety of Step 2 analysis."""
        # Note: Formatted with \n newlines for consistency with existing file style.
        return '"step2_analysis": {\n' \
               '    "performance_obligations": [\n' \
               '      {\n' \
               '        "po_description": "Brief description of the promised good or service. If immaterial, note that here.",\n' \
               '        "is_distinct": "Yes/No",\n' \
               '        "distinct_analysis": "Concise justification citing ASC 606-10-25-19 criteria: (a) capable of being distinct AND (b) separately identifiable. Focus on the key factors that drive the conclusion.",\n' \
               '        "series_analysis": "Analyze if this PO is part of a series of distinct goods or services under ASC 606-10-25-14. State Yes or No and provide justification, or \'N/A\'."\n' \
               '      }\n' \
               '    ],\n' \
               '    "principal_vs_agent_analysis": "Analyze whether the company is acting as a principal or an agent for any promises, per ASC 606-10-55-36 through 55-40. Conclude for each relevant promise. State \'N/A\' if not applicable.",\n' \
               '    "customer_options_analysis": "Analyze if the contract provides any customer options for additional goods or services (e.g., discounts, renewals). If so, assess if they provide a material right under ASC 606-10-55-41 and should be a separate performance obligation. State \'N/A\' if not applicable.",\n' \
               '    "step2_overall_conclusion": "Provide a single, definitive summary statement for all of Step 2."\n' \
               '  }\n'

    @staticmethod
    def get_step3_schema() -> str:
        """Returns a comprehensive, structured JSON schema for all Step 3 components."""
        # Note: Formatted with \n newlines for consistency with existing file style.
        return '"step3_analysis": {\n' \
               '    "transaction_price_components": {\n' \
               '      "fixed_consideration": "Amount and description of fixed consideration, or \'N/A\' if not applicable.",\n' \
               '      "variable_consideration": "Detailed analysis of any variable consideration (e.g., bonuses, royalties), or \'N/A\' if not applicable.",\n' \
               '      "financing_component_analysis": "Analysis of any significant financing component, or \'N/A\' if not applicable.",\n' \
               '      "noncash_consideration_analysis": "Analysis of any noncash consideration, or \'N/A\' if not applicable.",\n' \
               '      "consideration_payable_to_customer_analysis": "Analysis of any consideration payable to the customer (e.g., credits, coupons), or \'N/A\' if not applicable.",\n' \
               '      "other_considerations_analysis": "Analysis of any other relevant considerations affecting the transaction price, such as refund liabilities, rights of return, nonrefundable upfront fees or changes in the transaction price, or \'N/A\' if not applicable.",\n' \
               '      "total_transaction_price": "The final, total estimated transaction price."\n' \
               '    },\n' \
               '    "step3_overall_conclusion": "Provide a single, definitive summary statement for all of Step 3."\n' \
               '  }\n'

    @staticmethod
    def get_step4_schema() -> str:
        """Returns a comprehensive, structured JSON schema for the entirety of Step 4 analysis."""
        # Note: Formatted with \n newlines for consistency with existing file style.
        return '"step4_analysis": {\n' \
               '    "allocation_details": {\n' \
               '      "total_transaction_price": "The total amount from Step 3",\n' \
               '      "allocations": [\n' \
               '        {\n' \
               '          "performance_obligation": "Reference the PO from Step 2 (do NOT re-identify or re-describe performance obligations here)",\n' \
               '          "ssp_determination": "Describe how the Standalone Selling Price (SSP) was determined, following the hierarchy in ASC 606-10-32-33 (observable price, or estimation method like adjusted market, cost-plus-margin, or residual).",\n' \
               '          "allocated_amount": "Amount of the transaction price allocated to this performance obligation."\n' \
               '        }\n' \
               '      ]\n' \
               '    },\n' \
               '    "variable_consideration_allocation_analysis": "Analyze if any variable consideration should be allocated to a specific performance obligation per ASC 606-10-32-39, rather than proportionally. State \'N/A\' if no variable consideration exists or if it relates to the entire contract.",\n' \
               '    "discount_allocation_analysis": "Analyze if any discount should be allocated to one or more (but not all) performance obligations per ASC 606-10-32-37. State \'N/A\' if no discount exists or if it applies to all POs.",\n' \
               '    "changes_in_price_analysis": "Briefly describe how a change in the transaction price after contract inception would be allocated based on the guidance in ASC 606-10-32-42. State \'N/A\' if not relevant.",\n' \
               '    "step4_overall_conclusion": "Provide a single, definitive summary statement for all of Step 4."\n' \
               '  }\n'

    @staticmethod
    def get_step5_schema() -> str:
        """Returns a comprehensive, structured JSON schema for the entirety of Step 5 analysis."""
        # Note: Formatted with \n newlines for consistency with existing file style.
        return '"step5_analysis": {\n' \
               '    "revenue_recognition_plan": [\n' \
               '      {\n' \
               '        "performance_obligation": "Name of the PO from Step 2",\n' \
               '        "recognition_method": "Over Time / Point in Time",\n' \
               '        "recognition_justification": "If \'Over Time\', state which of the three criteria in ASC 606-10-25-27 is met. If \'Point in Time\', discuss the transfer of control indicators per ASC 606-10-25-30.",\n' \
               '        "measure_of_progress_analysis": "If \'Over Time\', describe the method (e.g., straight-line, input/output method) and justify why it best depicts the transfer of control. If \'Point in Time\', state the specific timing of control transfer."\n' \
               '      }\n' \
               '    ],\n' \
               '    "special_arrangements_analysis": {\n' \
               '      "licenses_of_ip": "Analyze if any POs are licenses of intellectual property and determine if they represent a right to use (point in time) or a right to access (over time) per ASC 606-10-55-58. State \'N/A\' if not applicable.",\n' \
               '      "repurchase_agreements": "Analyze for any repurchase agreements (forwards, calls, puts) and their accounting impact (lease, financing, or sale with a right of return) per ASC 606-10-55-66. State \'N/A\' if not applicable.",\n' \
               '      "bill_and_hold": "Analyze if any bill-and-hold arrangements exist and if they meet all the criteria in ASC 606-10-55-83 to recognize revenue. State \'N/A\' if not applicable.",\n' \
               '      "consignment_arrangements": "Analyze if any consignment arrangements exist where the entity controls the product before it is sold to an end customer. State \'N/A\' if not applicable.",\n' \
               '      "breakage": "Analyze for any expected breakage on non-refundable upfront fees or other prepayments. State \'N/A\' if not applicable."\n' \
               '    },\n' \
               '    "step5_overall_conclusion": "Provide a single, definitive summary statement for all of Step 5."\n' \
               '  }\n'



    @staticmethod
    def get_consistency_check_prompt(s1: dict, s2: dict, s3: dict, s4: dict,
                                     s5: dict) -> str:
        """Generate consistency check prompt using structured data from all 5 steps."""
        import json

        # Check for missing step data and flag it
        missing_steps = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            if not step or not isinstance(step, dict) or len(step) < 2:
                missing_steps.append(i)

        if missing_steps:
            return f"""You are an expert accounting review bot. CRITICAL ISSUE DETECTED:
Step(s) {missing_steps} returned insufficient data (likely due to API failures or parsing errors).
This prevents meaningful consistency checking.

You MUST return the following JSON structure indicating the analysis is incomplete:
{{
  "is_consistent": false,
  "issues_found": [
    {{
      "issue_code": "MISSING_STEP_DATA",
      "description": "Step(s) {missing_steps} failed to return complete analysis data, preventing consistency validation."
    }}
  ]
}}"""

        # Use the rich, structured data, not just the text conclusion
        step_data = {
            "step_1_assessment": s1.get('contract_criteria_assessment', {}),
            "step_2_obligations": s2.get('performance_obligations', []),
            "step_3_price": s3.get('transaction_price_components', {}),
            "step_4_allocation": s4.get('allocation_details', {}),
            "step_5_recognition": s5.get('revenue_recognition_plan', [])
        }

        return f"""You are an expert accounting review bot. Your task is to perform a logical consistency check on the following ASC 606 analysis data.

ANALYSIS DATA:
{json.dumps(step_data, indent=2)}

CRITICAL REVIEW TASK:
Analyze the data above and perform these specific checks:
1.  **PO Count Mismatch:** Does the number of distinct performance obligations in `step_2_obligations` match the number of allocations in `step_4_allocation`?
2.  **Price Mismatch:** Does the `total_transaction_price` in `step_3_price` appear to equal the sum of the `allocated_amount` fields in `step_4_allocation`? (You may need to parse numbers from strings).
3.  **Recognition Mismatch:** Does every performance obligation listed in `step_2_obligations` have a corresponding entry in the `step_5_recognition` plan?
4.  **Contract Validity:** If any criterion in `step_1_assessment` is "Not Met", does the rest of the analysis correctly reflect that no revenue should be recognized yet?
5.  **Semantic Mismatch:** For each performance obligation, does the `recognition_method` in `step_5_recognition` make logical sense given the `po_description` in `step_2_obligations`? (e.g., A one-time 'Setup Fee' should generally not be recognized 'Over Time'; a '12-month Support Service' should generally not be recognized at a 'Point in Time').


You MUST return your response as a single JSON object with the following exact structure:
{{
  "is_consistent": true/false,
  "issues_found": [
    {{
      "issue_code": "PO_COUNT_MISMATCH",
      "description": "A brief explanation of the inconsistency found."
    }}
  ]
}}

If the analysis is fully consistent, return {{"is_consistent": true, "issues_found": []}}. If you find multiple issues, add multiple objects to the 'issues_found' list."""

    @staticmethod
    def get_background_prompt(contract_data) -> str:
        """Generates a focused and non-repetitive background section."""
        key_focus = getattr(contract_data, 'key_focus_areas', '')

        return f"""You are writing the 'Background' section of a formal ASC 606 accounting memo. A summary data table will appear just before your text, so DO NOT repeat basic information like party names or contract dates.

YOUR TASK:
Write a single, concise paragraph that provides context for the analysis. Your paragraph should cover:
1. **Nature of the Arrangement:** Briefly describe the business purpose of the contract based on the summary provided below.
2. **Scope of this Memo:** State that the objective of this memorandum is to document the Company's accounting analysis and conclusions under ASC 606.
3. **Specific Areas of Judgment (if provided):** If the user provided specific 'Key Focus Areas', incorporate them into the scope. This is the most important part.

CONTEXT:
- Arrangement Summary: "{getattr(contract_data, 'arrangement_description', 'A standard sales arrangement.')}"
- Key Focus Areas provided by user: "{key_focus if key_focus else 'None'}"

Example if focus areas ARE provided:
"The objective of this memorandum is to document the accounting analysis for this arrangement under ASC 606, with a specific focus on evaluating whether the implementation services are distinct from the SaaS license, per the criteria in ASC 606-10-25-21."

Example if no focus areas are provided:
"The objective of this memorandum is to document the Company's accounting analysis and conclusions for the transaction with the customer under the five-step model of ASC 606."

Write only the paragraph, no additional formatting or labels."""

    @staticmethod
    def get_key_judgments_prompt(s1: dict, s2: dict, s3: dict, s4: dict,
                                 s5: dict) -> str:
        """Generates a highly discerning prompt for the Key Professional Judgments section."""
        all_judgments = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            # The 'professional_judgments' key comes from the initial 5-step analysis
            judgments = step.get('professional_judgments', [])
            if judgments and isinstance(judgments, list):
                # Apply consistent filtering using the shared utility function
                filtered = StepPrompts._filter_genuine_judgments(judgments)
                all_judgments.extend(filtered)

        # If, after filtering, no genuine judgments remain, provide a standard statement.
        if not all_judgments:
            return "RETURN_DIRECT_TEXT: The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

        # If judgments were flagged, this prompt acts as a final, expert-level quality filter.
        return f"""You are an accounting senior manager writing the "Key Professional Judgments" section of an audit-ready ASC 606 memo. Your role is to be a highly discerning final quality filter.

CONTEXT: The initial analysis flagged these potential judgment areas:
{json.dumps(all_judgments, indent=2)}

YOUR TASK:
1.  **Review the Context:** Scrutinize the list above. Your primary task is to distinguish between genuine professional judgments and standard contract analysis.
2.  **Identify Genuine Judgments:** A **genuine judgment** involves significant estimation, a choice between viable accounting alternatives, or a "gray area" in the guidance.
    - **Examples of Genuine Judgments:** "Estimating the standalone selling price (SSP) of a license using a residual approach," "Concluding that a performance bonus is not constrained," "Assessing whether a contract modification is a separate contract."
    - **Standard analysis is NOT a judgment.** Do not include items like: "Concluding a SaaS service is a single performance obligation," or "Recognizing subscription revenue over time."
3.  **Format Your Output:** For each genuine judgment you identify, create a bullet point with a single, well-written paragraph called 'Rationale' that seamlessly combines the issue, analysis, and authoritative guidance.
4.  **Provide a "No Judgments" Conclusion if Necessary:** If your review finds that none of the items in the context are genuine judgments, your entire response MUST be only the following sentence:
    "The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

---
### EXAMPLE OF DESIRED OUTPUT:

- **Estimating the Standalone Selling Price (SSP) for the On-Premise License:**
  **Rationale:** The contract does not include a standalone price for the on-premise license, and an observable price is not available as the license is not sold separately. Therefore, a significant judgment was required to estimate the SSP. Per the hierarchy in ASC 606-10-32-33, we used the residual approach. This was deemed appropriate because the SSP for the professional services and support obligations were readily observable and stable. The total transaction price less the observable SSPs equals $450,000, representing the estimated fair value for the license component.

---
Begin your work. Your precision is critical to producing an audit-ready memo.
"""

    @staticmethod
    def format_step_detail_as_markdown(step_data: dict, step_number: int,
                                       step_name: str) -> str:
        """Format step analysis from narrative JSON structure into professional markdown."""
        if not step_data or not isinstance(step_data, dict):
            return f"### Step {step_number}: {step_name}\n\nNo analysis data was returned for this step.\n"

        conclusion = step_data.get('executive_conclusion',
                                   'No conclusion was provided.')
        analysis_points = step_data.get('analysis_points', [])

        # Start with the main heading and the upfront conclusion
        markdown_sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            "\n---\n",  # Visual separator
            "**Detailed Analysis:**\n"
        ]

        # AUDITOR'S METHOD: Special handling for Steps 2, 3, and ALL steps to filter out N/A items
        if step_number == 2:
            return StepPrompts._format_step2_with_filtering(
                step_data, step_name, conclusion, analysis_points)
        elif step_number == 3:
            return StepPrompts._format_step3_with_filtering(
                step_data, step_name, conclusion, analysis_points)
        elif step_number in [1, 4, 5]:
            return StepPrompts._format_general_step_with_filtering(
                step_data, step_name, conclusion, analysis_points, step_number)

        # Continue with normal processing for other steps

        if not analysis_points:
            markdown_sections.append(
                "No detailed analysis points were provided.")
        else:
            # Loop through each thematically-grouped analysis point
            for i, point in enumerate(analysis_points):
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text',
                                          'No analysis text provided.')
                evidence_quotes = point.get('evidence_quotes', [])

                # Add the topic as a sub-heading
                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(analysis_text)

                # Add the evidence quotes for that topic
                # Add type check to prevent errors if the LLM returns a string instead of list
                if evidence_quotes and isinstance(evidence_quotes, list):
                    for quote in evidence_quotes:
                        if isinstance(
                                quote, str
                        ):  # Ensure the item in the list is a string
                            markdown_sections.append(f"> {quote}")
                elif isinstance(evidence_quotes, str):
                    # Handle case where LLM returns a single string instead of list
                    markdown_sections.append(f"> {evidence_quotes}")

                markdown_sections.append(
                    "")  # Add a blank line for spacing before the next point

        markdown_sections.append("---\n")  # Final separator
        return "\n".join(markdown_sections)

    @staticmethod
    def _format_step3_with_filtering(step_data: dict, step_name: str,
                                     conclusion: str,
                                     analysis_points: list) -> str:
        """
        Apply the Auditor's Method to Step 3: Merge structured components and
        analysis points into a single, consistently formatted list.
        """
        markdown_sections = [
            f"### Step 3: {step_name}", f"**Conclusion:**\n{conclusion}",
            "\n---\n", "**Detailed Analysis:**\n"
        ]

        all_points = []

        # 1. Process structured transaction_price_components intelligently
        transaction_components = step_data.get('step3_analysis', {}).get('transaction_price_components', {})

        # Define a mapping for better titles
        title_map = {
            'total_transaction_price': 'Total Transaction Price',
            'fixed_consideration': 'Fixed Consideration',
            'variable_consideration': 'Variable Consideration',
            'financing_component_analysis': 'Significant Financing Component',
            'noncash_consideration_analysis': 'Noncash Consideration',
            'consideration_payable_to_customer_analysis': 'Consideration Payable to Customer',
            'other_considerations_analysis': 'Other Considerations'
        }

        # Smart filtering: avoid redundant price entries
        processed_values = set()
        
        for key, analysis_text in transaction_components.items():
            is_not_applicable = (
                analysis_text is None or
                str(analysis_text).strip().lower() in ('n/a', 'not applicable', '') or
                str(analysis_text).strip().lower().startswith('n/a') or
                len(str(analysis_text).strip()) < 3
            )

            if not is_not_applicable:
                text_str = str(analysis_text).strip()
                
                # Skip if this is a redundant price amount we've already seen
                if key in ['fixed_consideration', 'total_transaction_price']:
                    if text_str in processed_values:
                        continue  # Skip duplicate price entries
                    processed_values.add(text_str)
                
                # Only include substantive analysis, not just price amounts
                if key in ['fixed_consideration', 'total_transaction_price'] and len(text_str) < 30:
                    # This is likely just a price amount, skip it if we have analysis_points with more detail
                    continue
                
                topic_title = title_map.get(key, key.replace('_', ' ').title())
                all_points.append({'topic_title': topic_title, 'analysis_text': analysis_text, 'evidence_quotes': []})

        # 2. Add the regular analysis_points (these already have quotes)
        if analysis_points:
            all_points.extend(analysis_points)

        # 3. Format the combined list
        if not all_points:
            markdown_sections.append("Only basic fixed consideration was identified in this contract.")
        else:
            for i, point in enumerate(all_points):
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text', 'No analysis text provided.')
                evidence_quotes = point.get('evidence_quotes', [])

                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(str(analysis_text))

                # Integrate evidence directly below the analysis text it supports
                if evidence_quotes and isinstance(evidence_quotes, list):
                    for quote in evidence_quotes:
                        # Add a blockquote for each piece of evidence
                        if isinstance(quote, str) and quote:
                            markdown_sections.append(f"> {quote}")

                markdown_sections.append("") # Add spacing before next point

        return "\n".join(markdown_sections)

    @staticmethod
    def _format_step2_with_filtering(step_data: dict, step_name: str,
                                     conclusion: str,
                                     analysis_points: list) -> str:
        """Apply the Auditor's Method to Step 2: Filter out N/A components."""
        markdown_sections = [
            f"### Step 2: {step_name}", f"**Conclusion:**\n{conclusion}",
            "\n---\n", "**Detailed Analysis:**\n"
        ]

        # Filter analysis points to remove N/A topics
        ignore_phrases = {'n/a', 'not applicable'}
        filtered_points = []

        for point in analysis_points:
            topic_title = point.get('topic_title', '')
            analysis_text = point.get('analysis_text', '')

            # Check if the analysis text indicates N/A
            analysis_text_str = str(analysis_text or '').strip().lower()
            is_not_applicable = False

            if not analysis_text_str:
                is_not_applicable = True
            elif analysis_text_str in ignore_phrases or analysis_text_str.startswith(
                    'n/a'):
                is_not_applicable = True

            # Only include if not N/A
            if not is_not_applicable:
                filtered_points.append(point)

        # Use filtered points for display
        if not filtered_points:
            markdown_sections.append(
                "The contract contains a straightforward single performance obligation."
            )
        else:
            for i, point in enumerate(filtered_points):
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text',
                                          'No analysis text provided.')
                evidence_quotes = point.get('evidence_quotes', [])

                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(analysis_text)

                # NEW: Integrate evidence directly below the analysis text it supports
                if evidence_quotes and isinstance(evidence_quotes, list):
                    for quote in evidence_quotes:
                        # Add a blockquote for each piece of evidence
                        if isinstance(quote, str) and quote:
                            markdown_sections.append(f"> {quote}")

                markdown_sections.append("") # Add spacing before next point

        return "\n".join(markdown_sections)

    @staticmethod
    def _format_general_step_with_filtering(step_data: dict, step_name: str,
                                            conclusion: str,
                                            analysis_points: list,
                                            step_number: int) -> str:
        """Apply the Auditor's Method to Steps 1, 4, and 5: Filter out N/A components and format structured data."""
        markdown_sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}", "\n---\n",
            "**Detailed Analysis:**\n"
        ]
    
        # Existing logic for filtering analysis_points for Steps 1, 4, and 5
        ignore_phrases = {'n/a', 'not applicable'}
        filtered_points = []
        for point in analysis_points:
            topic_title = point.get('topic_title', '')
            analysis_text = point.get('analysis_text', '')
    
            analysis_text_str = str(analysis_text or '').strip().lower()
            is_not_applicable = False
            if not analysis_text_str or analysis_text_str in ignore_phrases or analysis_text_str.startswith('n/a'):
                is_not_applicable = True
    
            if not is_not_applicable:
                filtered_points.append(point)
    
        if not filtered_points:
            markdown_sections.append("No additional analysis was required for this step.")
        else:
            for i, point in enumerate(filtered_points):
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text',
                                          'No analysis text provided.')
                evidence_quotes = point.get('evidence_quotes', [])
    
                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(analysis_text)
    
                if evidence_quotes and isinstance(evidence_quotes, list):
                    for quote in evidence_quotes:
                        if isinstance(quote, str):
                            markdown_sections.append(f"> {quote}")
                elif isinstance(evidence_quotes, str):
                    markdown_sections.append(f"> {evidence_quotes}")
    
                markdown_sections.append("")  # Add spacing
    
        markdown_sections.append("---\n")
        return "\n".join(markdown_sections)