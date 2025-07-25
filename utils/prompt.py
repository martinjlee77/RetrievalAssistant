"""
Centralized Prompt Management for Multi-Standard Platform
Provides reusable prompt templates with dynamic context injection
"""
from typing import Dict, List, Any, Optional
import streamlit as st

class ASC606PromptTemplates:
    """Centralized ASC 606 prompt templates"""
    
    @staticmethod
    def get_analysis_prompt(contract_text: str, user_inputs: Optional[Dict] = None) -> str:
        """Main ASC 606 analysis prompt template"""
        
        # Load expert guidance topics from contract review questions
        expert_guidance_topics = ""
        try:
            import os
            guidance_file = "attached_assets/contract_review_questions_1752258616680.txt"
            if os.path.exists(guidance_file):
                with open(guidance_file, 'r', encoding='utf-8') as f:
                    expert_guidance_topics = f.read()
        except Exception as e:
            expert_guidance_topics = "Expert guidance not available"
        
        # Extract contract types and collectibility for context
        contract_types_info = ""
        if user_inputs and user_inputs.get('contract_types'):
            contract_types_info = f"""
        DOCUMENT TYPES PROVIDED: {', '.join(user_inputs['contract_types'])}
        Note: The uploaded documents include {', '.join(user_inputs['contract_types'])}. Consider the relationship between these document types when analyzing the arrangement.
        """
        
        collectibility_info = ""
        if user_inputs and user_inputs.get('collectibility') is not None:
            collectibility_status = "probable" if user_inputs.get('collectibility') else "not probable"
            collectibility_info = f"""
        COLLECTIBILITY ASSESSMENT: {collectibility_status}
        Important: Management has assessed that collection of consideration is {collectibility_status}. This is fundamental to Step 1 contract identification under ASC 606-10-25-1(e).
        """
        
        consideration_payable_info = ""
        if user_inputs and user_inputs.get('consideration_payable_involved'):
            details = user_inputs.get('consideration_payable_details', '')
            consideration_payable_info = f"""
        CONSIDERATION PAYABLE TO CUSTOMER: Yes
        Details: {details}
        Important: The contract includes consideration payable to the customer. This must be considered in transaction price determination per ASC 606-10-32-25.
        """
        
        # Combined contract analysis
        combined_contract_info = ""
        if user_inputs and user_inputs.get('is_combined_contract'):
            combined_contract_info = f"""
        COMBINED CONTRACT ANALYSIS: Required
        Important: Management has determined these documents should be evaluated as a single combined contract per ASC 606-10-25-9. Consider all uploaded documents as one arrangement.
        """
        
        # Contract modification analysis
        modification_info = ""
        if user_inputs and user_inputs.get('is_modification'):
            modification_info = f"""
        CONTRACT MODIFICATION: Yes
        Important: This is a contract modification/amendment. Apply ASC 606-10-25-10 through 25-13 modification accounting guidance.
        """
        
        # Build comprehensive assessment from all UI fields
        enhanced_assessment_info = ""
        assessment_elements = []
        
        # Contract basics
        if user_inputs and user_inputs.get('arrangement_description'):
            assessment_elements.append(f"Arrangement Summary: {user_inputs['arrangement_description']}")
        
        # Principal vs Agent
        if user_inputs and user_inputs.get('principal_agent_involved'):
            principal_details = user_inputs.get('principal_agent_details', '')
            assessment_elements.append(f"Principal vs Agent Analysis Required: {principal_details}")
        
        # Variable consideration
        if user_inputs and user_inputs.get('variable_consideration_involved'):
            variable_details = user_inputs.get('variable_consideration_details', '')
            assessment_elements.append(f"Variable Consideration Present: {variable_details}")
        
        # Financing component
        if user_inputs and user_inputs.get('financing_component_involved'):
            financing_details = user_inputs.get('financing_component_details', '')
            assessment_elements.append(f"Significant Financing Component: {financing_details}")
        
        # Noncash consideration
        if user_inputs and user_inputs.get('noncash_consideration_involved'):
            noncash_details = user_inputs.get('noncash_consideration_details', '')
            assessment_elements.append(f"Noncash Consideration Present: {noncash_details}")
        
        # SSP assessment
        if user_inputs and user_inputs.get('ssp_represents_contract_price') is not None:
            ssp_status = "Yes" if user_inputs.get('ssp_represents_contract_price') else "No" 
            assessment_elements.append(f"Contract Prices Represent SSP: {ssp_status}")
        
        # Revenue recognition timing
        if user_inputs and user_inputs.get('revenue_recognition_timing_details'):
            timing_details = user_inputs.get('revenue_recognition_timing_details')
            assessment_elements.append(f"Revenue Recognition Timing: {timing_details}")
            
        if assessment_elements:
            enhanced_assessment_info = f"""
        DETAILED ASSESSMENT INPUTS:
        {chr(10).join(f"• {element}" for element in assessment_elements)}
        """
        
        # Build steering information for AI focus
        steering_info = ""
        if user_inputs:
            # Key focus areas - most important steering input
            if user_inputs.get('key_focus_areas'):
                steering_info += f"""
        SPECIFIC FOCUS AREAS (HIGH PRIORITY):
        {user_inputs['key_focus_areas']}
        
        Important: The user has specifically requested focus on the above areas. Pay special attention to these questions/clauses/risks and provide detailed analysis with supporting citations.
        """
            
            # Audience tailoring
            memo_audience = user_inputs.get('memo_audience', 'Technical Accounting Team / Audit File')
            if memo_audience == 'Management Review':
                steering_info += """
        MEMO AUDIENCE: Management Review
        - Focus on key judgments, financial impact, and business implications
        - Use less technical jargon and emphasize the "so what" for decision-makers
        - Summarize critical conclusions upfront
        """
            elif memo_audience == 'Deal Desk / Sales Team':
                steering_info += """
        MEMO AUDIENCE: Deal Desk / Sales Team
        - Focus on explaining revenue recognition impact of specific contract terms
        - Translate complex accounting rules into practical guidance for deal structuring
        - Explain how different clauses affect revenue timing
        """
            else:  # Technical Accounting Team / Audit File (default)
                steering_info += """
        MEMO AUDIENCE: Technical Accounting Team / Audit File
        - Provide deep technical compliance and audit readiness
        - Include detailed step-by-step reasoning and precise ASC 606 citations
        - Use full technical detail suitable for expert accountants and auditors
        """
            
            # Materiality threshold
            if user_inputs.get('materiality_threshold'):
                threshold = user_inputs['materiality_threshold']
                steering_info += f"""
        MATERIALITY THRESHOLD: {threshold:,} ({user_inputs.get('currency', 'USD')})
        - Focus detailed analysis on contract elements exceeding this threshold
        - Note materiality of bonuses, penalties, discounts, and other variable elements
        """
        
        return f"""You are a senior technical accountant from a Big 4 firm, tasked with preparing an audit-quality revenue recognition memo.

        Your analysis must be guided by the comprehensive list of topics and questions detailed in the 'Expert Reference Guide' below. This guide sets the **minimum standard** for a complete and professional analysis.

        **EXPERT REFERENCE GUIDE (Minimum Scope of Analysis):**
        ---
        {expert_guidance_topics}
        ---

        **YOUR TASK:**
        Analyze the provided contract text below. Write a professional accounting memo that follows the 5-step ASC 606 model. As you write your analysis for each of the 5 steps, you must address all **relevant topics** from the Expert Reference Guide.

        **Crucially, you are not limited to the guide. You must also identify and analyze any other unique provisions, risks, or terms within this specific contract that could impact revenue recognition under ASC 606, even if they are not explicitly listed in the guide.**

        - If a topic from the guide is relevant to the contract, discuss it in your analysis with supporting quotes and citations.
        - If a topic from the guide is **not applicable** (e.g., the contract has no significant financing component), you must explicitly state that it was considered and is not present. This demonstrates thoroughness.

        **CONTRACT TEXT TO ANALYZE:**
        ---
        {contract_text}
        ---

        {contract_types_info}
        {collectibility_info}
        {consideration_payable_info}
        {combined_contract_info}
        {modification_info}
        {enhanced_assessment_info}
        {steering_info}
        
        Provide a comprehensive analysis following these steps:
        1. Contract Identification (ASC 606-10-25-1)
        2. Performance Obligations (ASC 606-10-25-14)  
        3. Transaction Price (ASC 606-10-32-2)
        4. Allocation (ASC 606-10-32-28)
        5. Recognition (ASC 606-10-25-23)
        
        For each step, provide:
        - Analysis and conclusion
        - Supporting quotes from the contract
        - Relevant ASC 606 citations
        - Professional judgment rationale
        
        When analyzing multiple document types (MSA + SOW, Purchase Orders, Amendments, etc.), 
        consider how they work together to form the complete contractual arrangement.
        
        Pay special attention to:
        - Collectibility assessment provided by management
        - Contract identification criteria (ASC 606-10-25-1)
        - Combined contract evaluation per ASC 606-10-25-9 (if applicable)
        - Contract modification accounting per ASC 606-10-25-10 (if applicable)
        - Performance obligation identification and timing
        - Variable consideration estimates and constraints
        - Consideration payable to customer per ASC 606-10-32-25 (if applicable)
        - Significant financing components per ASC 606-10-32-15 (if applicable)
        - Material rights per ASC 606-10-55-42 (if applicable)
        - Customer options for additional goods/services (if applicable)
        
        Format your response in professional memo style suitable for audit workpapers.
        """
    
    @staticmethod
    def get_memo_generation_prompt(analysis_data: Dict) -> str:
        """Professional memo generation prompt"""
        return f"""
        Generate a comprehensive technical accounting memo based on this ASC 606 analysis:
        
        ANALYSIS DATA:
        {analysis_data}
        
        Create a professional memo with these sections:
        1. Executive Summary
        2. Background
        3. Detailed Analysis (5-step framework)
        4. Key Judgments
        5. Financial Impact
        6. Conclusion
        
        Use formal accounting language suitable for:
        - Audit committee presentations
        - External auditor documentation
        - SEC filing support
        
        Include specific contract quotes and ASC citations throughout.
        """
    
    @staticmethod
    def get_step_specific_prompt(step: int, contract_text: str, context: str = "") -> str:
        """Generate step-specific analysis prompts"""
        step_templates = {
            1: "Analyze whether this arrangement meets the contract definition under ASC 606-10-25-1",
            2: "Identify and analyze performance obligations under ASC 606-10-25-14 through 25-22",
            3: "Determine the transaction price including variable consideration per ASC 606-10-32-2",
            4: "Allocate transaction price to performance obligations per ASC 606-10-32-28",
            5: "Determine recognition timing under ASC 606-10-25-23 through 25-37"
        }
        
        return f"""
        Focus specifically on Step {step} of ASC 606: {step_templates[step]}
        
        CONTRACT TEXT:
        {contract_text}
        
        CONTEXT:
        {context}
        
        Provide detailed analysis with:
        - Specific ASC citations
        - Contract quotes supporting conclusion
        - Professional reasoning
        """

