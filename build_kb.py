import chromadb
from sentence_transformers import SentenceTransformer

# chromadb — A lightweight vector database that stores text and lets us search it by meaning (not just keywords)
# SentenceTransformer — An AI model that converts sentences into numbers (embeddings) so we can find similar content

def build_knowledge_base(text_file="website_content.txt", collection_name="bharatpur_docs"):
    # Load the multilingual embedding model
    # This model supports Nepali, English, and 50+ other languages
    # Downloads automatically on first run (~470MB)
    print("Loading multilingual model...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

#SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2') — Loads the AI model that understands both Nepali and English

        # Read the scraped content
    with open(text_file, 'r', encoding='utf-8') as f:
    #encoding='utf-8' — Crucial for Nepali characters (देवनागरी)
        raw_text = f.read()
    
    print(f"Loaded {len(raw_text)} characters from {text_file}")

    # Split the text into smaller chunks
    # Why? AI models have a limit on how much text they can process at once
    # Chunks of 500 characters with 50 character overlap work well for search
    chunks = []
    chunk_size = 500
    overlap = 50
    start = 0
    
    while start < len(raw_text):
        end = min(start + chunk_size, len(raw_text))
        chunk = raw_text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    print(f"Split into {len(chunks)} chunks")