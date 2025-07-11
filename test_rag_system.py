"""
Test RAG System Integration
"""

from rag_system import initialize_rag_system, search_asc606_guidance
from asc606_analyzer import ASC606Analyzer
import json

def test_rag_initialization():
    """Test RAG system initialization"""
    print("Testing RAG system initialization...")
    
    # Initialize RAG system
    results = initialize_rag_system()
    
    print(f"Status: {results['status']}")
    print(f"Ready for analysis: {results['ready_for_analysis']}")
    
    if results['status'] == 'success':
        print(f"Sources loaded: {results['load_results']['sources_loaded']}")
        print(f"Total chunks: {results['load_results']['total_chunks']}")
        print(f"Chunk distribution: {results['load_results']['chunk_distribution']}")
    else:
        print(f"Error: {results.get('error', 'Unknown error')}")
    
    return results['ready_for_analysis']

def test_search_functionality():
    """Test search functionality"""
    print("\nTesting search functionality...")
    
    # Test searches for each step
    test_queries = [
        "contract identification criteria",
        "performance obligations distinct goods services",
        "transaction price variable consideration",
        "allocate transaction price standalone selling price",
        "revenue recognition control transfer"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: {query}")
        results = search_asc606_guidance(query, max_context_tokens=500)
        print(f"Context length: {len(results)} characters")
        print(f"Sample context: {results[:200]}...")

def test_analyzer_initialization():
    """Test ASC606Analyzer initialization"""
    print("\nTesting ASC606Analyzer initialization...")
    
    try:
        analyzer = ASC606Analyzer()
        print(f"RAG initialized: {analyzer.rag_initialized}")
        return analyzer.rag_initialized
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== RAG System Test ===")
    
    # Test initialization
    rag_ready = test_rag_initialization()
    
    if rag_ready:
        # Test search
        test_search_functionality()
        
        # Test analyzer
        analyzer_ready = test_analyzer_initialization()
        
        if analyzer_ready:
            print("\n✅ All tests passed! RAG system is ready for analysis.")
        else:
            print("\n❌ Analyzer initialization failed.")
    else:
        print("\n❌ RAG system initialization failed.")