"""
Refactored ASC 606 prompt templates using System/User architecture for improved LLM adherence.
This approach separates the AI's core instructions (System Prompt) from the
dynamic task-specific instructions (User Prompt).

EXTENDED: ASC 340-40 Contract Costs prompt templates following the same proven architecture.
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
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 606. Your analysis must be audit-ready, understandable, precise, and objective.

<UNIVERSAL_RULES>
1.  **JSON Output Only:** You MUST return your response as a single, well-formed JSON object. CRITICAL: Begin your response with '{' and end with '}'. Do not include any text before '{' or after '}'. Your entire response must be valid JSON.
2.  **Knowledge Hierarchy:** Your analysis MUST be based on the following hierarchy of sources, in order of priority:
    a. **Contract Text:** The specific terms from the `<CONTRACT_TEXT>` are the primary evidence.
    b. **Authoritative Guidance:** The retrieved guidance from `<AUTHORITATIVE_CONTEXT>` (e.g., ASC 606) is the primary basis for your conclusions.
    c. **Interpretative Guidance:** Retrieved guidance from other sources (e.g., EY) should be used to support your analysis, especially in complex or high-judgment areas.
3.  **Evidence Formatting:** Every quote in the `evidence_quotes` array MUST include the source document name, formatted as: 'Quote text... (Source: [Document Name])'.
</UNIVERSAL_RULES>
"""

    @staticmethod
    def get_user_prompt_for_step(step_number: int, contract_text: str, rag_context: str, contract_data=None, debug_config=None) -> str:
        """
        Builds the dynamic, task-specific user prompt for a single step analysis.
        This revision uses programmatic logic and explicit instructions for using multi-source RAG context.
        """
        step_info = StepPrompts.get_step_info()[step_number]
        step_schema_name = f"step{step_number}_analysis"
        step_schema_definition = StepPrompts._get_schema_for_step(step_number)
        critical_rules = StepPrompts._get_critical_rules_for_step(step_number, contract_text)

        # Main instructions are constant. Define as a multi-line string.
        main_instructions = """### TASK-SPECIFIC INSTRUCTIONS FOR 'analysis_points' ###
        For each analysis point, you MUST generate the `analysis_text` using the "Issue, Analysis, Conclusion" (IAC) logical framework. Your final output should be a well-written, professional paragraph that seamlessly integrates these three parts without using explicit labels.

        1.  **Issue:** Begin by stating the specific accounting question being addressed.
        2.  **Analysis:** In the body of the paragraph, present your analysis. This must include:
            a. **Evidence:** Direct quotes from the `<CONTRACT_TEXT>`.
            b. **Rules:** Citations to the relevant authoritative guidance from `<AUTHORITATIVE_CONTEXT>`.
            c. **Reasoning:** Your explanation that connects the evidence and the rules to your conclusion.
        3.  **Conclusion:** End the paragraph with a clear, definitive conclusion that answers the issue.

        **META-EXAMPLE OF DESIRED NARRATIVE STYLE:**
        The primary issue is whether the promised implementation services are distinct from the SaaS license. The contract provides key evidence, stating that 'proprietary configuration' is required. Authoritative guidance in ASC 606-10-25-21 requires promises to be 'separately identifiable' to be considered distinct. Because the 'proprietary' nature of the configuration means the customer cannot obtain the full benefit of the SaaS license without this specific service, the two promises are not separately identifiable in the context of the contract. Therefore, the implementation service and the SaaS license are treated as a single performance obligation.

"""

        # Conditional instructions for specific steps
        alternative_treatment_instructions = ""
        if step_number in [2, 5]:
            alternative_treatment_instructions = """
### SPECIAL REQUIREMENT: Alternative View ###
For this step, you MUST append a second, separate paragraph to your `analysis_text`, starting with the bolded heading **"Alternative View Rejected:"**. Explain the alternative and why it was rejected.
"""

        # Combine the instructions programmatically.
        full_instructions = main_instructions + alternative_treatment_instructions

        # Assemble the final prompt parts.
        prompt_parts = [
            f"Your task is to analyze a contract for Step {step_number}: {step_info['title']}.",
            f"PRIMARY GUIDANCE FOR THIS STEP: {step_info['primary_guidance']}",
            f"<AUTHORITATIVE_CONTEXT>\n{rag_context}\n</AUTHORITATIVE_CONTEXT>",
            f"<CONTRACT_TEXT>\n{contract_text}\n</CONTRACT_TEXT>",
            f"<CONTRACT_DATA>\nCustomer: {getattr(contract_data, 'customer_name', 'N/A')}\nAnalysis Focus: {getattr(contract_data, 'key_focus_areas', 'General ASC 606 compliance')}\n</CONTRACT_DATA>",
            "---",
            "CRITICAL TASK: Analyze the contract based on the context provided. Populate the JSON structure below with your complete analysis. Adhere to all universal rules from the system prompt and the task-specific instructions that follow the JSON structure.",
            "```json",
            "{",
            f'  "executive_conclusion": "A clear, one-to-three sentence conclusion for this entire step. This is the \'bottom line\'.",',
            f'  "{step_schema_name}": {step_schema_definition},',
            '  "professional_judgments": [ {"judgment_title": "SHORT TITLE (2-4 words)", "judgment_rationale": "Brief explanation of the judgment and why it was necessary"} ],',
            '  "analysis_points": [ { "topic_title": "...", "analysis_text": "...", "evidence_quotes": ["..."] } ]',
            "}",
            "```",
            full_instructions,
            critical_rules
        ]

        return "\n\n".join(filter(None, prompt_parts))

    # --- NEW: Modular Helper Functions ---

    @staticmethod
    def _filter_genuine_judgments(judgments: list) -> list:
        """
        Applies consistent filtering logic to remove standard ASC 606 application 
        that doesn't represent genuine professional judgment.

        Returns only judgments that involve significant estimation, choice between 
        viable alternatives, or genuine uncertainty.
        
        Updated to handle both string and title/rationale object formats.
        """
        filtered_judgments = []
        for judgment in judgments:
            # Handle both old string format and new title/rationale object format
            if isinstance(judgment, dict):
                # New format: {"judgment_title": "...", "judgment_rationale": "..."}
                judgment_text = f"{judgment.get('judgment_title', '')} {judgment.get('judgment_rationale', '')}".lower()
                judgment_title = judgment.get('judgment_title', '')
            elif isinstance(judgment, str):
                # Old format: simple string
                judgment_text = judgment.lower()
                judgment_title = judgment
            else:
                continue
                
            # Filter out standard ASC 606 application
            is_standard_application = (
                "single performance obligation" in judgment_text or
                "over time" in judgment_text or 
                "point in time" in judgment_text or
                "distinct" in judgment_text or
                "revenue is recognized" in judgment_text or
                "subscription service" in judgment_text
            )
            
            if not is_standard_application:
                # Return the original judgment (preserving new format if it's an object)
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
- You MUST evaluate ALL FIVE criteria from ASC 606-10-25-1(a) through (e).
- You MUST create a corresponding `analysis_points` entry for each of the five criteria.

