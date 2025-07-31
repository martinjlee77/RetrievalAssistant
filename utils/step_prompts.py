"""
Enhanced step-by-step prompt templates for ASC 606 analysis.
"""

class StepPrompts:
    """Enhanced prompts with proportional complexity handling."""
    
    @staticmethod
    def get_step_info() -> dict:
        """Returns information about each ASC 606 step."""
        return {
            1: {
                "title": "Identify the Contract",
                "primary_guidance": "ASC 606-10-25-1 through 25-8",
                "description": "Contract identification and combination criteria"
            },
            2: {
                "title": "Identify Performance Obligations",
                "primary_guidance": "ASC 606-10-25-14 through 25-22",
                "description": "Distinct goods or services identification"
            },
            3: {
                "title": "Determine the Transaction Price",
                "primary_guidance": "ASC 606-10-32-2 through 32-27",
                "description": "Fixed and variable consideration determination"
            },
            4: {
                "title": "Allocate the Transaction Price",
                "primary_guidance": "ASC 606-10-32-28 through 32-41",
                "description": "Standalone selling prices and allocation methods"
            },
            5: {
                "title": "Recognize Revenue",
                "primary_guidance": "ASC 606-10-25-23 through 25-37",
                "description": "Over time vs point in time recognition criteria"
            }
        }

    @staticmethod
    def get_financial_impact_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str) -> str:
        """Generates proportional financial impact prompt based on transaction complexity."""
        
        # Robust data extraction logic
        price_details = "Not specified"
        recognition_summary = "Not specified"
        
        # ENHANCED: Prioritize structured data from Step 4 allocation
        if s4_allocation := s4.get('allocation_details'):
            import json
            try:
                if isinstance(s4_allocation, dict):
                    price_details = json.dumps(s4_allocation, indent=2)
                else:
                    price_details = str(s4_allocation)
            except (TypeError, ValueError):
                price_details = str(s4_allocation)
        # Fallback to regex extraction from Step 3
        elif s3_conclusion := s3.get('executive_conclusion', ''):
            import re
            if price_match := re.search(r'\$[\d,]+\.?\d*', s3_conclusion):
                price_details = f"Total Transaction Price: {price_match.group()}"
        
        # Get recognition summary from Step 5
        recognition_summary = s5.get('executive_conclusion', 'Not specified')

        # Logic to determine transaction complexity
        is_complex = "multiple performance obligations" in s2.get('executive_conclusion', '').lower() or \
                     "variable consideration" in s3.get('executive_conclusion', '').lower() or \
                     "financing component" in s3.get('executive_conclusion', '').lower()

        return f"""You are a corporate controller writing the "Financial Impact" section of an ASC 606 memo. Your response must be concise and proportional to the complexity of the transaction.

CONTEXT FROM ANALYSIS:
- Price & Allocation Details: {price_details}
- Revenue Recognition Summary: {recognition_summary}
- Is the transaction complex (e.g., multiple POs, variable consideration)? {"Yes" if is_complex else "No"}

YOUR TASK:
Write a concise financial impact analysis.

**CRITICAL RULE: Be Proportional.**
- **For SIMPLE transactions** (like a standard, single-element subscription): Provide a very brief, 1-2 sentence summary of the accounting treatment and one summary journal entry. DO NOT write a lengthy narrative or explain basic accounting principles.
- **For COMPLEX transactions:** Provide a more detailed analysis, including separate sections for Financial Statement Impact and Illustrative Journal Entries as described below.

---
**IF THE TRANSACTION IS COMPLEX, follow this structure:**

1.  **Financial Statement Impact:** In a narrative paragraph, describe the expected impact on the income statement and balance sheet (e.g., creation of contract assets or multiple deferred revenue liabilities).

2.  **Illustrative Journal Entries:** Provide key journal entries in a clear, tabular Markdown format. Use standard account names.

    | Date       | Account                          | Debit     | Credit    |
    |------------|----------------------------------|-----------|-----------|
    | ...        | ...                              | ...       | ...       |

3.  **Internal Control & Process Considerations:** Briefly mention any operational considerations required for accurate accounting (e.g., the need to track usage for variable revenue, or new processes to monitor the satisfaction of performance obligations over time).

---
**IF THE TRANSACTION IS SIMPLE, follow this structure:**

The $XX.XX fee will be recorded as a deferred revenue liability upon receipt and recognized as revenue on a straight-line basis over the service period.

**Illustrative Journal Entry:**
| Account                      | Debit     | Credit    |
|------------------------------|-----------|-----------|
| Cash / Accounts Receivable   | $XX.XX    |           |
| Deferred Revenue             |           | $XX.XX    |
| *To record contract inception* | | |

---

Begin writing the financial impact section, strictly adhering to the proportionality rule.
"""

    @staticmethod
    def get_conclusion_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str) -> str:
        """Generates a proportional and meaningful conclusion prompt."""

        # Logic to determine transaction complexity
        is_complex = "multiple performance obligations" in s2.get('executive_conclusion', '').lower() or \
                     "variable consideration" in s3.get('executive_conclusion', '').lower() or \
                     "financing component" in s3.get('executive_conclusion', '').lower()

        return f"""You are an accounting manager writing the final "Conclusion and Recommendations" section of an ASC 606 memo. Your response must be professional, decisive, and proportional to the complexity of the transaction.

CONTEXT FROM ANALYSIS:
- Is the transaction complex? {"Yes" if is_complex else "No"}

YOUR TASK:
Write a final concluding section for the memo, strictly adhering to the proportionality rule below.

**CRITICAL RULE: Be Proportional and Avoid Generic Boilerplate.**

---
**IF THE TRANSACTION IS COMPLEX, follow this structure:**

### Conclusion
In a single paragraph, state that the accounting treatment outlined in the memo is appropriate and in accordance with ASC 606. Briefly reiterate the core revenue recognition conclusion.

### Recommendations
Based on the analysis, provide a bulleted list of specific, practical next steps derived directly from the complexities of this contract. Focus on items like:
- "The process for estimating the variable consideration for [specific bonus] must be documented and reviewed quarterly."
- "The ERP system must be configured to handle the allocation of the transaction price to the three distinct performance obligations."

---
**IF THE TRANSACTION IS SIMPLE, your ENTIRE output must be the following two paragraphs ONLY:**

### Conclusion
The accounting treatment for this straightforward arrangement is appropriate and in accordance with ASC 606. Revenue will be recognized as described in the analysis above.

### Recommendations
It is recommended that this memorandum and the supporting contract documentation be retained as audit evidence for the transaction. No other specific actions are required as a result of this analysis.

---

Begin writing the "Conclusion and Recommendations" section. Do not add any other text, summaries, or boilerplate language.
"""

    @staticmethod 
    def get_enhanced_executive_summary_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, analysis_title: str, customer_name: str) -> str:
        """Generates enhanced executive summary with professional dashboard format."""
        
        conclusions = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            conclusion = step.get('executive_conclusion', 'N/A')
            conclusions.append(f"Step {i}: {conclusion}")
        
        return f"""Write a professional executive summary for an ASC 606 technical accounting memo using a structured dashboard format.

ANALYSIS RESULTS:
- Analysis: {analysis_title}
- Customer: {customer_name}
- Step Conclusions: {chr(10).join(conclusions)}

Create an executive summary using this professional structure:

**OVERALL CONCLUSION**
[Single paragraph stating overall ASC 606 compliance and revenue recognition approach]

**KEY FINDINGS**
• Contract Status: [Valid/Invalid under ASC 606-10-25-1]
• Performance Obligations: [Number and nature of distinct obligations]
• Transaction Price: [Amount and any variable consideration]
• Revenue Recognition: [Over time/Point in time with timing]
• Critical Judgments: [1-2 most significant accounting decisions]

**FINANCIAL IMPACT SUMMARY**
• Expected Revenue: [Amount and timing]
• Implementation Requirements: [Key operational changes needed]

Keep this professional, concise, and focused on executive-level insights."""

    @staticmethod
    def get_step1_schema() -> str:
        """Returns Step 1 specific JSON schema for contract criteria assessment."""
        return '"contract_criteria_assessment": [\n    {\n      "criterion": "Approval and Commitment",\n      "status": "Met/Not Met",\n      "justification": "Analysis based on ASC 606-10-25-1(a)..."\n    },\n    {\n      "criterion": "Identification of Rights",\n      "status": "Met/Not Met", \n      "justification": "Analysis based on ASC 606-10-25-1(b)..."\n    },\n    {\n      "criterion": "Identification of Payment Terms",\n      "status": "Met/Not Met",\n      "justification": "Analysis based on ASC 606-10-25-1(c)..."\n    },\n    {\n      "criterion": "Commercial Substance", \n      "status": "Met/Not Met",\n      "justification": "Analysis based on ASC 606-10-25-1(d)..."\n    },\n    {\n      "criterion": "Collectibility",\n      "status": "Met/Not Met",\n      "justification": "Analysis based on ASC 606-10-25-1(e)..."\n    }\n  ],\n  '

    @staticmethod
    def get_step2_schema() -> str:
        """Returns Step 2 specific JSON schema for performance obligations assessment."""
        return '"performance_obligations": [\n    {\n      "po_description": "Description of the performance obligation",\n      "is_distinct": "Yes/No",\n      "distinct_analysis": "Justification based on ASC 606-10-25-19: (a) capable of being distinct and (b) separately identifiable in the contract context."\n    }\n  ],\n  '

    @staticmethod  
    def get_step3_schema() -> str:
        """Returns Step 3 specific JSON schema for transaction price components."""
        return '"transaction_price_components": {\n    "fixed_consideration": "Amount and description",\n    "variable_consideration": [\n      {\n        "type": "e.g., Performance Bonus, Sales-Based Royalty, Discount",\n        "estimated_amount": "Amount or \'Not applicable\'",\n        "estimation_method": "Expected Value / Most Likely Amount / Not applicable",\n        "constraint_analysis": "Analysis of variable consideration constraint per ASC 606-10-32-11."\n      }\n    ],\n    "financing_component_analysis": "Analysis of any significant financing component per ASC 606-10-32-15.",\n    "total_transaction_price": "Total estimated transaction price."\n  },\n  '

    @staticmethod
    def get_step4_schema() -> str:
        """Returns Step 4 specific JSON schema for allocation details."""
        return '"allocation_details": {\n    "total_transaction_price": "The total amount from Step 3",\n    "allocations": [\n      {\n        "performance_obligation": "Description of the performance obligation from Step 2",\n        "standalone_selling_price": "SSP amount and estimation method",\n        "allocated_amount": "Amount allocated to this performance obligation"\n      }\n    ]\n  },\n  '

    @staticmethod
    def get_step5_schema() -> str:
        """Returns Step 5 specific JSON schema for revenue recognition plan."""
        return '"revenue_recognition_plan": [\n    {\n      "performance_obligation": "Name of the PO from Step 2",\n      "recognition_method": "Over Time / Point in Time",\n      "justification": "If \'Over Time\', state which of the three criteria in ASC 606-10-25-27 is met. If \'Point in Time\', discuss transfer of control indicators per ASC 606-10-25-30.",\n      "measure_of_progress": "If \'Over Time\', describe the method (e.g., straight-line, input/output method). If \'Point in Time\', state timing of control transfer."\n    }\n  ],\n  '

    @staticmethod
    def get_step_specific_analysis_prompt(step_number: int, step_title: str, step_guidance: str, 
                                        contract_text: str, rag_context: str, 
                                        contract_data=None, debug_config=None) -> str:
        """Generate step-specific analysis prompt that requests narrative, thematically-grouped JSON output."""
        
        # Get step-specific schema
        step_specific_json_field = ""
        if step_number == 1:
            step_specific_json_field = StepPrompts.get_step1_schema()
        elif step_number == 2:
            step_specific_json_field = StepPrompts.get_step2_schema()
        elif step_number == 3:
            step_specific_json_field = StepPrompts.get_step3_schema()
        elif step_number == 4:
            step_specific_json_field = StepPrompts.get_step4_schema()
        elif step_number == 5:
            step_specific_json_field = StepPrompts.get_step5_schema()
        
        return f"""You are an expert technical accountant specializing in ASC 606. Your task is to analyze a contract for Step {step_number}: {step_title}.

PRIMARY GUIDANCE FOR THIS STEP: {step_guidance}

AUTHORITATIVE & INDUSTRY GUIDANCE CONTEXT:
{rag_context}

CONTRACT TEXT TO ANALYZE:
{contract_text}

CONTRACT DATA:
Customer: {getattr(contract_data, 'customer_name', 'N/A') if contract_data else 'N/A'}
Analysis Focus: {getattr(contract_data, 'key_focus_areas', 'General ASC 606 compliance') if contract_data else 'General ASC 606 compliance'}

*** YOUR CRITICAL TASK ***
Analyze the contract and provide both structured step-specific assessment AND thematic narrative analysis. 

You MUST return your response as a single, well-formed JSON object with the following exact structure:
{{
  "executive_conclusion": "A clear, one-to-three sentence conclusion for this entire step. This is the 'bottom line'.",
  {step_specific_json_field}"analysis_points": [
    {{
      "topic_title": "The name of the first major theme or issue you analyzed (e.g., 'Identification of Fixed Consideration').",
      "analysis_text": "Your detailed analysis for THIS TOPIC ONLY. Explain the issue, apply the ASC 606 guidance (citing specific paragraphs like ASC 606-10-XX-XX), and introduce the contract evidence. Weave in any key considerations or judgment areas for this topic.",
      "evidence_quotes": [
        "A specific, direct quote from the contract that supports the analysis for this topic. You MUST include the source document name, formatted as: 'Quote text... (Source: [Document Name])'",
        "Another supporting quote, if applicable."
      ]
    }},
    {{
      "topic_title": "The name of the second major theme or issue (e.g., 'Assessment of Variable Consideration').",
      "analysis_text": "Your detailed analysis for this second topic...",
      "evidence_quotes": [
        "A quote supporting the second topic... (Source: [Document Name])"
      ]
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
- Fill out the step-specific structured assessment thoroughly and precisely
- Complete the structured assessment by citing relevant ASC 606 paragraphs for each element
- Ensure structured assessment connects logically to your narrative analysis points
- Aim for 2-4 analysis points per step (avoid single mega-topics or excessive fragmentation)
- Every quote MUST include source document name
- Use specific ASC 606 paragraph citations (e.g., ASC 606-10-25-1)
- Make analysis flow naturally, building from one point to the next"""

    @staticmethod
    def get_consistency_check_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """Generate consistency check prompt for all 5 steps."""
        return f"""Review the logical consistency of this ASC 606 analysis across all 5 steps:

STEP 1 - CONTRACT IDENTIFICATION:
{s1.get('executive_conclusion', 'N/A')}

STEP 2 - PERFORMANCE OBLIGATIONS:
{s2.get('executive_conclusion', 'N/A')}

STEP 3 - TRANSACTION PRICE:
{s3.get('executive_conclusion', 'N/A')}

STEP 4 - ALLOCATION:
{s4.get('executive_conclusion', 'N/A')}

STEP 5 - RECOGNITION:
{s5.get('executive_conclusion', 'N/A')}

CRITICAL REVIEW TASK:
1. Check if the number of performance obligations in Step 2 matches the allocation approach in Step 4
2. Verify that the transaction price in Step 3 aligns with the allocation amounts in Step 4
3. Ensure the recognition timing in Step 5 matches the nature of obligations identified in Step 2
4. Look for any logical contradictions between steps

Provide brief feedback on any inconsistencies found, or confirm the analysis is consistent."""

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
    def get_key_judgments_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """Generates a highly discerning prompt for the Key Professional Judgments section."""
        all_judgments = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            judgments = step.get('professional_judgments', [])
            if judgments:
                all_judgments.extend(judgments)

        # If, after stricter identification, no judgments were passed up, provide a standard statement.
        if not all_judgments:
            return "The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

        # If judgments were flagged, this prompt will act as a final quality filter.
        return f"""You are an accounting senior manager writing the "Key Professional Judgments" section of an audit-ready ASC 606 memo. You must be highly discerning. Do not mistake standard analysis for a key judgment.

CONTEXT FROM ANALYSIS:
The following key judgments were identified during the five-step analysis:
{chr(10).join(all_judgments)}

YOUR TASK:
Transform the list of judgments above into a formal, well-articulated narrative. For each key judgment, present it as a separate bullet point following this precise structure:
- **Judgment:** State the judgment clearly and concisely (e.g., "Conclusion on the Distinctness of Implementation Services").
- **Analysis:** Briefly explain the issue and the rationale for the conclusion, referencing the relevant facts from the contract.
- **Authoritative Guidance:** Explicitly cite the primary ASC 606 guidance that supports the judgment (e.g., "This conclusion is based on the criteria outlined in ASC 606-10-25-21.").

Review the list above. Write a formal summary of ONLY the items that represent a genuine professional judgment (i.e., a "gray area" requiring significant estimation or a choice between viable alternatives).

- **CRITICAL RULE:** If the items in the list above are merely restatements of standard ASC 606 application (e.g., "the service is distinct," "revenue is recognized over time for a subscription"), then DISREGARD THEM. In this case, your entire output must be only the following single sentence:
"The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

- If there are genuine judgments, present each one as a separate bullet point following this precise structure:
  - **Judgment:** State the judgment clearly.
  - **Analysis:** Explain the issue and the rationale for the conclusion.
  - **Authoritative Guidance:** Cite the specific ASC 606 guidance that supports the judgment.

Your reputation for precision is on the line. Do not overstate the complexity of a simple contract."""

    @staticmethod
    def format_step_detail_as_markdown(step_data: dict, step_number: int, step_name: str) -> str:
        """Format step analysis from narrative JSON structure into professional markdown."""
        if not step_data or not isinstance(step_data, dict):
            return f"### Step {step_number}: {step_name}\n\nNo analysis data was returned for this step.\n"

        conclusion = step_data.get('executive_conclusion', 'No conclusion was provided.')
        analysis_points = step_data.get('analysis_points', [])

        # Start with the main heading and the upfront conclusion
        markdown_sections = [
            f"### Step {step_number}: {step_name}",
            f"**Conclusion:**\n{conclusion}",
            "\n---\n",  # Visual separator
            "**Detailed Analysis:**\n"
        ]

        if not analysis_points:
            markdown_sections.append("No detailed analysis points were provided.")
        else:
            # Loop through each thematically-grouped analysis point
            for i, point in enumerate(analysis_points):
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text', 'No analysis text provided.')
                evidence_quotes = point.get('evidence_quotes', [])

                # Add the topic as a sub-heading
                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(analysis_text)

                # Add the evidence quotes for that topic
                # Add type check to prevent errors if the LLM returns a string instead of list
                if evidence_quotes and isinstance(evidence_quotes, list):
                    for quote in evidence_quotes:
                        if isinstance(quote, str):  # Ensure the item in the list is a string
                            markdown_sections.append(f"> {quote}")
                elif isinstance(evidence_quotes, str):
                    # Handle case where LLM returns a single string instead of list
                    markdown_sections.append(f"> {evidence_quotes}")

                markdown_sections.append("")  # Add a blank line for spacing before the next point

        markdown_sections.append("---\n")  # Final separator
        return "\n".join(markdown_sections)