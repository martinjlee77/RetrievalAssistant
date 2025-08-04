"""
Centralized Prompt Management for Multi-Standard Platform
Provides reusable prompt templates with dynamic context injection
"""
from typing import Dict, List, Any, Optional
import streamlit as st

class ASC606PromptTemplates:
    """Legacy prompt templates - kept for backwards compatibility"""
    
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
    def _get_memo_format(user_inputs: Optional[Dict] = None) -> str:
        """Get audience-specific memo formatting instructions"""
        if not user_inputs:
            return ASC606PromptTemplates._technical_memo_format()
        
        memo_audience = user_inputs.get('memo_audience', 'Technical Accounting Team / Audit File')
        
        if memo_audience == 'Management Review':
            return ASC606PromptTemplates._management_memo_format()
        elif memo_audience == 'Deal Desk / Sales Team':
            return ASC606PromptTemplates._deal_desk_memo_format()
        else:  # Technical Accounting Team / Audit File (default)
            return ASC606PromptTemplates._technical_memo_format()
    
    @staticmethod
    def _technical_memo_format() -> str:
        """Technical accounting memo format for audit workpapers"""
        return """
        Format your response as a technical accounting memo with these sections:
        1. Executive Summary (key conclusions and financial impact)
        2. Background (contract parties, dates, nature of arrangement)
        3. Detailed Analysis (comprehensive 5-step ASC 606 framework)
        4. Key Judgments (critical accounting positions with rationale)
        5. Financial Impact (revenue amounts, timing, P&L effects)
        6. Conclusion (final conclusion)
        
        Use technical accounting language suitable for:
        - Audit committee presentations
        - External auditor documentation
        - SEC filing support
        - Detailed step-by-step reasoning with precise ASC 606 citations
        """
    
    @staticmethod
    def _management_memo_format() -> str:
        """Management-focused memo format"""
        return """
        Format your response as a management memo with these sections:
        1. Executive Summary (key business implications and financial impact)
        2. Background (brief contract overview)
        3. Key Findings (most important revenue recognition impacts)
        4. Business Impact (revenue timing, P&L effects, cash flow)
        5. Recommendations (actionable next steps)
        6. Technical Summary (abbreviated 5-step analysis)
        
        Use business-focused language that:
        - Emphasizes "so what" for decision-makers
        - Minimizes technical jargon
        - Focuses on financial and business implications
        - Provides clear recommendations
        """
    
    @staticmethod
    def _deal_desk_memo_format() -> str:
        """Deal desk/sales team memo format"""
        return """
        Format your response as a deal structuring memo with these sections:
        1. Revenue Recognition Summary (when revenue will be recognized)
        2. Contract Terms Impact (how specific clauses affect revenue timing)
        3. Deal Structure Analysis (optimal ways to structure similar deals)
        4. Revenue Acceleration Opportunities (terms that could speed recognition)
        5. Risk Factors (terms that could delay revenue recognition)
        6. Recommendations for Future Deals
        
        Use practical language that:
        - Translates accounting rules into deal structuring guidance
        - Explains how contract terms affect revenue timing
        - Provides actionable insights for sales negotiations
        - Identifies optimal deal structures for revenue recognition
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