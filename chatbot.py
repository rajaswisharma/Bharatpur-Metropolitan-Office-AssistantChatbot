import chromadb
from sentence_transformers import SentenceTransformer
import os
import re
from dotenv import load_dotenv

# ============================================================
# SETUP: Load API keys and models ONCE (not on every question)
# ============================================================

# Load variables from .env file (like API keys)
load_dotenv()
# load_dotenv() — Reads the .env file where you store secret keys

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# os.getenv("OPENAI_API_KEY") — Gets the API key. Returns None if not set

# Check if Ollama is available (free local AI)
try:
    import ollama
    # Test connection to Ollama server
    ollama.list()
    # ollama.list() — Checks if Ollama server is running on localhost:11434
    ollama_available = True
    print("✅ Ollama ready — AI-enhanced answers available (free & local).")
except:
    ollama_available = False
    print("⚠️  Ollama not available — running in offline mode.")
    print("   Install Ollama: https://ollama.com")

# Load the multilingual embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# embedding_model — Loads the same multilingual model that created the knowledge base
# Supports Nepali, English, and 50+ other languages

# Connect to the vector database we built earlier
print("Connecting to knowledge base...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# chromadb.PersistentClient(...) — Opens the database folder on your disk

collection = chroma_client.get_collection("bharatpur_docs")
# collection — Connects to the "bharatpur_docs" collection we created with build_kb.py

print("Ready! You can now ask questions.\n")


# ============================================================
# SOURCE EXTRACTION: Get URLs from chunk labels
# ============================================================

def extract_source_from_chunk(chunk):
    """
    Extract the source URL from a chunk.
    Our chunks are labeled like: '--- Page: https://bharatpurmun.gov.np/en ---'
    
    Parameters:
        chunk (str): A text chunk that may contain a source URL label
    
    Returns:
        str or None: The URL if found, None otherwise
    """
    # Look for the URL pattern in the chunk
    # Pattern matches: '--- Page: URL ---' anywhere in the text
    match = re.search(r'--- Page: (https?://[^\s]+) ---', chunk)
    # r'--- Page: (https?://[^\s]+) ---' — Matches '--- Page: ' followed by a URL
    
    if match:
        return match.group(1)
        # match.group(1) — Returns just the URL part (the part in parentheses)
    
    return None
    # Returns None if no URL pattern found in the chunk


# ============================================================
# ENHANCED SEARCH: Returns chunks WITH source URLs
# ============================================================

def get_relevant_chunks_with_sources(query, top_k=5):
    """
    Search the knowledge base and return chunks WITH their source URLs.
    Uses more chunks (5 instead of 3) to give the AI better context.
    
    Parameters:
        query (str): The user's question
        top_k (int): How many chunks to return (default 5 for better coverage)
    
    Returns:
        list: List of dictionaries, each with:
              - 'text': The chunk content
              - 'source': The source URL (or None)
    """
    # Convert question to embedding (numerical representation)
    query_embedding = embedding_model.encode([query]).tolist()
    # embedding_model.encode([query]) — Turns Nepali/English question into numbers
    
    # Search for top_k most similar chunks
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    # n_results=top_k — Get more chunks (5) for richer context
    
    chunks = results['documents'][0]
    # Get the text of all matching chunks
    
    # Build list with both text and source URL for each chunk
    chunks_with_sources = []
    for chunk in chunks:
        source_url = extract_source_from_chunk(chunk)
        # extract_source_from_chunk(chunk) — Find the URL label in this chunk
        
        chunks_with_sources.append({
            "text": chunk,
            "source": source_url
        })
        # Each item is a dict with 'text' and 'source' keys
    
    return chunks_with_sources
    # Returns list like: [{"text": "...", "source": "https://..."}, ...]


# ============================================================
# ORIGINAL SEARCH: Simple search without sources (kept for compatibility)
# ============================================================

def get_relevant_chunks(query, top_k=3):
    """
    Search the knowledge base for chunks most relevant to the user's question.
    Works with both Nepali and English queries.
    
    Parameters:
        query (str): The user's question
        top_k (int): How many chunks to return (default 3)
    
    Returns:
        list: The top_k most relevant text chunks
    """
    # Convert the user's question into an embedding
    query_embedding = embedding_model.encode([query]).tolist()
    # embedding_model.encode([query]) — Turns Nepali/English question into numbers
    
    # Search ChromaDB for the most similar chunks
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    # collection.query(...) — "Which chunks are most similar to this question?"
    
    # Return just the text of the matching chunks
    return results['documents'][0]
    # results['documents'][0] — Extracts just the text from the search results


# ============================================================
# ANSWER FUNCTION: Generate a formatted answer with sources
# ============================================================

def ask_question(question, use_ai=False):
    """
    Answer a question using the knowledge base.
    Returns BOTH the answer and its source URLs.
    
    Parameters:
        question (str): The user's question (Nepali or English)
        use_ai (bool): If True, use Ollama for a natural, formatted answer.
                       If False, return raw search results.
    
    Returns:
        dict: {
            "answer": "The formatted answer text",
            "sources": [
                {"title": "Page Title or URL", "url": "https://..."},
                ...
            ]
        }
    """
    # Step 1: ALWAYS search the knowledge base first
    chunks_with_sources = get_relevant_chunks_with_sources(question, top_k=5)
    # get_relevant_chunks_with_sources() — Returns chunks + their source URLs
    
    # Build context from all chunks
    context = "\n\n---\n\n".join([c["text"] for c in chunks_with_sources])
    # Joins chunks with a separator so the AI can distinguish different sources
    
    # Collect unique source URLs (remove duplicates and None values)
    sources = []
    seen_urls = set()
    # seen_urls — Tracks URLs we've already added to avoid duplicates
    
    for chunk in chunks_with_sources:
        url = chunk["source"]
        if url and url not in seen_urls:
            sources.append({
                "title": url.split("/")[-1] or url,
                # url.split("/")[-1] — Last part of URL as a short title
                "url": url,
                "document": "Bharatpur Municipality Website"
            })
            seen_urls.add(url)
    # sources now contains unique URLs with titles and document info
    
    # Step 2: If AI is requested AND Ollama is available, generate a formatted answer
    if use_ai and ollama_available:
        # System prompt tells the AI exactly how to behave
                # System prompt tells the AI exactly how to behave
        system_prompt = (
            "You are a helpful assistant for Bharatpur Metropolitan City, Nepal. "
            "Your role is to provide ACCURATE municipal information ONLY from the provided context.\n\n"
            
            "CRITICAL RULES:\n"
            "1. Answer ONLY using the provided context. Never use outside knowledge.\n"
            "2. If information is not in the context, say exactly: "
            "'यो जानकारी हाल उपलब्ध छैन। (This information is currently not available.)'\n"
            "3. LANGUAGE RULE (MOST IMPORTANT):\n"
            "   - If the question is in English → You MUST answer in English ONLY.\n"
            "   - If the question is in Nepali → You MUST answer in Nepali ONLY.\n"
            "   - Translate ALL content to match the question's language.\n"
            "   - Never mix languages in a single answer.\n"
            "4. Never invent names, dates, fees, phone numbers, or procedures.\n"
            "5. Preserve exact factual details: dates, amounts, requirements, office names, phone numbers.\n"
            "6. Do NOT repeat the same information multiple times.\n"
            "7. Be concise but complete. Remove irrelevant navigation text and menu items.\n"
            "8. Sort services in a logical order (emergency services first, then alphabetical).\n\n"
            
            "FORMATTING RULES:\n"
            "- Start with a brief 1-2 sentence introduction ending with a colon or period.\n"
            "- Write each service name as PLAIN TEXT on its own line (do NOT use **, ##, or any markdown symbols for headings).\n"
            "- Use bullet points (•) for each detail under a service.\n"
            "- Each bullet should be on its own line.\n"
            "- Use a blank line between different services for readability.\n"
            "- Only use **bold** (with asterisks) for: phone numbers, fees, exact amounts, and deadlines.\n"
            "- NEVER wrap service titles/categories/headings in ** asterisks.\n"
            "- Keep the formatting clean, simple, and consistent.\n"
            "- End with a brief note if information seems incomplete.\n\n"
            
            "CORRECT ENGLISH FORMAT (follow this exactly):\n\n"
            "Bharatpur Metropolitan City provides various citizen services through its offices. "
            "Here are the key services available:\n\n"
            "Fire Brigade Service\n"
            "• Service time: Immediate\n"
            "• Fee: Free\n"
            "• Contact: **056-521083, 9845143878**\n"
            "• Office: Fire Brigade Department\n\n"
            "Stray Animal Control\n"
            "• Service time: Immediate\n"
            "• Fee: Free\n"
            "• Office: Municipal Police Branch\n\n"
            "Education Department Service\n"
            "• Service type: Registration of private institutions\n"
            "• Processing time: 7 days after document submission\n"
            "• Fee: Basic level **Rs. 300**, Secondary level **Rs. 500**\n"
            "• Office: Education Administration Division\n\n"
            "Information Services\n"
            "• Service type: Information under Right to Information Act\n"
            "• Processing time: 1 to 15 days based on nature of request\n"
            "• Fee: Free for up to 10 pages, **Rs. 5 per page** above 10 pages\n"
            "• Office: Information and Technology Branch\n\n"
            
            "CORRECT NEPALI FORMAT (follow this exactly):\n\n"
            "भरतपुर महानगरपालिकाले विभिन्न नागरिक सेवाहरू प्रदान गर्दछ। "
            "यहाँ उपलब्ध मुख्य सेवाहरू:\n\n"
            "दमकल सेवा\n"
            "• सेवा समय: तत्काल\n"
            "• शुल्क: नि:शुल्क\n"
            "• सम्पर्क: **०५६-५२१०८३, ९८४५१४३८७८**\n"
            "• कार्यालय: वारुण यन्त्र प्रमुख\n\n"
            "छाडा चौपाया नियन्त्रण\n"
            "• सेवा समय: तत्काल\n"
            "• शुल्क: नि:शुल्क\n"
            "• कार्यालय: नगर प्रहरी शाखा\n\n"
            
            "SOURCE ATTRIBUTION:\n"
            "- Do NOT mention 'the context' or 'the provided text' in your answer.\n"
            "- Answer as if you are the official municipal assistant.\n"
            "- If information from different sources conflicts, note the discrepancy.\n"
            "- Never say 'according to the website' — just state the information directly."
        )

                # Detect language of the question
        has_nepali = any(ord(c) > 2304 for c in question)  # Devanagari Unicode range
        lang_instruction = (
            "Answer in NEPALI only. सबै जानकारी नेपालीमा मात्र दिनुहोस्।"
            if has_nepali 
            else "Answer in ENGLISH only. Translate all information to English."
        )
        
        # User prompt combines the official context with the citizen's question
        user_prompt = (
            f"OFFICIAL MUNICIPAL WEBSITE CONTENT:\n{context}\n\n"
            f"CITIZEN'S QUESTION: {question}\n\n"
            f"LANGUAGE INSTRUCTION: {lang_instruction}\n\n"
            f"FORMAT REMINDER: Use plain text for service names, bullet points (•) for details, "
            f"**bold** only for phone numbers/fees/amounts. No markdown headings."
        )
        # user_prompt — Frames the context as official data and reinforces language rule
        
        # Send to Ollama (free, local AI — no API key needed)
        response = ollama.chat(
            model="llama3.1:8b",
            # model="llama3.1:8b" — Good multilingual model, runs locally
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        # ollama.chat() — Sends the prompt to your local Ollama server
        
        answer = response['message']['content'].strip()
        # response['message']['content'] — Gets the AI's response text
        
        # Return both the formatted answer and its sources
        return {
            "answer": answer,
            "sources": sources
        }
    
    # Step 3: If no AI, return raw search results (offline mode)
    return {
        "answer": context,
        "sources": sources
    }
    # Returns the raw chunks and their source URLs


# ============================================================
# TEST RUNNER: Simple terminal interface for testing
# ============================================================

if __name__ == "__main__":
    # This code only runs when you execute chatbot.py directly
    
    print("\n" + "="*50)
    print("🇳🇵 Bharatpur Municipality Chatbot")
    print("="*50)
    print("Type 'quit' to exit")
    print("Type 'ai on' to enable AI-enhanced answers (Ollama)")
    print("Type 'ai off' to use offline mode")
    print("="*50 + "\n")
    
    ai_mode = False  # Start in offline mode by default
    
    while True:
        # Get user input
        user_input = input("You: ")
        
        # Check for special commands
        if user_input.lower() == 'quit':
            print("Goodbye! 🙏")
            break
        
        if user_input.lower() == 'ai on':
            if ollama_available:
                ai_mode = True
                print("🤖 AI mode enabled (Ollama - Free & Local)\n")
            else:
                print("❌ Ollama not available. Install from https://ollama.com\n")
            continue
        
        if user_input.lower() == 'ai off':
            ai_mode = False
            print("📚 Offline mode (knowledge base only)\n")
            continue
        
        # Get the answer
        result = ask_question(user_input, use_ai=ai_mode)
        # result is a dict with "answer" and "sources"
        
        # Display the answer
        print(f"\nBot: {result['answer']}\n")
        
        # Show sources if available
        if result['sources']:
            print("Sources:")
            for s in result['sources']:
                print(f"  • {s['url']}")
            print()