class ASC842PromptTemplates:
    """Centralized ASC 842 lease analysis templates"""
    
    @staticmethod
    def get_lease_classification_prompt(lease_terms: Dict) -> str:
        """Lease classification analysis prompt"""
        return f"""
        Analyze this lease arrangement under ASC 842 classification criteria:
        
        LEASE TERMS:
        {lease_terms}
        
        Apply the five classification tests:
        1. Transfer of ownership (ASC 842-10-25-2(a))
        2. Purchase option (ASC 842-10-25-2(b))
        3. Lease term vs. economic life (ASC 842-10-25-2(c))
        4. Present value vs. fair value (ASC 842-10-25-2(d))
        5. Specialized nature (ASC 842-10-25-2(e))
        
        Conclude whether this is an operating or finance lease with supporting analysis.
        """

class PromptEnhancer:
    """Dynamic prompt enhancement utilities"""
    
    @staticmethod
    def add_context_awareness(base_prompt: str, user_data: Dict) -> str:
        """Add user-specific context to prompts"""
        enhancements = []
        
        if user_data.get("company_type"):
            enhancements.append(f"Consider this is a {user_data['company_type']} company.")
        
        if user_data.get("industry"):
            enhancements.append(f"Industry context: {user_data['industry']}")
        
        if user_data.get("complexity_level"):
            level = user_data['complexity_level']
            if level == "high":
                enhancements.append("Provide additional technical detail for complex transaction.")
            elif level == "low":
                enhancements.append("Focus on clear, straightforward analysis.")
        
        if enhancements:
            context = "\n".join(enhancements)
            return f"{base_prompt}\n\nADDITIONAL CONTEXT:\n{context}"
        
        return base_prompt
    
    @staticmethod
    def add_debugging_context(prompt: str, debug_info: Optional[str] = None) -> str:
        """Add debugging context for prompt engineering"""
        if debug_info and st.session_state.get("debug_mode", False):
            return f"{prompt}\n\nDEBUG INFO: {debug_info}"
        return prompt

