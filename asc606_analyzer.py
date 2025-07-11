"""
ASC 606 Contract Analysis Engine
RAG-powered professional contract analysis using authoritative ASC 606 sources
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from openai import OpenAI
from dataclasses import dataclass

# Import RAG system
from rag_system import initialize_rag_system, search_asc606_guidance, asc606_kb

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

@dataclass
class ASC606Analysis:
    """Structure for ASC 606 analysis results"""
    contract_overview: Dict[str, Any]
    step1_contract_identification: Dict[str, Any]
    step2_performance_obligations: Dict[str, Any]
    step3_transaction_price: Dict[str, Any]
    step4_price_allocation: Dict[str, Any]
    step5_revenue_recognition: Dict[str, Any]
    professional_memo: str
    implementation_guidance: List[str]
    citations: List[str]
    not_applicable_items: List[str]

class ASC606Analyzer:
    """Professional ASC 606 contract analyzer using GPT-4o"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.setup_logging()
        self.rag_initialized = False
        self.initialize_rag_system()
    
    def setup_logging(self):
        """Setup logging for analysis tracking"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize_rag_system(self):
        """Initialize RAG system with authoritative ASC 606 sources"""
        try:
            self.logger.info("Initializing RAG system with authoritative ASC 606 sources...")
            
            rag_results = initialize_rag_system()
            
            if rag_results["status"] == "success" and rag_results["ready_for_analysis"]:
                self.rag_initialized = True
                self.logger.info("RAG system successfully initialized")
                self.logger.info(f"Knowledge base contains {rag_results['load_results']['total_chunks']} chunks")
                self.logger.info(f"Sources loaded: {rag_results['load_results']['sources_loaded']}")
            else:
                self.logger.error("RAG system initialization failed")
                self.logger.error(f"Error: {rag_results.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Error initializing RAG system: {str(e)}")
            self.rag_initialized = False
    
    def _load_comprehensive_questions(self) -> str:
        """Load the comprehensive ASC 606 questions framework"""
        return """
        COMPREHENSIVE ASC 606 ANALYSIS FRAMEWORK:
        
        1.0 SCOPE OF ASC 606
        1.0.1 Definition of a customer - Is this a contract with a customer receiving goods/services that are outputs of ordinary activities?
        1.0.2 Contract elements outside scope - Are there lease contracts, insurance, financial instruments, guarantees, nonmonetary exchanges?
        1.0.3 License of intellectual property - Does the contract contain IP licenses?
        
        STEP 1: IDENTIFY THE CONTRACT
        1.1 Definition of a contract - Do parties have approved obligations, identifiable rights, payment terms, commercial substance, probable collection?
        1.1.1 Contract enforceability - Does contract have stated duration without cancellation rights?
        1.2 Combining contracts - Were contracts entered at same time with same customer?
        1.2.1 Contract combination criteria - Single commercial objective, interdependent pricing, single performance obligation?
        1.3 Contract modifications - Has contract been modified since inception?
        1.3.1 Separate revenue arrangements - Does modification add distinct goods/services at standalone selling price?
        1.3.2 Treatment of modified contract - Are remaining goods/services distinct or part of partially satisfied obligation?
        1.3.2.1 Decrease in scope - Has contract scope decreased (partial termination)?
        
        STEP 2: IDENTIFY PERFORMANCE OBLIGATIONS
        2.0 Performance obligations - What are the performance obligations?
        2.1 Identify promised goods/services - What goods/services are promised?
        2.1.1 Determine if distinct - Are goods/services capable of being distinct and distinct in context?
        2.1.2 Non-distinct goods/services - If not distinct, combine until distinct bundle exists
        2.1.3 Shipping and handling - Were shipping/handling performed after control transfer?
        2.2 Principal versus agent - Is another party involved in providing goods/services?
        2.2.1 Identify specified goods/services - What are the specified goods/services for customer?
        2.2.2 Control determination - Does entity control goods/services before transfer?
        2.2.3 Principal indicators - Primary responsibility, inventory risk, pricing discretion?
        2.2.4 Principal vs agent conclusion - Is entity principal or agent?
        2.3 Service-type warranties - Are warranties sold separately or provide additional service?
        2.4 Customer options - Does contract contain material rights for additional goods/services?
        
        STEP 3: DETERMINE TRANSACTION PRICE
        3.0 Base transaction price - Is there non-variable consideration?
        3.1 Variable consideration - Is any consideration variable or uncertain?
        3.1.1 Estimating variable consideration - Expected value or most likely amount method?
        3.1.2 Constraint on revenue - Amount constrained, likelihood of reversal, magnitude assessment?
        3.1.3 Reassessment - Have uncertainties been resolved or new information gained?
        3.1.4 Rights of return - Does entity give return rights?
        3.2 Refund liabilities - Does entity have refund liability?
        3.3 Significant financing component - Does payment timing provide significant financing benefit?
        3.3.1 Financing component conclusion - Entity's conclusions on financing components?
        3.4 Noncash consideration - Is entity entitled to noncash consideration?
        3.5 Consideration payable to customer - Is consideration payable not for distinct goods/services?
        3.5.1 Form of consideration - Is payment to customer in equity form?
        3.5.2 Timing of recognition - When should consideration paid/payable be recognized?
        3.6 Nonrefundable up-front fees - Is entity entitled to up-front payments?
        3.7 Changes in transaction price - Has transaction price changed since inception?
        
        STEP 4: ALLOCATE TRANSACTION PRICE
        4.0 Allocation of transaction price - Are there multiple performance obligations?
        4.1 Attributable variable consideration - Is variable consideration attributable to specific obligations?
        4.2 Allocating a discount - Does contract contain a discount?
        4.3 Standalone selling price - How was standalone selling price determined?
        4.3.1 Updating standalone selling price - Has contract been modified requiring price updates?
        4.4 Options as separate obligations - If material right exists, was practical alternative applied?
        4.5 Relative standalone selling price method - Was transaction price allocated using relative method?
        4.6 Elements outside scope - Does arrangement contain out-of-scope elements?
        
        STEP 5: SATISFACTION OF PERFORMANCE OBLIGATIONS
        5.0 Transfer of control - Do obligations meet over-time criteria (simultaneous consumption, customer-controlled enhancement, no alternative use with enforceable payment)?
        5.1 Point in time control - If not over-time, when does control transfer?
        5.2 Repurchase provisions - Does contract contain repurchase provisions?
        5.3 Residual value guarantees - Does contract contain residual value guarantees?
        5.4 Bill-and-hold arrangements - Could contract be bill-and-hold arrangement?
        5.5 Consignment arrangements - Could contract be consignment arrangement?
        5.5.1 Consignment control criteria - When does control transfer to dealer/end customer?
        5.6 Customer acceptance - If acceptance provisions exist, has control objectively transferred?
        5.7 Revenue recognition pattern - What is the measure of progress for over-time obligations and point-in-time timing?
        5.8 Breakage and prepayments - Does entity receive consideration for unexercised customer rights?
        """
    
    def analyze_contract(self, contract_text: str, contract_data: Dict[str, Any]) -> ASC606Analysis:
        """
        Perform comprehensive ASC 606 analysis on contract using RAG system
        
        Args:
            contract_text: Extracted text from contract document
            contract_data: Structured contract information from user input
            
        Returns:
            ASC606Analysis: Complete analysis results
        """
        self.logger.info(f"Starting RAG-powered ASC 606 analysis for contract: {contract_data.get('analysis_title', 'Unknown')}")
        
        if not self.rag_initialized:
            raise Exception("RAG system not initialized. Cannot perform analysis without authoritative sources.")
        
        try:
            # Generate contextual analysis using RAG
            analysis_prompt = self._create_rag_analysis_prompt(contract_text, contract_data)
            
            # Call GPT-4o for analysis with RAG context
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_rag_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000
            )
            
            # Parse the response
            analysis_result = json.loads(response.choices[0].message.content)
            
            # Generate professional memo
            memo = self._generate_professional_memo(analysis_result, contract_data)
            
            # Structure the complete analysis
            return self._structure_analysis_result(analysis_result, memo)
            
        except Exception as e:
            self.logger.error(f"Error in ASC 606 analysis: {str(e)}")
            raise Exception(f"Analysis failed: {str(e)}")
    
    def _get_rag_system_prompt(self) -> str:
        """Get the RAG-enhanced system prompt for ASC 606 analysis"""
        return """
        You are a senior manager at a Big 4 accounting firm specializing in ASC 606 revenue recognition. 
        You have deep expertise in applying ASC 606 to complex contractual arrangements and preparing 
        professional accounting memos for clients.
        
        CRITICAL: You must base your analysis EXCLUSIVELY on the authoritative ASC 606 guidance and 
        EY interpretative materials provided in the context. Do not rely on general knowledge - 
        only use the specific guidance provided from the knowledge base.
        
        Your task is to analyze contracts following the ASC 606 five-step methodology using the 
        authoritative sources provided and provide comprehensive professional analysis suitable 
        for Big 4 audit and advisory work.
        
        RESPONSE FORMAT: Return your analysis as a JSON object with the following structure:
        {
            "contract_overview": {
                "nature_of_arrangement": "string",
                "key_terms": ["list of key terms"],
                "complexity_assessment": "string",
                "industry_considerations": "string"
            },
            "step1_contract_identification": {
                "contract_exists": "boolean",
                "rationale": "string",
                "combination_required": "boolean",
                "modifications_present": "boolean",
                "key_findings": ["list"]
            },
            "step2_performance_obligations": {
                "identified_obligations": ["list of obligations"],
                "distinctness_analysis": "string",
                "principal_agent_analysis": "string",
                "key_judgments": ["list"]
            },
            "step3_transaction_price": {
                "fixed_consideration": "number",
                "variable_consideration": "string",
                "constraint_analysis": "string",
                "financing_components": "string",
                "key_estimates": ["list"]
            },
            "step4_price_allocation": {
                "allocation_method": "string",
                "standalone_selling_prices": "object",
                "allocation_results": "object",
                "key_assumptions": ["list"]
            },
            "step5_revenue_recognition": {
                "recognition_pattern": "string",
                "control_transfer_analysis": "string",
                "timing_determination": "string",
                "implementation_steps": ["list"]
            },
            "professional_conclusions": {
                "executive_summary": "string",
                "key_accounting_policies": ["list"],
                "implementation_timeline": "string",
                "ongoing_considerations": ["list"]
            },
            "citations": ["list of ASC 606 paragraph references"],
            "not_applicable_items": ["list of ASC 606 concepts not applicable to this contract"]
        }
        
        QUALITY STANDARDS:
        - Cite specific ASC 606 paragraphs for each conclusion
        - Use professional accounting language
        - Provide clear implementation guidance
        - Address alternative interpretations where relevant
        - Maintain audit-ready documentation standards
        """
    
    def _create_rag_analysis_prompt(self, contract_text: str, contract_data: Dict[str, Any]) -> str:
        """Create RAG-enhanced analysis prompt with authoritative context"""
        
        # Generate relevant context from knowledge base for each step
        step1_context = search_asc606_guidance(
            f"contract identification criteria enforceable rights obligations {contract_data.get('customer_name', '')}"
        )
        
        step2_context = search_asc606_guidance(
            f"performance obligations distinct goods services {contract_data.get('arrangement_description', '')}"
        )
        
        step3_context = search_asc606_guidance(
            f"transaction price variable consideration {contract_data.get('transaction_price', '')}"
        )
        
        step4_context = search_asc606_guidance(
            f"allocate transaction price performance obligations standalone selling price"
        )
        
        step5_context = search_asc606_guidance(
            f"revenue recognition control transfer over time point in time"
        )
        
        # Build comprehensive prompt with RAG context
        prompt = f"""
        AUTHORITATIVE ASC 606 GUIDANCE CONTEXT:

        **STEP 1 - CONTRACT IDENTIFICATION:**
        {step1_context}

        **STEP 2 - PERFORMANCE OBLIGATIONS:**
        {step2_context}

        **STEP 3 - TRANSACTION PRICE:**
        {step3_context}

        **STEP 4 - PRICE ALLOCATION:**
        {step4_context}

        **STEP 5 - REVENUE RECOGNITION:**
        {step5_context}

        CONTRACT ANALYSIS REQUEST:
        
        Contract Information:
        - Analysis Title: {contract_data.get('analysis_title', 'N/A')}
        - Customer: {contract_data.get('customer_name', 'N/A')}
        - Arrangement: {contract_data.get('arrangement_description', 'N/A')}
        - Contract Period: {contract_data.get('contract_start', 'N/A')} to {contract_data.get('contract_end', 'N/A')}
        - Transaction Price: {contract_data.get('currency', 'USD')} {contract_data.get('transaction_price', 'N/A')}
        - Analysis Depth: {contract_data.get('analysis_depth', 'Standard')}

        CONTRACT TEXT:
        {contract_text[:3000]}  # Limit contract text to avoid token limits

        INSTRUCTIONS:
        Using ONLY the authoritative ASC 606 guidance provided above, perform a comprehensive 
        analysis following the five-step methodology. Base all conclusions on the specific 
        guidance provided - do not use general knowledge or assumptions.

        For each step, cite specific ASC 606 paragraphs and EY guidance where applicable.
        """
        
        return prompt

    def _create_master_analysis_prompt(self, contract_text: str, contract_data: Dict[str, Any]) -> str:
        """Create the master analysis prompt"""
        return f"""
        COMPREHENSIVE ASC 606 CONTRACT ANALYSIS REQUEST
        
        CONTRACT CONTEXT:
        - Analysis Title: {contract_data.get('analysis_title', 'N/A')}
        - Customer: {contract_data.get('customer_name', 'N/A')}
        - Contract Period: {contract_data.get('contract_start', 'N/A')} to {contract_data.get('contract_end', 'N/A')}
        - Transaction Price: {contract_data.get('currency', 'USD')} {contract_data.get('transaction_price', 0):,.2f}
        - Arrangement Description: {contract_data.get('arrangement_description', 'N/A')}
        - Analysis Depth: {contract_data.get('analysis_depth', 'Standard Analysis')}
        
        CONTRACT TEXT:
        {contract_text}
        
        ANALYSIS REQUIREMENTS:
        Please perform a comprehensive ASC 606 analysis following the framework provided in the system prompt.
        
        For each step of the ASC 606 analysis, address the relevant questions from this comprehensive framework:
        {self.asc606_guidance['comprehensive_questions']}
        
        SPECIFIC INSTRUCTIONS:
        1. Apply the five-step ASC 606 methodology systematically
        2. Address each applicable question from the comprehensive framework
        3. Provide specific ASC 606 paragraph citations
        4. Include professional judgment documentation
        5. Identify concepts/questions that are not applicable to this contract
        6. Provide implementation guidance and timeline
        
        Focus on professional quality suitable for Big 4 audit and advisory work.
        """
    
    def _generate_professional_memo(self, analysis_result: Dict[str, Any], contract_data: Dict[str, Any]) -> str:
        """Generate professional accounting memo"""
        memo_prompt = f"""
        Based on the ASC 606 analysis provided, generate a professional accounting memo with the following structure:
        
        MEMORANDUM
        
        TO: {contract_data.get('customer_name', 'Client')} Management
        FROM: [Accounting Advisory Team]
        DATE: {datetime.now().strftime('%B %d, %Y')}
        RE: ASC 606 Revenue Recognition Analysis - {contract_data.get('analysis_title', 'Contract Analysis')}
        
        EXECUTIVE SUMMARY
        [2-3 paragraph executive summary of key findings and recommendations]
        
        BACKGROUND
        [Brief description of the arrangement and analysis purpose]
        
        ASC 606 ANALYSIS
        
        Step 1: Contract Identification
        [Analysis and conclusions]
        
        Step 2: Performance Obligations
        [Analysis and conclusions]
        
        Step 3: Transaction Price
        [Analysis and conclusions]
        
        Step 4: Price Allocation
        [Analysis and conclusions]
        
        Step 5: Revenue Recognition
        [Analysis and conclusions]
        
        IMPLEMENTATION GUIDANCE
        [Specific steps and timeline for implementation]
        
        ONGOING CONSIDERATIONS
        [Key items to monitor and reassess]
        
        CONCLUSION
        [Final recommendations and next steps]
        
        Analysis data: {json.dumps(analysis_result, indent=2)}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior accounting professional writing a formal accounting memo. Use professional language, proper formatting, and ensure all conclusions are well-supported."
                    },
                    {
                        "role": "user",
                        "content": memo_prompt
                    }
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating professional memo: {str(e)}")
            return f"Error generating memo: {str(e)}"
    
    def _structure_analysis_result(self, analysis_result: Dict[str, Any], memo: str) -> ASC606Analysis:
        """Structure the analysis result into the final format"""
        return ASC606Analysis(
            contract_overview=analysis_result.get('contract_overview', {}),
            step1_contract_identification=analysis_result.get('step1_contract_identification', {}),
            step2_performance_obligations=analysis_result.get('step2_performance_obligations', {}),
            step3_transaction_price=analysis_result.get('step3_transaction_price', {}),
            step4_price_allocation=analysis_result.get('step4_price_allocation', {}),
            step5_revenue_recognition=analysis_result.get('step5_revenue_recognition', {}),
            professional_memo=memo,
            implementation_guidance=analysis_result.get('professional_conclusions', {}).get('implementation_steps', []),
            citations=analysis_result.get('citations', []),
            not_applicable_items=analysis_result.get('not_applicable_items', [])
        )
    
    def export_analysis_to_docx(self, analysis: ASC606Analysis, filename: str) -> str:
        """Export analysis to Word document format"""
        # This would implement Word document generation
        # For now, returning the memo text
        return analysis.professional_memo
    
    def validate_analysis_quality(self, analysis: ASC606Analysis) -> Dict[str, Any]:
        """Validate the quality of the analysis"""
        validation_prompt = f"""
        Review this ASC 606 analysis for:
        1. Technical accuracy of ASC 606 applications
        2. Completeness of required analysis
        3. Professional quality of conclusions
        4. Proper citation of authoritative guidance
        5. Clear implementation guidance
        
        Analysis to review:
        {json.dumps(analysis.__dict__, indent=2, default=str)}
        
        Provide a quality score (1-100) and specific feedback for improvement.
        Return as JSON with: {{"quality_score": number, "feedback": ["list of feedback items"], "recommendations": ["list of recommendations"]}}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior accounting partner reviewing ASC 606 analysis for quality and accuracy."
                    },
                    {
                        "role": "user",
                        "content": validation_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Error in quality validation: {str(e)}")
            return {"quality_score": 0, "feedback": [f"Validation error: {str(e)}"], "recommendations": []}