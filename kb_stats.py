"""
Knowledge Base Statistics Collector
Gathers comprehensive stats from all ASC knowledge bases
"""

import os
from datetime import datetime
from shared.knowledge_base import (
    ASC606KnowledgeBase,
    ASC340KnowledgeBase, 
    ASC842KnowledgeBase,
    ASC718KnowledgeBase,
    ASC805KnowledgeBase
)

def get_all_kb_stats():
    """Get comprehensive stats from all knowledge bases"""

    knowledge_bases = {
        "ASC 606": ASC606KnowledgeBase,
        "ASC 340-40": ASC340KnowledgeBase,
        "ASC 842": ASC842KnowledgeBase,
        "ASC 718": ASC718KnowledgeBase,
        "ASC 805": ASC805KnowledgeBase
    }

    all_stats = {}
    total_documents = 0

    for standard_name, kb_class in knowledge_bases.items():
        try:
            # Initialize knowledge base
            kb = kb_class()

            # Get basic stats
            stats = kb.get_stats()

            # Add directory size info
            db_path = stats.get('database_path', '')
            if db_path and os.path.exists(db_path):
                # Calculate directory size
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(db_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)

                stats['database_size_mb'] = round(total_size / (1024 * 1024), 2)
                stats['last_modified'] = datetime.fromtimestamp(
                    os.path.getmtime(db_path)
                ).strftime("%Y-%m-%d")

            all_stats[standard_name] = stats

            if 'document_count' in stats:
                total_documents += stats['document_count']

        except Exception as e:
            all_stats[standard_name] = {"error": str(e)}

    # Add summary stats
    all_stats['_summary'] = {
        "total_standards": len(knowledge_bases),
        "total_documents": total_documents,
        "last_refresh_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_knowledge_bases": len([k for k, v in all_stats.items() 
                                     if k != '_summary' and 'error' not in v])
    }

    return all_stats

# Usage
if __name__ == "__main__":
    stats = get_all_kb_stats()

    # Pretty print results
    for standard, data in stats.items():
        print(f"\n{standard}:")
        for key, value in data.items():
            print(f"  {key}: {value}")