- **SPECIAL RULE FOR COLLECTIBILITY (ASC 606-10-25-1(e)):** You are NOT to analyze this criterion based on the contract text. The analysis of a customer's credit risk requires external information. Instead, you MUST use the following specific text for the `justification` in the `contract_criteria_assessment` and for the `analysis_text` in the corresponding `analysis_points` entry:

"The assessment of collectibility under ASC 606 is based on a customer's ability and intent to pay the consideration to which the entity is entitled. This requires an analysis of the customer's financial capacity and intention to pay, considering all relevant facts and circumstances, including historical payment experience.

As this analysis requires information external to the contract documents, it is assumed for the purpose of this initial memo that collection is probable and this criterion is met. This assumption must be validated by management's credit assessment of the customer. If it is determined that collection is not probable, this conclusion must be revisited, as a valid contract under ASC 606 would not exist."

For the 'status' of this criterion, you MUST set it to 'Met (Assumed)'.


</CRITICAL_INSTRUCTION>""",
            2: """<CRITICAL_INSTRUCTION>
Your analysis for this step must be exceptionally thorough. You will emulate the analytical style found in the ASC 606-10-55 implementation guidance (Example 11).

Your final output must be in the `analysis_points` array. For EACH promised good or service (e.g., SaaS, Hardware, Services), you MUST create a distinct "topic_title" and the corresponding "analysis_text" MUST follow this exact three-part structure:

**1. Assessment Against 606-10-25-19(a) (Benefit on its own):**
- State whether the customer can benefit from the good/service either on its own or with other readily available resources.
- Provide a brief justification. For example: "The customer can benefit from the hardware on its own by reselling it, or with other resources like third-party software."