def format_prompt_with_data(template: str, **kwargs) -> str:
    """
    Safely format prompt templates with data
    Prevents KeyError if template variables are missing
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        st.error(f"Missing template variable: {e}")
        return template

def get_system_message(role: str = "technical_accountant") -> str:
    """Get appropriate system messages for different roles"""
    system_messages = {
        "technical_accountant": """
        You are a senior technical accountant with 15+ years of experience in revenue recognition, 
        lease accounting, and financial instruments. You have worked at Big 4 firms and understand 
        the requirements for audit-quality documentation. Provide precise, well-cited analysis 
        suitable for professional accounting memos.
        """,
        "audit_partner": """
        You are an audit partner reviewing technical accounting positions. Focus on risk assessment, 
        materiality, and audit evidence. Highlight areas requiring additional scrutiny and provide 
        recommendations for audit procedures.
        """,
        "controller": """
        You are a corporate controller implementing accounting standards. Focus on practical 
        implementation, system requirements, and process improvements. Consider operational 
        efficiency and internal control implications.
        """
    }
    
    return system_messages.get(role, system_messages["technical_accountant"])

def create_prompt_debugging_ui():
    """Create UI for prompt template testing and debugging"""
    with st.expander("🔍 Prompt Engineering Tools"):
        st.subheader("Template Testing")
        
        template_type = st.selectbox(
            "Template Type",
            ["ASC 606 Analysis", "Memo Generation", "Step-Specific", "Lease Classification"]
        )
        
        if template_type == "ASC 606 Analysis":
            sample_prompt = ASC606PromptTemplates.get_analysis_prompt("Sample contract text")
            st.code(sample_prompt, language="text")
        
        st.subheader("Dynamic Enhancement")
        user_context = {
            "company_type": st.selectbox("Company Type", ["Public", "Private", "Non-profit"]),
            "industry": st.text_input("Industry", "Technology"),
            "complexity_level": st.selectbox("Complexity", ["Low", "Medium", "High"])
        }
        
        if st.button("Test Enhancement"):
            base_prompt = "Analyze this contract under ASC 606."
            enhanced = PromptEnhancer.add_context_awareness(base_prompt, user_context)
            st.code(enhanced, language="text")