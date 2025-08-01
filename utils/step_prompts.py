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
                "description":
                "Contract identification and combination criteria"
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
                "description":
                "Standalone selling prices and allocation methods"
            },
            5: {
                "title": "Recognize Revenue",
                "primary_guidance": "ASC 606-10-25-23 through 25-37",
                "description":
                "Over time vs point in time recognition criteria"
            }
        }

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

**CRITICAL TAX RULE: Any sales tax collected from the customer is NOT revenue or deferred revenue.** It must be recorded as a separate liability (e.g., 'Sales Tax Payable'). The journal entry should show a credit to Deferred Revenue for the pre-tax amount and a separate credit to Sales Tax Payable.

**CRITICAL RULE: Be Proportional.**
#... rest of the prompt

**CRITICAL RULE: Be Proportional.**
- **For SIMPLE transactions** (like a standard, single-element subscription): Provide a very brief, 1-2 sentence summary of the accounting treatment and one summary journal entry. DO NOT write a lengthy narrative or explain basic accounting principles.
- **For COMPLEX transactions:** Provide a more detailed analysis, including separate sections for Financial Statement Impact and Illustrative Journal Entries as described below.

---
**IF THE TRANSACTION IS COMPLEX, follow this structure:**

1.  **Financial Statement Impact:** In a narrative paragraph, describe the expected impact on the income statement and balance sheet (e.g., creation of contract assets or deferred revenue liabilities).

2.  **Illustrative Journal Entries:** Provide key journal entries in a clear, tabular Markdown format. Use standard account names.
**Focus on the most critical events, such as:**
- **The journal entry upon contract signing/initial invoicing.**
- **The journal entry to recognize the first period of revenue for 'Over Time' obligations.**
- **The journal entry to recognize revenue for a 'Point in Time' obligation.**

    | Date       | Account                          | Debit     | Credit    |
    |------------|----------------------------------|-----------|-----------|
    | ...        | ...                              | ...       | ...       |

3.  **Internal Control & Process Considerations:** Briefly mention any internal controls over financial reportin (ICFR) considerations required for accurate accounting and effective control environment (e.g., the need to track usage for variable revenue, or new processes to monitor the satisfaction of performance obligations over time).

---
**IF THE TRANSACTION IS SIMPLE, follow this structure:**

The {transaction_price_data.get('total_price', '$XX.XX')} fee will be recorded as a deferred revenue liability upon receipt and recognized as revenue on a straight-line basis over the service period.

**Illustrative Journal Entry:**
| Account                      | Debit     | Credit    |
|------------------------------|-----------|-----------|
| Cash / Accounts Receivable   | {transaction_price_data.get('total_price', '$XX.XX')}    |           |
| Deferred Revenue             |           | {transaction_price_data.get('total_price', '$XX.XX')}    |
| *To record contract inception* | | |

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

        # Professional judgments from all steps (this part was already correct)
        all_judgments = []
        for step in [s1, s2, s3, s4, s5]:
            judgments = step.get('professional_judgments', [])
            if judgments:
                all_judgments.extend(judgments)

        # Mark as complex if any complexity indicators present
        if po_count > 1 or has_variable_consideration or has_financing_component or len(all_judgments) > 0:
            is_simple_contract = False

        # For simple contracts, return standard conclusion directly
        if is_simple_contract:
            return "RETURN_DIRECT_TEXT: The accounting treatment for this straightforward arrangement is appropriate and in accordance with ASC 606. Revenue will be recognized as described in the analysis above."

        # --- End Enhanced Complexity Logic ---

        return f"""You are an accounting manager writing the final "Conclusion" section of an ASC 606 memo. Your response must be professional, decisive, and proportional to the complexity of the transaction.

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
Write a comprehensive conclusion paragraph that:
1. States that the accounting treatment outlined in the memo is appropriate and in accordance with ASC 606
2. Summarizes the key revenue recognition approach
3. Only mention significant judgments if actual professional judgments were identified in the analysis: {all_judgments}
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
        critical_judgments = []
        if s5_analysis := s5.get('step5_analysis'):
            if s5_plan := s5_analysis.get('revenue_recognition_plan'):
                for po_plan in s5_plan:
                    method = po_plan.get('recognition_method', 'Unknown')
                    po_name = po_plan.get('performance_obligation', 'Unknown PO')
                    recognition_summary.append(f"{po_name}: {method}")

                    # Extract critical judgments
                    if 'Over Time' in method and po_plan.get('justification'):
                        critical_judgments.append(
                            f"Over time recognition criteria for {po_name}")

        # Extract actual critical judgments from step analyses (no defaults)  
        all_step_judgments = []
        for step_result in [s1, s2, s3, s4, s5]:
            if step_analysis := step_result.get(f'step{[s1, s2, s3, s4, s5].index(step_result) + 1}_analysis'):
                if judgments := step_result.get('professional_judgments'):
                    all_step_judgments.extend(judgments)
        
        # Only use actual judgments found in the analysis, not defaults
        critical_judgments = all_step_judgments[:3]  # Limit to top 3 to avoid overwhelming

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
• Critical Judgments: {', '.join(critical_judgments[:2]) if critical_judgments else 'None identified at this time'}{'...' if len(critical_judgments) > 2 else ''}

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
    def get_step_specific_analysis_prompt(step_number: int,
                                          step_title: str,
                                          step_guidance: str,
                                          contract_text: str,
                                          rag_context: str,
                                          contract_data=None,
                                          debug_config=None) -> str:
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

        # Add critical override for Step 3 to prevent variable consideration hallucination
        step3_override = ""
        if step_number == 3:
            # Check if this is a simple contract (basic heuristics)
            contract_lower = contract_text.lower()
            simple_indicators = ["monthly subscription", "fixed fee", "streaming service", "$"]
            complex_indicators = ["bonus", "royalty", "percentage", "variable", "contingent"]
            
            simple_score = sum(1 for indicator in simple_indicators if indicator in contract_lower)
            complex_score = sum(1 for indicator in complex_indicators if indicator in contract_lower)
            
            if simple_score > complex_score:
                step3_override = """