**2. Assessment Against 606-10-25-19(b) (Separately Identifiable):**
- This section must explicitly evaluate the three factors from ASC 606-10-25-21.
- **(i) Significant Integration Service:** Analyze whether you are providing a significant service of integrating the items into a combined output. Quote from the SOW and explain *why* this service is (or is not) significant. In your reasoning, you MUST directly address phrases from the SOW like "required for optimal use."
- **(ii) Significant Modification:** Analyze whether one promised good/service significantly modifies or customizes another.
- **(iii) Highly Interdependent/Interrelated:** Analyze whether the goods/services are highly dependent on each other. Explain *why* the entity would (or would not) be able to fulfill its promise to transfer one item independently of the others.
- **(iv) Conclusion on Separately Identifiable:** Based on the three factors above, conclude whether the promise is distinct within the context of the contract.

**3. Overall Conclusion on Distinctness:**
- Based on the complete assessment above, identify the final performance obligation. For example: "On the basis of this assessment, the entity identifies the Hardware as a distinct performance obligation."

**META-EXAMPLE OF DESIRED OUTPUT STYLE:**

*Incorrect (too shallow):* "The hardware is distinct because title transfers at delivery."

*Correct (in-depth, emulating the guidance):*
"The entity determines that its promises to transfer the equipment and to provide the installation services are each separately identifiable. In making this determination, the entity considers the factors in 606-10-25-21. a) The entity is not providing a significant integration service because the entity would be able to fulfill its promise to transfer the equipment separately from its promise to subsequently install it. b) The installation services will not significantly modify the equipment. c) Although the customer can only benefit from the installation after receiving the equipment, the items are not highly interdependent because the equipment and services do not significantly affect each other. Therefore, the promise to provide the hardware is separately identifiable."

</CRITICAL_INSTRUCTION>
""",
            3: """<CRITICAL_INSTRUCTION>
- Your primary analysis MUST occur within the `transaction_price_components` JSON structure.
- Only use `analysis_points` for truly separate or unusual considerations not already covered by the standard components.
</CRITICAL_INSTRUCTION>""",
            4: """<CRITICAL_INSTRUCTION>
Your analysis of price allocation must clearly state the principles that will be applied.

1.  **Allocation Basis:** State that the total transaction price must be allocated to each performance obligation based on its relative Standalone Selling Price (SSP), as required by ASC 606-10-32-28.

2.  **SSP Source:** Briefly mention that determining SSP may require analyzing data outside of the contract, such as standalone sales data or other estimation methods (market assessment, cost-plus, residual) if an observable price is not available.

3.  **CRITICAL DISCOUNT INTERPRETATION RULES:**
   - When a contract states "The fees reflect a X% discount" or "The fees include a X% discount", the amounts listed are ALREADY POST-DISCOUNT amounts
   - Use the exact amounts stated in the contract - do NOT apply additional discounts to amounts that are already discounted
   - If the contract explicitly states which components are discounted and which are not (e.g., "The SaaS license is priced at its standard standalone rate. The hardware and services reflect a 10% discount"), treat each component according to its specified pricing
   - Per ASC 606-10-32-37, if the discount does not relate to one specific PO, it should be allocated proportionally to all POs. However, if the contract clearly indicates which POs are discounted, allocate accordingly.

4.  **Allocation Method:** Use the stated contract amounts as the basis for allocation - these represent the agreed-upon standalone selling prices as reflected in the contractual arrangement.

Your role is to frame the necessary analysis, not to perform external market research.

</CRITICAL_INSTRUCTION>""",
            5: """<CRITICAL_INSTRUCTION>
Your analysis of revenue recognition timing must be precise and directly reference the authoritative guidance. For EACH performance obligation, your analysis MUST clearly state:

1.  **Recognition Method:** State "Over Time" or "Point in Time".

2.  **Recognition Justification (The most important part):**
    *   **If "Over Time":** You MUST state which of the three criteria in ASC 606-10-25-27 is met and why.
        - (a) Customer simultaneously receives and consumes the benefits.
        - (b) The entity's performance creates or enhances an asset the customer controls.
        - (c) The performance does not create an asset with an alternative use, and the entity has an enforceable right to payment for performance completed to date.
    *   **If "Point in Time":** You MUST describe the specific event that signifies the transfer of control, referencing the indicators in ASC 606-10-25-30 (e.g., customer has legal title, physical possession, significant risks and rewards, etc.).

