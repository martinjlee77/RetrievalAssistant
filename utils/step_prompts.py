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
        """Generates proportional financial impact prompt based on structured data analysis."""
        import json
        
        # Extract structured data from each step
        
        # Step 1: Contract validity
        contract_valid = "Valid"
        if s1_criteria := s1.get('contract_criteria_assessment'):
            failed_criteria = [c for c in s1_criteria if c.get('status') == 'Not Met']
            if failed_criteria:
                contract_valid = f"Invalid - Failed: {', '.join([c.get('criterion', 'Unknown') for c in failed_criteria])}"
        
        # Step 2: Performance obligations
        performance_obligations = []
        if s2_pos := s2.get('performance_obligations'):
            performance_obligations = [po.get('po_description', 'Unknown PO') for po in s2_pos if po.get('is_distinct') == 'Yes']
        po_summary = f"{len(performance_obligations)} distinct performance obligations: {', '.join(performance_obligations)}" if performance_obligations else "Performance obligations not clearly identified"
        
        # Step 3: Transaction price components
        transaction_price_data = {}
        if s3_price := s3.get('transaction_price_components'):
            transaction_price_data = {
                'total_price': s3_price.get('total_transaction_price', 'Not specified'),
                'fixed_consideration': s3_price.get('fixed_consideration', 'Not specified'),
                'variable_consideration': s3_price.get('variable_consideration', []),
                'financing_component': s3_price.get('financing_component_analysis', 'None identified')
            }
        
        # Step 4: Allocation details  
        allocation_data = s4.get('allocation_details', {})
        
        # Step 5: Revenue recognition plan
        recognition_methods = []
        if s5_plan := s5.get('revenue_recognition_plan'):
            recognition_methods = [(po.get('performance_obligation', 'Unknown'), 
                                  po.get('recognition_method', 'Unknown'),
                                  po.get('measure_of_progress', 'Unknown')) for po in s5_plan]

        # Enhanced logic to determine transaction complexity using structured data
        is_complex = (
            len(performance_obligations) > 1 or  # Multiple POs
            (transaction_price_data.get('variable_consideration') and 
             len(transaction_price_data.get('variable_consideration', [])) > 0) or  # Variable consideration exists
            'significant financing component' in transaction_price_data.get('financing_component', '').lower() or  # Financing component
            any('Over Time' in method[1] for method in recognition_methods)  # Over time recognition
        )

        return f"""You are a corporate controller writing the "Financial Impact" section of an ASC 606 memo. Your response must be concise and proportional to the complexity of the transaction.

STRUCTURED ANALYSIS DATA:
- Contract Status: {contract_valid}
- Performance Obligations: {po_summary}
- Transaction Price: {transaction_price_data.get('total_price', 'Not specified')}
- Variable Consideration: {json.dumps(transaction_price_data.get('variable_consideration', []), indent=2) if transaction_price_data.get('variable_consideration') else 'None'}
- Allocation Details: {json.dumps(allocation_data, indent=2) if allocation_data else 'Not specified'}
- Revenue Recognition Methods: {recognition_methods}
- Is transaction complex? {"Yes" if is_complex else "No"}

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
        """Generates a proportional and meaningful conclusion prompt using structured data."""

        # Extract structured data for conclusion
        
        # Performance obligations count
        po_count = 0
        if s2_pos := s2.get('performance_obligations'):
            po_count = len([po for po in s2_pos if po.get('is_distinct') == 'Yes'])
        
        # Variable consideration check
        has_variable_consideration = False
        if s3_price := s3.get('transaction_price_components'):
            has_variable_consideration = bool(s3_price.get('variable_consideration') and 
                                            len(s3_price.get('variable_consideration', [])) > 0)
        
        # Financing component check
        has_financing_component = False
        if s3_price := s3.get('transaction_price_components'):
            financing_analysis = s3_price.get('financing_component_analysis', '').lower()
            has_financing_component = 'significant financing component' in financing_analysis
        
        # Over time recognition check
        has_over_time_recognition = False
        if s5_plan := s5.get('revenue_recognition_plan'):
            has_over_time_recognition = any('Over Time' in po.get('recognition_method', '') for po in s5_plan)

        # Enhanced logic using structured data
        is_complex = (
            po_count > 1 or
            has_variable_consideration or
            has_financing_component or
            has_over_time_recognition
        )

        return f"""You are an accounting manager writing the final "Conclusion and Recommendations" section of an ASC 606 memo. Your response must be professional, decisive, and proportional to the complexity of the transaction.

