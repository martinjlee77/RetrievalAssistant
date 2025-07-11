"""
Simple RAG Test - Initialize once and test search
"""

from rag_system import initialize_rag_system, search_asc606_guidance
import json

def test_simple_rag():
    """Test basic RAG functionality"""
    print("Testing simple RAG system...")
    
    # Initialize (this may take a while)
    print("Initializing RAG system...")
    results = initialize_rag_system()
    
    if results['status'] == 'success':
        print("✅ RAG system initialized successfully")
        print(f"Sources loaded: {results['load_results']['sources_loaded']}")
        print(f"Total chunks: {results['load_results']['total_chunks']}")
        
        # Test search
        print("\nTesting search functionality...")
        context = search_asc606_guidance("contract identification criteria", max_context_tokens=500)
        print(f"Context retrieved: {len(context)} characters")
        print(f"Sample context: {context[:300]}...")
        
        return True
    else:
        print(f"❌ RAG initialization failed: {results.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    test_simple_rag()