3.  **Measure of Progress (for "Over Time" only):** If recognition is Over Time, describe the method used to measure progress (e.g., straight-line, output method like milestones, or input method like hours incurred) and justify why it best depicts the transfer of control.

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
    def get_financial_extraction_prompt(contract_text: str) -> str:
        """Generate prompt for extracting structured financial components from contract text."""
        return f"""You are a financial analyst extracting structured fee components from a contract for precise calculation.

CONTRACT TEXT:
{contract_text}

Your task: Extract all fee components from this contract into structured JSON format.

REQUIRED JSON OUTPUT FORMAT:
{{
  "fee_components": [
    {{
      "component_name": "Brief, standardized name (e.g., 'SaaS License', 'Hardware Scanners')",
      "base_amount": 240000.00,
      "period": "annual" or "monthly" or "one-time" or "contingent",
      "duration": 3,
      "is_variable": false,
      "probability": 1.0,
      "notes": "Any source details, e.g., 'From SOW 2.1'"
    }}
  ]
}}

CRITICAL DISCOUNT INTERPRETATION RULES:
1. When a contract states "The fees reflect a X% discount" or "The fees include a X% discount", the amounts listed are ALREADY POST-DISCOUNT amounts
2. Use the exact amounts stated in the contract - do NOT apply additional discounts to amounts that are already discounted
3. If the contract says "standard price minus X% discount", then calculate the discount. But if it says "the fees reflect a discount", use the stated amounts as-is
4. Variable considerations (bonuses, penalties) are separate from bundle discounts

INSTRUCTIONS:
- Extract ALL monetary amounts mentioned in the contract
- Use the EXACT amounts stated in the pricing section - do not recalculate discounted amounts
- Convert percentages to decimal (10% = 0.10) only for probability calculations, not for fee amounts
- Use precise decimal amounts (no rounding)
- Include both fixed and variable considerations
- Be thorough but accurate - do not add amounts not explicitly mentioned

Respond ONLY with the JSON object."""

    @staticmethod
    def get_financial_impact_prompt(s1: dict,
                                    s2: dict,
                                    s3: dict,
                                    s4: dict,
                                    s5: dict,
                                    customer_name: str,
                                    memo_audience: str,
                                    contract_data=None,
                                    financial_facts=None) -> str:
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

        # Step 3: Use ONLY the calculated financial facts from hybrid system
        # NO EXTRACTION - Use the already-calculated Step 3 results directly
        transaction_price_data = {}
        if financial_facts and financial_facts.get("total_transaction_price", 0) > 0:
            # Use the hybrid extract-then-calculate results (100% reliable)
            transaction_price_data = {
                'total_price': f"${financial_facts.get('total_transaction_price', 0):,.2f}",
                'fixed_consideration': f"${financial_facts.get('fixed_consideration_total', 0):,.2f}",
                'variable_consideration': financial_facts.get('variable_consideration_items', []),
                'financing_component': 'None identified'
            }
        else:
            # Fallback if hybrid system failed
            transaction_price_data = {
                'total_price': 'Not available - hybrid calculation failed',
                'fixed_consideration': 'Not available',
                'variable_consideration': [],
                'financing_component': 'Not available'
            }

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

        return f"""You are a corporate controller writing the "Financial Impact" section of an ASC 606 memo.

STRUCTURED ANALYSIS DATA:
- Contract Status: {contract_valid}
- Performance Obligations: {po_summary}
- Transaction Price: {transaction_price_data.get('total_price', 'Not specified')}
- Variable Consideration: {json.dumps(transaction_price_data.get('variable_consideration', []), indent=2) if transaction_price_data.get('variable_consideration') else 'None'}
- Allocation Details: {json.dumps(allocation_data, indent=2) if allocation_data else 'Not specified'}
- Revenue Recognition Methods: {recognition_methods}
- Transaction Complexity: {complexity_summary}

YOUR TASK:
Write a concise financial impact analysis. Your analysis, including the narrative description and journal entries, MUST be based **exclusively** on the `STRUCTURED ANALYSIS DATA` provided. This data represents the official conclusions from the 5-step analysis, which was grounded in the knowledge hierarchy.

**CRITICAL CALCULATION RULE: DO NOT RECALCULATE AMOUNTS. Use the exact Transaction Price from the STRUCTURED ANALYSIS DATA above. Use the exact Allocation Details from Step 4 for journal entries. The amounts have already been calculated using the hybrid extract-then-calculate system and are 100% reliable.**

**CRITICAL TAX RULE: Any sales tax collected from the customer is NOT revenue.** It must be recorded as a separate liability (e.g., 'Sales Tax Payable'). **Since the tax rate is not specified in the contract data, you MUST OMIT sales tax from the illustrative journal entries and add a brief narrative sentence stating that the entries exclude any applicable sales tax.** Do not use placeholders like `[sales tax amount]`.

**CRITICAL RULE: Be Proportional.**
- **For SIMPLE transactions** (like a standard, single-element subscription): Provide a very brief, 1-2 sentence summary of the accounting treatment and one summary journal entry. DO NOT write a lengthy narrative or explain basic accounting principles.
- ** For COMPLEX transactions**, follow this structure:**

1.  **Financial Statement Impact:** In a narrative paragraph, describe the expected impact on the income statement and balance sheet (e.g., creation of contract assets or deferred revenue liabilities).

2.  **Illustrative Journal Entries:** Provide key journal entries using clean accounting format. Your entries MUST be balanced (Total Debits = Total Credits).
**REQUIRED JOURNAL ENTRIES - Show ALL of the following:**
- **Contract signing/initial invoicing:** Establish the total receivable and corresponding deferred revenue liability for the entire contract value.
- **Revenue recognition for EACH distinct performance obligation:** Show separate journal entries for each performance obligation identified in Step 2, whether point-in-time or over-time recognition.

**Example format for each performance obligation:**

**[Date]:**
Dr. [Asset/Expense Account] ........... $[amount]
    Cr. [Liability/Revenue Account] ........... $[amount]
*To record [description of transaction purpose]*


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

        return f"""You are an accounting senior manager writing the final "Conclusion" section of an ASC 606 memo.

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
Write a final concluding paragraph. Your paragraph must:

