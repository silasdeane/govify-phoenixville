import os
from pinecone import Pinecone

# Use the direct API key instead of relying on environment variables
pinecone_api_key = "pcsk_1MfLA_QRmNnRSR4pumc7thAYp6eqHkxGF3Jhmbs9X66SN2i1Rr4akBzmERV5NCjyBhE8e"
index_name = "phoenixville-municipal-code"  # Changed to target this index

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

# Check if index exists
try:
    indexes = pc.list_indexes()
    if index_name in indexes.names():
        # Get the index
        index = pc.Index(index_name)
        
        # Get stats to see namespaces
        stats = index.describe_index_stats()
        print(f"Current vector count: {stats.total_vector_count}")
        print(f"Namespaces: {stats.namespaces}")
        
        # Check if there are namespaces
        if stats.namespaces:
            # Delete vectors from each namespace
            for namespace in stats.namespaces.keys():
                print(f"Deleting vectors from namespace '{namespace}'...")
                index.delete(delete_all=True, namespace=namespace)
                print(f"All vectors deleted from namespace '{namespace}' in index '{index_name}'")
        else:
            # No namespaces, delete all vectors from default namespace
            index.delete(delete_all=True)
            print(f"All vectors deleted from default namespace in index '{index_name}'")
            
        # Verify deletion
        stats_after = index.describe_index_stats()
        print(f"Vector count after deletion: {stats_after.total_vector_count}")
        print(f"Namespaces after deletion: {stats_after.namespaces}")
    else:
        print(f"Index '{index_name}' doesn't exist")
except Exception as e:
    print(f"Error: {e}")