STRUCTURED ANALYSIS DATA:
- Performance Obligations Count: {po_count}
- Has Variable Consideration: {"Yes" if has_variable_consideration else "No"}
- Has Financing Component: {"Yes" if has_financing_component else "No"}
- Has Over Time Recognition: {"Yes" if has_over_time_recognition else "No"}
- Transaction Complexity: {"Complex" if is_complex else "Simple"}

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
        """Generates enhanced executive summary using structured data from all steps."""
        import json
        
        # Extract structured data for executive summary
        
        # Step 1: Contract validity
        contract_status = "Valid"
        failed_criteria = []
        if s1_criteria := s1.get('contract_criteria_assessment'):
            failed_criteria = [c.get('criterion', 'Unknown') for c in s1_criteria if c.get('status') == 'Not Met']
            if failed_criteria:
                contract_status = f"Invalid - Failed criteria: {', '.join(failed_criteria)}"
        
        # Step 2: Performance obligations summary
        po_count = 0
        po_descriptions = []
        if s2_pos := s2.get('performance_obligations'):
            distinct_pos = [po for po in s2_pos if po.get('is_distinct') == 'Yes']
            po_count = len(distinct_pos)
            po_descriptions = [po.get('po_description', 'Unnamed PO') for po in distinct_pos]
        
        # Step 3: Transaction price details
        total_price = "Not specified"
        has_variable_consideration = False
        if s3_price := s3.get('transaction_price_components'):
            total_price = s3_price.get('total_transaction_price', 'Not specified')
            has_variable_consideration = bool(s3_price.get('variable_consideration') and 
                                            len(s3_price.get('variable_consideration', [])) > 0)
        
        # Step 5: Revenue recognition methods
        recognition_summary = []
        critical_judgments = []
        if s5_plan := s5.get('revenue_recognition_plan'):
            for po_plan in s5_plan:
                method = po_plan.get('recognition_method', 'Unknown')
                po_name = po_plan.get('performance_obligation', 'Unknown PO')
                recognition_summary.append(f"{po_name}: {method}")
                
                # Extract critical judgments
                if 'Over Time' in method and po_plan.get('justification'):
                    critical_judgments.append(f"Over time recognition criteria for {po_name}")
        
        # Identify key judgments
        if has_variable_consideration:
            critical_judgments.append("Variable consideration estimation and constraint analysis")
        if po_count > 1:
            critical_judgments.append("Distinct performance obligation assessment")
        
        return f"""Write a professional executive summary for an ASC 606 technical accounting memo using a structured dashboard format.

STRUCTURED ANALYSIS DATA:
- Analysis: {analysis_title}
- Customer: {customer_name}
- Contract Status: {contract_status}
- Performance Obligations Count: {po_count}
- Performance Obligations: {po_descriptions}
- Total Transaction Price: {total_price}
- Has Variable Consideration: {"Yes" if has_variable_consideration else "No"}
- Revenue Recognition Methods: {recognition_summary}
- Key Judgment Areas: {critical_judgments}

Create an executive summary using this professional structure:

**OVERALL CONCLUSION**
[Single paragraph stating overall ASC 606 compliance and revenue recognition approach based on the structured data above]

**KEY FINDINGS**
• Contract Status: {contract_status}
• Performance Obligations: {po_count} distinct obligations - {', '.join(po_descriptions[:3])}{'...' if len(po_descriptions) > 3 else ''}
• Transaction Price: {total_price}{' (includes variable consideration)' if has_variable_consideration else ''}
• Revenue Recognition: {', '.join(recognition_summary[:2])}{'...' if len(recognition_summary) > 2 else ''}
• Critical Judgments: {', '.join(critical_judgments[:2])}{'...' if len(critical_judgments) > 2 else ''}

**FINANCIAL IMPACT SUMMARY**
• Expected Revenue: [Derive from transaction price and recognition timing]
• Implementation Requirements: [Base on complexity - simple vs multi-PO arrangements]

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
        """Generate consistency check prompt using structured data from all 5 steps."""
        import json

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