1.  Reaffirm that the accounting treatment outlined in the memo is appropriate and in accordance with ASC 606.
2.  Briefly summarize the key revenue recognition approach (e.g., "revenue for the SaaS is recognized over time, while hardware is at a point in time").
3.  If significant judgments were made, you MUST briefly reference them in one sentence without repeating the details. For example: "This conclusion was reached after careful consideration of key judgments regarding SSP estimation and variable consideration, which are detailed in Section 4 of this memo."
4.  Only mention ongoing monitoring if the contract has variable elements that require it.

**CRITICAL RULE: Be Proportional and Avoid Generic Boilerplate.** Do NOT list the judgments again.

---
**IF THE TRANSACTION or Contract IS COMPLEX, follow this structure:**

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
        """Enhanced executive summary prompt with structured data extraction and clear role separation."""

        # Step 1: Contract validity assessment
        contract_exists = "Yes"
        if s1_analysis := s1.get('step1_analysis'):
            if s1_criteria := s1_analysis.get('contract_criteria_assessment'):
                failed_criteria = [c for c in s1_criteria if c.get('status') == 'Not Met']
                if failed_criteria:
                    contract_exists = "No"

        # Step 2: Performance obligations extraction  
        po_count = 0
        po_descriptions = []
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                po_count = len(s2_pos) if s2_pos else 0
                po_descriptions = [po.get('po_description', 'Unnamed PO') for po in s2_pos]

        # Step 3: Transaction price details
        total_price = "Not specified"
        has_variable_consideration = False
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                total_price = s3_price.get('total_transaction_price', 'Not specified')
                var_consideration = s3_price.get('variable_consideration')
                if var_consideration:
                    var_str = str(var_consideration).strip().lower()
                    has_variable_consideration = (
                        var_str not in ['n/a', 'not applicable', 'none', 'none identified', '']
                        and len(var_str) > 10
                        and 'variable' in var_str
                    )

        # Step 4: Allocation method
        allocation_method = "Not applicable (single performance obligation)" if po_count <= 1 else "Not specified"
        if s4_analysis := s4.get('step4_analysis'):
            if s4_details := s4_analysis.get('allocation_details'):
                if allocations := s4_details.get('allocations'):
                    if len(allocations) > 1:
                        allocation_method = "Price allocated across multiple POs based on standalone selling prices"

        # Step 5: Revenue recognition methods
        recognition_methods = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                recognition_methods = [
                    f"{po.get('performance_obligation', 'Unknown PO')}: {po.get('recognition_method', 'Unknown')}"
                    for po in s5_plan
                ]

        # Extract and filter critical judgments from all steps
        all_step_judgments = []
        for step_result in [s1, s2, s3, s4, s5]:
            if judgments := step_result.get('professional_judgments'):
                all_step_judgments.extend(judgments)

        critical_judgments = StepPrompts._filter_genuine_judgments(all_step_judgments)

        return f"""You are writing the Executive Summary for a professional ASC 606 technical accounting memo.

ANALYSIS CONTEXT:
- Contract Analysis: {analysis_title}
- Customer: {customer_name}

STRUCTURED DATA FROM 5-STEP ANALYSIS:
• ASC 606 Contract Exists: {contract_exists}
• Performance Obligations Count: {po_count}
• Performance Obligations: {po_descriptions}
• Total Transaction Price: {total_price}
• Has Variable Consideration: {"Yes" if has_variable_consideration else "No"}
• Allocation Method: {allocation_method}
• Revenue Recognition Methods: {recognition_methods}

YOUR TASK:
Synthesize the **structured data provided above** into a cohesive, executive-level summary. Your conclusions in the summary MUST be directly supported by the findings in the structured data. Do not introduce new analysis. The structured data is your single source of truth for this task, as it was derived from a rigorous application of the knowledge hierarchy (Contract → Authoritative → Interpretative).

SECTION STRUCTURE & REQUIREMENTS:

**OVERALL CONCLUSION** (2-3 sentences maximum)
- Provide the strategic, bottom-line accounting determination based on the structured data
- State the total transaction price and high-level revenue recognition approach
- Confirm ASC 606 compliance
- **Critical Rule**: This is a narrative summary, NOT a detailed listing of components

**KEY FINDINGS** (Scannable dashboard format)

**FORMATTING RULE:** For the 'KEY FINDINGS' section, use a structured bullet point format with sub-bullets where appropriate:

- ASC 606 Contract Exists: {contract_exists}
- Performance Obligations: {po_count} distinct obligation{'s' if po_count != 1 else ''}
  {chr(10).join([f'  • {po}' for po in po_descriptions]) if po_descriptions else ''}
- Transaction Price: {total_price}{' (includes variable consideration)' if has_variable_consideration else ''}
- Allocation: {allocation_method}
- Revenue Recognition:
  {chr(10).join([f'  • {method}' for method in recognition_methods]) if recognition_methods else '  • Not applicable'}
- Critical Judgments: {', '.join([j.get('judgment_title', str(j)) if isinstance(j, dict) else str(j) for j in critical_judgments]) if critical_judgments else 'None identified'}

**PROFESSIONAL STANDARDS:**
- Write with the authority and precision expected in Big 4 audit documentation
- Ensure internal consistency with the detailed 5-step analysis that preceded this summary
- Focus on decision-useful information for senior stakeholders

Use the structured data provided above to create a cohesive, executive-level summary that respects readers' time while providing comprehensive oversight of the accounting conclusions."""

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
        """Generates a highly discerning prompt for the Key Professional Judgments section with structured context."""

        # Extract structured context from step analyses for comprehensive judgment evaluation

        # Step 1: Contract criteria complexity
        contract_complexity_factors = []
        if s1_analysis := s1.get('step1_analysis'):
            if s1_criteria := s1_analysis.get('contract_criteria_assessment'):
                failed_criteria = [c for c in s1_criteria if c.get('status') == 'Not Met']
                if failed_criteria:
                    contract_complexity_factors.append(f"Failed criteria: {len(failed_criteria)}")

        # Step 2: Performance obligation complexity
        po_complexity_factors = []
        po_count = 0
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                po_count = len(s2_pos) if s2_pos else 0
                if po_count > 2:
                    po_complexity_factors.append(f"Multiple POs ({po_count})")

                # Check for distinct analysis complexity
                complex_distinct_analysis = [po for po in s2_pos if 'distinct' in str(po.get('distinct_analysis', '')).lower() and len(str(po.get('distinct_analysis', ''))) > 50]
                if complex_distinct_analysis:
                    po_complexity_factors.append("Complex distinctiveness analysis")

        # Step 3: Transaction price complexity
        price_complexity_factors = []
        total_price = "Not specified"
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                total_price = s3_price.get('total_transaction_price', 'Not specified')

                # Variable consideration complexity
                var_consideration = s3_price.get('variable_consideration')
                if var_consideration:
                    var_str = str(var_consideration).strip().lower()
                    if (var_str not in ['n/a', 'not applicable', 'none', 'none identified', ''] 
                        and len(var_str) > 20 and 'variable' in var_str):
                        price_complexity_factors.append("Variable consideration estimation")

                # Financing component complexity
                financing = s3_price.get('financing_component_analysis', '')
                if 'significant' in str(financing).lower():
                    price_complexity_factors.append("Significant financing component")

        # Step 4: Allocation complexity
        allocation_complexity_factors = []
        if s4_analysis := s4.get('step4_analysis'):
            if s4_details := s4_analysis.get('allocation_details'):
                if allocations := s4_details.get('allocations'):
                    estimation_count = sum(1 for alloc in allocations 
                                         if 'estimation' in str(alloc.get('ssp_determination', '')).lower() 
                                         or 'residual' in str(alloc.get('ssp_determination', '')).lower())
                    if estimation_count > 0:
                        allocation_complexity_factors.append(f"SSP estimation required ({estimation_count} POs)")

        # Step 5: Recognition complexity
        recognition_complexity_factors = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                over_time_count = sum(1 for po in s5_plan if 'over time' in str(po.get('recognition_method', '')).lower())
                if over_time_count > 0:
                    recognition_complexity_factors.append(f"Over time recognition ({over_time_count} POs)")

                # Check for complex progress measurement
                complex_measurement = [po for po in s5_plan if len(str(po.get('measure_of_progress', ''))) > 30]
                if complex_measurement:
                    recognition_complexity_factors.append("Complex progress measurement")

        # Extract and filter professional judgments
        all_judgments = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            judgments = step.get('professional_judgments', [])
            if judgments and isinstance(judgments, list):
                filtered = StepPrompts._filter_genuine_judgments(judgments)
                all_judgments.extend(filtered)

        # If no genuine judgments remain after filtering, provide standard statement
        if not all_judgments:
            return "RETURN_DIRECT_TEXT: The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

        # Aggregate complexity indicators for context
        all_complexity_factors = []
        if contract_complexity_factors:
            all_complexity_factors.extend(contract_complexity_factors)
        if po_complexity_factors:
            all_complexity_factors.extend(po_complexity_factors)
        if price_complexity_factors:
            all_complexity_factors.extend(price_complexity_factors)
        if allocation_complexity_factors:
            all_complexity_factors.extend(allocation_complexity_factors)
        if recognition_complexity_factors:
            all_complexity_factors.extend(recognition_complexity_factors)
        return f"""You are writing the "Key Professional Judgments" section of a Big 4 quality ASC 606 memo. This section MUST represent only the most complex, high-judgment areas.

STRUCTURED ANALYSIS CONTEXT:
- Performance Obligations: {po_count} identified
- Transaction Price: {total_price}
- Complexity Indicators: {', '.join(all_complexity_factors) if all_complexity_factors else 'None identified'}

CANDIDATE JUDGMENTS (filtered from 5-step analysis):
{json.dumps(all_judgments, indent=2)}

YOUR TASK:
Your primary task is to **filter** the provided `CANDIDATE JUDGMENTS` and **rewrite** only the genuine ones into a professional, defensible format. A genuine judgment is one that requires significant estimation or interpretation because the contract is silent or the authoritative guidance is not definitive.

For each genuine judgment you identify, you must provide a full, detailed 'Rationale' paragraph explaining *why* it is a judgment. This section is the single source of truth for the detailed justification of all professional judgments made.

Use the KNOWLEDGE HIERARCHY REFERENCE to structure your reasoning.

**KNOWLEDGE HIERARCHY REFERENCE:**
A genuine judgment exists when:
- **Contract Text** is ambiguous or silent on key terms
- **Authoritative Guidance** (ASC 606) provides general principles but lacks specific direction
- **Interpretative Guidance** (e.g., Big 4 publications) must be relied upon for practical application
- **Management Estimation** is required to bridge gaps in the hierarchy

---
### EXAMPLE OF DESIRED OUTPUT:

- **Estimating the Standalone Selling Price (SSP) for the On-Premise License:**
  **Rationale:** A significant judgment was required because the **contract text** does not specify a price for the license, and the **authoritative guidance** in ASC 606-10-32-33 allows for estimation when an observable price is unavailable. We referenced **interpretative guidance** (e.g., from EY) which suggests the residual approach is appropriate in such cases. This forced an estimation, making it a key judgment.

---
Begin your work. Your precision is critical.
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

        # Route to the correct helper function based on step number
        if step_number == 2:
            return StepPrompts._format_step2_with_filtering(
                step_data, step_name, conclusion, analysis_points)
        elif step_number == 3:
            return StepPrompts._format_step3_with_filtering(
                step_data, step_name, conclusion, analysis_points)
        elif step_number in [1, 4, 5]:
            return StepPrompts._format_general_step_with_filtering(
                step_data, step_name, conclusion, analysis_points, step_number)

        # Fallback for any unhandled steps (should not be reached)
        markdown_sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            "**Detailed Analysis:**\n"
        ]
        if analysis_points:
            for i, point in enumerate(analysis_points):
                # Simplified fallback logic
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text', 'No analysis text provided.')
                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(analysis_text)

        final_content = [section for section in markdown_sections if str(section).strip()]
        return "\n\n".join(final_content)

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
            "**Detailed Analysis:**\n"
        ]

        all_points = []
        transaction_components = step_data.get('step3_analysis', {}).get('transaction_price_components', {})
        title_map = {
            'total_transaction_price': 'Total Transaction Price', 'fixed_consideration': 'Fixed Consideration',
            'variable_consideration': 'Variable Consideration', 'financing_component_analysis': 'Significant Financing Component',
            'noncash_consideration_analysis': 'Noncash Consideration', 'consideration_payable_to_customer_analysis': 'Consideration Payable to Customer',
            'other_considerations_analysis': 'Other Considerations'
        }
        processed_values = set()

        for key, analysis_text in transaction_components.items():
            is_not_applicable = (not analysis_text or str(analysis_text).strip().lower() in ('n/a', 'not applicable', '') or
                               str(analysis_text).strip().lower().startswith('n/a') or len(str(analysis_text).strip()) < 3)
            if not is_not_applicable:
                text_str = str(analysis_text).strip()
                if key in ['fixed_consideration', 'total_transaction_price']:
                    if text_str in processed_values: continue
                    processed_values.add(text_str)
                    if len(text_str) < 30: continue
                topic_title = title_map.get(key, key.replace('_', ' ').title())
                all_points.append({'topic_title': topic_title, 'analysis_text': analysis_text, 'evidence_quotes': []})

        if analysis_points:
            all_points.extend(analysis_points)

        if not all_points:
            markdown_sections.append("Only basic fixed consideration was identified in this contract.")
        else:
            for i, point in enumerate(all_points):
                markdown_sections.append(f"**{i+1}. {point.get('topic_title', 'Analysis Point')}**")
                markdown_sections.append(str(point.get('analysis_text', 'No analysis text provided.')))
                if evidence_quotes := point.get('evidence_quotes', []):
                    if isinstance(evidence_quotes, list):
                        for quote in evidence_quotes:
                            if isinstance(quote, str) and quote:
                                markdown_sections.append(f"> {quote}")

        final_content = [section for section in markdown_sections if str(section).strip()]
        return "\n\n".join(final_content)

    @staticmethod
    def _format_step2_with_filtering(step_data: dict, step_name: str,
                                     conclusion: str,
                                     analysis_points: list) -> str:
        """Apply the Auditor's Method to Step 2: Filter out N/A components."""
        markdown_sections = [
            f"### Step 2: {step_name}", f"**Conclusion:**\n{conclusion}",
            "**Detailed Analysis:**\n"
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

        final_content = [section for section in markdown_sections if str(section).strip()]
        return "\n\n".join(final_content)

    @staticmethod
    def _format_general_step_with_filtering(step_data: dict, step_name: str,
                                            conclusion: str,
                                            analysis_points: list,
                                            step_number: int) -> str:
        """Apply the Auditor's Method to Steps 1, 4, and 5: Filter out N/A components and format structured data."""
        markdown_sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}",
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

        final_content = [section for section in markdown_sections if str(section).strip()]
        return "\n\n".join(final_content)