**🚨 CRITICAL OVERRIDE: This appears to be a simple, fixed-price contract. You MUST follow these rules:**
- Set `variable_consideration` to "N/A" (not a detailed analysis of why there isn't any)
- Set `professional_judgments` to an empty list []
- Do NOT invent complexity where none exists
- Focus only on the fixed consideration amount

"""

        return f"""You are an expert technical accountant specializing in ASC 606. Your task is to analyze a contract for Step {step_number}: {step_title}.
{step3_override}
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
  {step_specific_json_field}
  "professional_judgments": [
    "A list of strings. For this step only, describe any conclusions that required significant professional judgment (e.g., 'Estimation of SSP for the license using the residual approach', 'Conclusion that implementation services are not distinct from the SaaS platform'). If no significant judgments were made in this step, return an empty list []."
  ],
  "analysis_points": [
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
- **🚨 MANDATORY: You MUST analyze and populate every single field in the step-specific JSON schema.** Do not skip any fields; use "N/A" only if truly not applicable.
- **FOR STEP 1: You MUST evaluate ALL FIVE criteria from ASC 606-10-25-1(a) through (e). No shortcuts or summary assessments allowed. Your response MUST include exactly 5 criteria assessments AND 5 analysis_points covering each criterion separately.**
- Fill out the step-specific structured assessment thoroughly and precisely
- Complete the structured assessment by citing relevant ASC 606 paragraphs for each element
- Ensure structured assessment connects logically to your narrative analysis points
- Aim for 2-4 analysis points per step (avoid single mega-topics or excessive fragmentation)
- For single performance obligation contracts: Keep allocation analysis concise - simply state "Entire transaction price allocated to single performance obligation" with minimal elaboration
- Every quote MUST include source document name
- Use specific ASC 606 paragraph citations (e.g., ASC 606-10-25-1)
- Make analysis flow naturally, building from one point to the next
- **CRITICAL FOR STEP 2:** 
  * If no distinct performance obligations are found, set "performance_obligations": [] and explain in analysis_points why no obligations were identified
  * For simple contracts with obvious single obligations (e.g., "product sale"), keep analysis concise but complete
  * Always include at least one performance obligation unless truly none exist (very rare)
  * Focus on the "separately identifiable" criterion which is typically the decisive factor
**- CRITICAL FOR STEP 3:**
  * **The primary analysis MUST occur within the `transaction_price_components` JSON structure.**
  * **Only use `analysis_points` for truly separate or unusual considerations not already covered by the standard components.**
  * For simple fixed-price contracts, `variable_consideration` MUST be "N/A" and `professional_judgments` MUST be an empty list []. Do not invent judgments.
**- CRITICAL FOR STEP 4:**
  * **If there is only one performance obligation, `analysis_points` should be an empty list []. The `step4_overall_conclusion` is sufficient.**
  * **Do NOT re-analyze the transaction price in Step 4.**
**- CRITICAL FOR STEP 5:**
  * **You MUST provide detailed analysis in both the JSON schema AND analysis_points. Do not use shortcuts like "No additional analysis required".**
  * **The `revenue_recognition_plan` must include specific recognition_justification for each performance obligation.**
  * **Include measure_of_progress_analysis explaining the method used (straight-line, input/output method, etc.).**

"""

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
            judgments = step.get('professional_judgments', [])
            if judgments:
                all_judgments.extend(judgments)

        # If, after stricter identification, no judgments were passed up, provide a standard statement.
        if not all_judgments:
            return "RETURN_DIRECT_TEXT: The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

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

- **CRITICAL RULE:** If the items in the list above are merely restatements of standard ASC 606 application (e.g., "the service is distinct," "revenue is recognized over time for a subscription"), then DISREGARD THEM. **Only focus on items that involve significant estimation or a choice between viable accounting alternatives.** Examples of genuine judgments include: "Estimating the standalone selling price of the license using a residual approach" or "Concluding that the performance bonus is not constrained and should be included in the transaction price." In this case (i.e., no genuine judgments), your entire output must be only the following single sentence:
"The accounting for this arrangement is considered straightforward under ASC 606 and did not require any significant professional judgments outside of the standard application of the five-step model."

- If there are genuine judgments, present each one as a separate bullet point following this precise structure:
  - **Judgment:** State the judgment clearly.
  - **Analysis:** Explain the issue and the rationale for the conclusion.
  - **Authoritative Guidance:** Cite the specific ASC 606 guidance that supports the judgment.

Your reputation for precision is on the line. Do not overstate the complexity of a simple contract."""

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
        """Apply the Auditor's Method to Step 3: Filter out N/A transaction price components."""
        markdown_sections = [
            f"### Step 3: {step_name}", f"**Conclusion:**\n{conclusion}",
            "\n---\n", "**Transaction Price Analysis:**\n"
        ]

        # Get the transaction price components from the AI analysis
        transaction_components = step_data.get('transaction_price_components',
                                               {})

        # Filter out N/A items using the Auditor's Method
        relevant_components = []
        for key, analysis_text in transaction_components.items():
            # Define what "not applicable" means
            is_not_applicable = (
                analysis_text is None
                or str(analysis_text).strip().lower() == 'n/a'
                or str(analysis_text).strip().lower() == 'not applicable'
                or str(analysis_text).strip().lower().startswith('n/a')
                or str(analysis_text).strip() == ''
                or len(str(analysis_text).strip()) < 3)

            # If the AI's analysis for this component is NOT "N/A", include it in the memo
            if not is_not_applicable:
                topic_title = key.replace('_', ' ').replace(' analysis',
                                                            '').title()
                # Special formatting for transaction price components
                if key == 'total_transaction_price':
                    topic_title = 'Total Transaction Price'
                elif key == 'fixed_consideration':
                    topic_title = 'Fixed Consideration'
                elif key == 'variable_consideration':
                    topic_title = 'Variable Consideration'
                elif key == 'financing_component_analysis':
                    topic_title = 'Significant Financing Component'
                elif key == 'noncash_consideration_analysis':
                    topic_title = 'Noncash Consideration'
                elif key == 'consideration_payable_to_customer_analysis':
                    topic_title = 'Consideration Payable to Customer'
                elif key == 'other_considerations_analysis':
                    topic_title = 'Other Considerations'

                relevant_components.append((topic_title, analysis_text))

        # Add the relevant components to the markdown
        if relevant_components:
            for topic_title, analysis_text in relevant_components:
                markdown_sections.append(f"**{topic_title}:**")
                markdown_sections.append(str(analysis_text))
        else:
            markdown_sections.append(
                "Only basic fixed consideration was identified in this contract."
            )

        # Add the regular analysis points if they exist
        if analysis_points:
            markdown_sections.append("\n**Additional Analysis:**\n")
            for i, point in enumerate(analysis_points):
                topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                analysis_text = point.get('analysis_text',
                                          'No analysis text provided.')
                evidence_quotes = point.get('evidence_quotes', [])

                markdown_sections.append(f"**{i+1}. {topic_title}**")
                markdown_sections.append(analysis_text)

                if evidence_quotes and isinstance(evidence_quotes, list):
                    markdown_sections.append(
                        "**Supporting Contract Evidence:**")
                    for quote in evidence_quotes:
                        markdown_sections.append(f"> {quote}")

        return "\n\n".join(markdown_sections)

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

                if evidence_quotes and isinstance(evidence_quotes, list):
                    markdown_sections.append(
                        "**Supporting Contract Evidence:**")
                    for quote in evidence_quotes:
                        markdown_sections.append(f"> {quote}")

        return "\n\n".join(markdown_sections)

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
    
        # NEW: Special formatting logic for Step 5
        if step_number == 5:
            plan_formatted = False
            if step5_analysis := step_data.get('step5_analysis'):
                if plan := step5_analysis.get('revenue_recognition_plan'):
                    for po_plan in plan:
                        po_name = po_plan.get('performance_obligation', 'Unknown PO')
                        method = po_plan.get('recognition_method', 'N/A')
                        justification = po_plan.get('recognition_justification', 'No justification provided.')
    
                        markdown_sections.append(f"• **{po_name} (Method: {method})**")
                        markdown_sections.append(f"  - **Justification:** {justification}")
                        plan_formatted = True
    
            if not plan_formatted:
                markdown_sections.append("No detailed revenue recognition plan was provided.")
    
            # Add analysis_points if they exist for Step 5
            if analysis_points:
                markdown_sections.append("\n**Additional Analysis Points:**\n")
                for i, point in enumerate(analysis_points):
                    topic_title = point.get('topic_title', f'Analysis Point {i+1}')
                    analysis_text = point.get('analysis_text', 'No analysis text provided.')
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
    
        # Existing logic for filtering analysis_points for Steps 1 and 4
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
            markdown_sections.append(
                "No additional analysis was required for this step.")
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