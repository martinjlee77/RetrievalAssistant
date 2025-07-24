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
        
        # Extract contract types and collectibility for context
        contract_types_info = ""
        if user_inputs and user_inputs.get('contract_types'):
            contract_types_info = f"""
        DOCUMENT TYPES PROVIDED: {', '.join(user_inputs['contract_types'])}
        Note: The uploaded documents include {', '.join(user_inputs['contract_types'])}. Consider the relationship between these document types when analyzing the arrangement.
        """
        
        collectibility_info = ""
        if user_inputs and user_inputs.get('collectibility_assessment'):
            collectibility_info = f"""
        MANAGEMENT'S COLLECTIBILITY ASSESSMENT: {user_inputs['collectibility_assessment']}
        Important: Management has assessed that collection of consideration is "{user_inputs['collectibility_assessment']}". This is fundamental to Step 1 contract identification under ASC 606-10-25-1(e).
        """
        
        consideration_payable_info = ""
        if user_inputs and user_inputs.get('has_consideration_payable'):
            amount = user_inputs.get('consideration_payable_amount', 0)
            consideration_payable_info = f"""
        CONSIDERATION PAYABLE TO CUSTOMER: Yes (${amount:,.2f})
        Important: The contract includes consideration payable to the customer. This must be considered in transaction price determination per ASC 606-10-32-25.
        """
        
        return f"""
        You are an expert technical accountant specializing in ASC 606 Revenue Recognition.
        
        Analyze the following contract according to the 5-step ASC 606 framework:
        
        CONTRACT TEXT:
        {contract_text}
        
        {contract_types_info}
        
        {collectibility_info}
        
        {consideration_payable_info}
        
        {f"USER PRELIMINARY ASSESSMENT: {user_inputs}" if user_inputs else ""}
        
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
        - Performance obligation identification and timing
        - Variable consideration estimates and constraints
        - Consideration payable to customer (if applicable) per ASC 606-10-32-25
        
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