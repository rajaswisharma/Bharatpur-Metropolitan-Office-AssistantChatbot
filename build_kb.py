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
    #overlap = 50 — Each chunk shares 50 characters with the next one (prevents cutting words/sentences in half)
    start = 0
    
    while start < len(raw_text):
        end = min(start + chunk_size, len(raw_text))
        chunk = raw_text[start:end]
        #chunk = raw_text[start:end] — Grab a 500-character slice
        chunks.append(chunk)
        start += chunk_size - overlap
    
    print(f"Split into {len(chunks)} chunks")

# Chunk 1: [characters 1-500]
# Chunk 2:        [characters 451-950]
# Chunk 3:               [characters 901-1400]

    # Convert each chunk into embeddings (numerical representations)
    # The model understands meaning in both Nepali and English
    print("Creating embeddings...")
    embeddings = model.encode(chunks).tolist() #.tolist() — Converts to a format ChromaDB understands

    # Store in ChromaDB (a local vector database)
    client = chromadb.PersistentClient(path="./chroma_db")
    #chromadb.PersistentClient(path="./chroma_db") — Creates/opens a database folder on your computer
    collection = client.get_or_create_collection(name=collection_name)
    
    # Add all chunks with their embeddings to the database
    collection.add(
        embeddings=embeddings,
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )
    
    print(f"Stored {len(chunks)} chunks in the knowledge base!")

if __name__ == "__main__":
    build_knowledge_base()