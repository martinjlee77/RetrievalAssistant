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
            critical_rules,
            f'JSON STRUCTURE: {{"executive_conclusion": "A clear, one-to-three sentence conclusion for this entire step. This is the \'bottom line\'.", "{step_schema_name}": {step_schema_definition}, "professional_judgments": [ "A list of strings describing conclusions that required significant professional judgment for this step. If none, return an empty list []." ], "analysis_points": [ {{ "issue": "Brief statement of the accounting issue addressed", "analysis": "Detailed reasoning connecting contract language to accounting guidance", "conclusion": "Definitive answer" }} ] }}'
        ]

        return '\n\n'.join(prompt_parts)

    @staticmethod
    def _get_critical_rules_for_step(step_number: int, contract_text: str) -> str:
        """Returns step-specific critical rules and guidance"""
        base_rule = """**CRITICAL REQUIREMENTS FOR ANALYSIS_POINTS:**
1. **Issue:** State the specific accounting question or challenge for this step.
2. **Analysis:** Provide detailed reasoning that explicitly connects the contract's language to the applicable accounting guidance.
    - **Crucially, you must then explicitly connect the contract language to the accounting guidance.** Explain *how* the specific words in the contract cause the arrangement to either meet or fail the criteria in the guidance. Do not just state the facts and the rule; explain the reasoning that links them. One or two sentences are not enough; you must provide a thorough explanation and support for the conclusion.
3.  **Conclusion:** Provide a definitive answer to the issue raised.

**ANALYSIS TEMPLATE:**
"The primary accounting question is [state the specific issue, e.g., 'whether the professional services are distinct from the main product'] (Issue). The contract includes specific language stating, '[Quote the relevant key phrase or sentence from the contract source text]'. The authoritative guidance in ASC XXX-XX-XX-X requires that [paraphrase the relevant accounting rule or criteria]. In this case, the quoted contract language directly impacts this assessment because [explain the reasoning that connects the quote to the rule; for instance, 'the service is described as being integral to the product's core function']. This indicates that the two promises are highly interrelated and not separately identifiable in the context of the contract (Analysis). Therefore, based on this analysis, we conclude that [state the definitive conclusion, e.g., 'the professional services and the product must be accounted for as a single performance obligation'] (Conclusion)."
"""

        step_specific_rules = {
            1: "Focus on contract existence and enforceability criteria per ASC 606-10-25-1.",
            2: "Analyze distinct goods/services using the two-pronged test: capable of being distinct AND separately identifiable.",
            3: "Consider all transaction price components including variable consideration, financing, and noncash consideration.",
            4: "Apply standalone selling price allocation methodology. If there is only one performance obligation identified in Step 2, the `analysis_points` array MUST be empty `[]`. The `step4_overall_conclusion` is sufficient.",
            5: "Determine timing of revenue recognition - over time vs. point in time criteria."
        }

        return f"{base_rule}\n\n**STEP {step_number} SPECIFIC FOCUS:**\n{step_specific_rules.get(step_number, '')}"

    @staticmethod
    def _get_schema_for_step(step_number: int) -> str:
        """Returns the JSON schema definition for each step"""
        schemas = {
            1: '{ "contract_parties": "List the contracting parties", "contract_enforceable": "Yes/No with brief justification", "step1_overall_conclusion": "Provide a single, definitive summary statement for all of Step 1." }',
            2: '{ "performance_obligations": [ { "po_description": "Description of the performance obligation", "distinct_analysis": "Concise justification citing ASC 606-10-25-19 criteria", "conclusion": "Distinct or Not Distinct" } ], "step2_overall_conclusion": "Provide a single, definitive summary statement for all of Step 2." }',
            3: '{ "transaction_price_components": { "fixed_consideration": "Amount in dollars", "variable_consideration": ["List any variable elements"], "financing_component_analysis": "Assessment of significant financing component" }, "step3_overall_conclusion": "Provide a single, definitive summary statement for all of Step 3." }',
            4: '{ "allocation_method": "Description of allocation approach used", "step4_overall_conclusion": "Provide a single, definitive summary statement for all of Step 4." }',
            5: '{ "revenue_recognition_plan": [ { "performance_obligation": "PO description", "recognition_method": "Over Time or Point in Time", "measure_of_progress": "If over time, specify measure" } ], "step5_overall_conclusion": "Provide a single, definitive summary statement for all of Step 5." }'
        }
        return schemas.get(step_number, '{}')

    # === MEMO GENERATION PROMPTS ===

    @staticmethod
    def get_executive_summary_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str, contract_data=None) -> str:
        """Enhanced executive summary prompt with structured data extraction"""
        
        # Extract structured data from analysis steps
        contract_exists = s1.get('step1_analysis', {}).get('contract_enforceable', 'Unknown')
        
        # Performance obligations data
        performance_obligations = []
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                performance_obligations = [po.get('po_description', 'Unknown PO') for po in s2_pos]
        
        # Transaction price data
        transaction_price = 'Not specified'
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                fixed = s3_price.get('fixed_consideration', 'N/A')
                variable = s3_price.get('variable_consideration', [])
                if fixed != 'N/A':
                    transaction_price = fixed
                if variable:
                    transaction_price += f" plus variable elements: {', '.join(variable)}"
        
        # Allocation method
        allocation_method = 'Not specified'
        if s4_analysis := s4.get('step4_analysis'):
            allocation_method = s4_analysis.get('allocation_method', 'Not specified')
        
        # Recognition methods
        recognition_methods = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                recognition_methods = [(po.get('performance_obligation', 'Unknown'), 
                                      po.get('recognition_method', 'Unknown')) for po in s5_plan]

        return f"""You are an accounting senior manager writing the "Executive Summary" section of an ASC 606 memo for {memo_audience}. Your response must be professional, decisive, and provide executive-level oversight.

Using the structured data provided below, create a comprehensive executive summary with two distinct subsections:

**STRUCTURED DATA FROM ASC 606 ANALYSIS:**
- Contract Status: {contract_exists}
- Performance Obligations: {performance_obligations}
- Transaction Price: {transaction_price}
- Allocation Method: {allocation_method}
- Recognition Methods: {recognition_methods}

**OVERALL CONCLUSION** (2-3 sentences maximum)
Write a strategic, high-level narrative that provides the essential business conclusion. Focus on the overall revenue recognition approach and key business implications.

**KEY FINDINGS** (Structured dashboard format)
Present the following items as a scannable list:
• ASC 606 Contract Exists: [Yes/No based on analysis]
• Performance Obligations: [List the distinct performance obligations identified]
• Transaction Price: [State the total transaction price and key components]
• Allocation: [Briefly describe the allocation method used]
• Revenue Recognition: [Summarize the recognition timing and methods]
• Critical Judgments: [List the most significant professional judgments made, filtered for genuine complexity]

Use the structured data provided above to create a cohesive, executive-level summary that respects readers' time while providing comprehensive oversight of the accounting conclusions."""

    @staticmethod
    def get_background_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str, contract_data=None) -> str:
        """Background section prompt"""
        return f"""You are writing the "Background" section of an ASC 606 technical accounting memo for {memo_audience}.

Create a professional background section that provides essential context including:
- Nature of the business arrangement with {customer_name}
- Key contract terms and commercial structure
- Significant dates and milestones
- Any unique aspects that drive the accounting analysis

Keep this section concise (2-3 paragraphs) and focus on information that directly supports the ASC 606 analysis that follows."""

    @staticmethod
    def get_key_judgments_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """Enhanced key judgments prompt with filtering logic"""
        
        # Extract all professional judgments from steps
        all_judgments = []
        for step_data in [s1, s2, s3, s4, s5]:
            if judgments := step_data.get('professional_judgments', []):
                all_judgments.extend(judgments)
        
        # If no significant judgments found, return simple statement
        if not all_judgments or len(all_judgments) == 0:
            return "RETURN_DIRECT_TEXT: No significant professional judgments were required for this straightforward ASC 606 analysis. The contract terms were clear and the application of the standard was routine."
        
        # Filter for genuine complexity indicators
        complexity_indicators = ['estimate', 'judgment', 'assumption', 'uncertain', 'complex', 'significant', 'material', 'substantial']
        genuine_judgments = [j for j in all_judgments if any(indicator in j.lower() for indicator in complexity_indicators)]
        
        if not genuine_judgments:
            return "RETURN_DIRECT_TEXT: While the analysis involved various considerations, no significant professional judgments requiring substantial estimation or complex interpretation were identified. The accounting treatment follows established guidance in a straightforward manner."

        return f"""You are writing the "Key Professional Judgments" section of an ASC 606 memo. Focus only on judgments that involved significant estimation, complex interpretation, or material assumptions.

**JUDGMENTS IDENTIFIED:**
{chr(10).join(f"• {judgment}" for judgment in genuine_judgments)}

For each genuine judgment above:
1. Describe the accounting issue requiring judgment
2. Explain the factors considered and rationale applied
3. State the conclusion reached and its impact

**Important:** If after review you determine that none of these represent genuine professional judgments requiring significant estimation or interpretation, your entire response MUST be only: "No significant professional judgments were required for this ASC 606 analysis."

Write in professional accounting language suitable for audit documentation."""

    @staticmethod
    def get_financial_impact_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str, contract_data=None) -> str:
        """Financial impact assessment prompt"""
        
        # Extract revenue amounts and timing from analysis
        transaction_price = 'Not specified'
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                transaction_price = s3_price.get('fixed_consideration', 'Not specified')
        
        recognition_methods = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                recognition_methods = [(po.get('performance_obligation', 'Unknown'),
                                      po.get('recognition_method', 'Unknown')) for po in s5_plan]

        return f"""You are writing the "Financial Impact Assessment" section of an ASC 606 memo for {memo_audience}.

**TRANSACTION DATA:**
- Transaction Price: {transaction_price}
- Recognition Methods: {recognition_methods}
- Customer: {customer_name}

Create a comprehensive financial impact assessment covering:

1. **Revenue Recognition Timing:** Describe when and how revenue will be recognized
2. **P&L Impact:** Explain the income statement effects and timing
3. **Balance Sheet Considerations:** Note any contract assets/liabilities
4. **Comparison to Previous Treatment:** If applicable, note changes from prior accounting
5. **Material Considerations:** Highlight any significant financial implications

Focus on practical business implications and be specific about amounts and timing where possible."""

    @staticmethod
    def get_conclusion_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str, contract_data=None) -> str:
        """Generates a proportional and meaningful conclusion prompt using structured data."""

        # Extract structured data for conclusion
        performance_obligations = []
        recognition_methods = []
        if s2_analysis := s2.get('step2_analysis'):
            if s2_pos := s2_analysis.get('performance_obligations'):
                performance_obligations = [po.get('po_description', 'Unknown PO') for po in s2_pos]
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                recognition_methods = [(po.get('performance_obligation', 'Unknown'),
                                      po.get('recognition_method', 'Unknown'),
                                      po.get('measure_of_progress', 'Unknown')) for po in s5_plan]

        # Transaction price data
        transaction_price_data = {}
        if s3_analysis := s3.get('step3_analysis'):
            if s3_price := s3_analysis.get('transaction_price_components'):
                transaction_price_data = {
                    'variable_consideration': s3_price.get('variable_consideration', []),
                    'financing_component': s3_price.get('financing_component_analysis', 'None identified')
                }

        # Enhanced complexity scoring system
        complexity_score = 0
        complexity_reasons = []

        # Multiple POs with different timing
        po_methods = [method[1] for method in recognition_methods]
        if len(po_methods) > 2:
            complexity_score += 1
            complexity_reasons.append("More than two performance obligations")
        
        # Variable consideration
        var_consideration = transaction_price_data.get("variable_consideration")
        has_variable_consideration = (isinstance(var_consideration, list) and len(var_consideration) > 0) or \
                                   (isinstance(var_consideration, str) and var_consideration.lower() not in ['none', 'n/a', ''])
        if has_variable_consideration:
            complexity_score += 1
            complexity_reasons.append("Variable consideration components")

        # Mixed recognition methods
        unique_methods = set(po_methods)
        if len(unique_methods) > 1 and 'Unknown' not in unique_methods:
            complexity_score += 1
            complexity_reasons.append("Mixed revenue recognition methods")

        # For simple contracts, return standard conclusion directly
        if complexity_score == 0:
            return f"RETURN_DIRECT_TEXT: Based on our comprehensive ASC 606 analysis, the contract with {customer_name} represents a straightforward revenue arrangement. The accounting treatment follows established guidance without significant complexity or unusual judgments. Revenue recognition will proceed in accordance with the five-step model as detailed in the analysis above, providing clear and appropriate financial reporting for this transaction."

        return f"""You are an accounting senior manager writing the final "Conclusion" section of an ASC 606 memo. Your response must be professional, decisive, and proportional to the complexity of the transaction.

**TRANSACTION COMPLEXITY INDICATORS:**
- Performance Obligations: {len(performance_obligations)}
- Recognition Methods: {list(set(po_methods))}
- Variable Consideration: {'Yes' if has_variable_consideration else 'No'}
- Complexity Factors: {complexity_reasons if complexity_reasons else ['Standard transaction']}

**RECOGNITION PLAN:**
{chr(10).join(f"• {method[0]}: {method[1]} ({method[2] if method[1] == 'Over Time' else 'N/A'})" for method in recognition_methods)}

Write one comprehensive conclusion paragraph that:
1. Reaffirms the appropriateness of the ASC 606 analysis
2. Summarizes the key accounting treatment decisions
3. Notes any ongoing monitoring or implementation considerations
4. Provides final assurance on the accounting approach

Begin writing the "Conclusion" section. Do not add any other text, summaries, or boilerplate language."""

    @staticmethod
    def format_step_detail_as_markdown(step_data: Dict[str, Any], step_number: int, step_name: str) -> str:
        """Formats individual step analysis as detailed markdown for the memo"""
        if not step_data:
            return f"### Step {step_number}: {step_name}\n*No analysis data available*"
        
        conclusion = step_data.get('executive_conclusion', 'No conclusion was provided.')
        analysis_points = step_data.get('analysis_points', [])
        
        # Start with the main heading and the upfront conclusion
        sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            ""
        ]
        
        # Add step-specific details
        if step_number == 3:
            return StepPrompts._format_step3_details(step_data, step_name, conclusion, analysis_points)
        elif step_number == 2:
            return StepPrompts._format_step2_details(step_data, step_name, conclusion, analysis_points)
        else:
            return StepPrompts._format_generic_step_details(step_data, step_name, conclusion, analysis_points, step_number)

    @staticmethod
    def _format_step3_details(step_data: Dict[str, Any], step_name: str, conclusion: str, analysis_points: List[Dict]) -> str:
        """Format Step 3 with transaction price components"""
        sections = [
            f"### Step 3: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            ""
        ]
        
        # Transaction price breakdown
        step3_analysis = step_data.get('step3_analysis', {})
        if price_components := step3_analysis.get('transaction_price_components'):
            sections.extend([
                "**Transaction Price Components:**",
                f"• Fixed Consideration: {price_components.get('fixed_consideration', 'Not specified')}",
                f"• Variable Consideration: {', '.join(price_components.get('variable_consideration', [])) or 'None'}",
                f"• Financing Component: {price_components.get('financing_component_analysis', 'None identified')}",
                ""
            ])
        
        # Analysis points
        if analysis_points:
            sections.append("**Detailed Analysis:**")
            for i, point in enumerate(analysis_points, 1):
                sections.extend([
                    f"**Issue {i}:** {point.get('issue', 'Not specified')}",
                    f"**Analysis:** {point.get('analysis', 'No analysis provided')}",
                    f"**Conclusion:** {point.get('conclusion', 'No conclusion provided')}",
                    ""
                ])
        
        return "\n".join(sections)

    @staticmethod
    def _format_step2_details(step_data: Dict[str, Any], step_name: str, conclusion: str, analysis_points: List[Dict]) -> str:
        """Format Step 2 with performance obligations"""
        sections = [
            f"### Step 2: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            ""
        ]
        
        # Performance obligations details
        step2_analysis = step_data.get('step2_analysis', {})
        if pos := step2_analysis.get('performance_obligations'):
            sections.append("**Performance Obligations Identified:**")
            for i, po in enumerate(pos, 1):
                sections.extend([
                    f"**PO {i}:** {po.get('po_description', 'Not specified')}",
                    f"• Distinct Analysis: {po.get('distinct_analysis', 'No analysis provided')}",
                    f"• Conclusion: {po.get('conclusion', 'Not specified')}",
                    ""
                ])
        
        # Analysis points
        if analysis_points:
            sections.append("**Detailed Analysis:**")
            for i, point in enumerate(analysis_points, 1):
                sections.extend([
                    f"**Issue {i}:** {point.get('issue', 'Not specified')}",
                    f"**Analysis:** {point.get('analysis', 'No analysis provided')}",
                    f"**Conclusion:** {point.get('conclusion', 'No conclusion provided')}",
                    ""
                ])
        
        return "\n".join(sections)

    @staticmethod
    def _format_generic_step_details(step_data: Dict[str, Any], step_name: str, conclusion: str, analysis_points: List[Dict], step_number: int) -> str:
        """Format generic step details"""
        sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            "\n---\n",
            ""
        ]
        
        # Analysis points
        if analysis_points:
            sections.append("**Detailed Analysis:**")
            for i, point in enumerate(analysis_points, 1):
                sections.extend([
                    f"**Issue {i}:** {point.get('issue', 'Not specified')}",
                    f"**Analysis:** {point.get('analysis', 'No analysis provided')}",
                    f"**Conclusion:** {point.get('conclusion', 'No conclusion provided')}",
                    ""
                ])
        
        return "\n".join(sections)