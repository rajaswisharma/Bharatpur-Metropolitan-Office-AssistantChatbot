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

# ============================================================
# AI SETUP: Google Gemini (Free Cloud AI)
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_API_KEY — Get Gemini key from .env file

gemini_available = False

# Try Gemini (cloud AI - free, fast, excellent Nepali support)
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        # genai — Google's AI library (works with AQ. format keys)
        genai.configure(api_key=GEMINI_API_KEY)
        # genai.configure() — Sets up the Gemini connection using .env key
        gemini_model = genai.GenerativeModel('gemini-3.6-flash')
        # gemini-3.6-flash — Latest fast, free model with excellent multilingual support
        gemini_available = True
        print("✅ Gemini ready — AI-enhanced answers available (free cloud AI).")
    except Exception as e:
        print(f"⚠️  Gemini setup failed: {e}")
else:
    print("ℹ️  No Gemini API key found. Set GEMINI_API_KEY in .env for cloud AI.")

# Final AI status
ai_available = gemini_available
# ai_available — True if Gemini is working

if not ai_available:
    print("⚠️  Gemini not available — will use offline search only.")

# ============================================================
# LOAD MODELS AND DATABASE
# ============================================================

# Load the multilingual embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# embedding_model — Converts text to numbers for searching
# Supports Nepali, English, and 50+ other languages

# Connect to the vector database we built earlier
print("Connecting to knowledge base...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# chromadb.PersistentClient(...) — Opens the database folder on your disk

collection = chroma_client.get_collection("bharatpur_docs")
# collection — Connects to the "bharatpur_docs" collection

print("Ready! You can now ask questions.\n")


# ============================================================
# SOURCE EXTRACTION: Get URLs from chunk labels
# ============================================================

def extract_source_from_chunk(chunk):
    """
    Extract the source URL from a chunk.
    Our chunks are labeled like: '--- Page: https://bharatpurmun.gov.np/en ---'
    """
    match = re.search(r'--- Page: (https?://[^\s]+) ---', chunk)
    if match:
        return match.group(1)
    return None


# ============================================================
# ENHANCED SEARCH: Returns chunks WITH source URLs
# ============================================================

def get_relevant_chunks_with_sources(query, top_k=5):
    """
    Search the knowledge base and return chunks WITH their source URLs.
    """
    query_embedding = embedding_model.encode([query]).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    
    chunks = results['documents'][0]
    
    chunks_with_sources = []
    for chunk in chunks:
        source_url = extract_source_from_chunk(chunk)
        chunks_with_sources.append({
            "text": chunk,
            "source": source_url
        })
    
    return chunks_with_sources


# ============================================================
# SIMPLE SEARCH: Without sources (kept for compatibility)
# ============================================================

def get_relevant_chunks(query, top_k=3):
    """Search the knowledge base for chunks most relevant to the user's question."""
    query_embedding = embedding_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    return results['documents'][0]


# ============================================================
# ANSWER FUNCTION: Smart answer with Gemini + fallback
# ============================================================

def ask_question(question, use_ai=False):
    """
    Answer a question using the knowledge base + Gemini AI.
    
    Strategy:
    1. Search knowledge base first
    2. If context matches question → AI answers from YOUR data
    3. If context doesn't match → AI uses general knowledge with warning
    4. If no AI available → return raw search results
    """
    # Step 1: ALWAYS search the knowledge base first
    chunks_with_sources = get_relevant_chunks_with_sources(question, top_k=5)
    
    # Build context from all chunks
    context = "\n\n---\n\n".join([c["text"] for c in chunks_with_sources])
    
    # Collect unique source URLs
    sources = []
    seen_urls = set()
    
    for chunk in chunks_with_sources:
        url = chunk["source"]
        if url and url not in seen_urls:
            sources.append({
                "title": url.split("/")[-1] or url,
                "url": url,
                "document": "Bharatpur Municipality Website"
            })
            seen_urls.add(url)
    
    # Step 2: If AI is requested AND Gemini is available, generate formatted answer
    if use_ai and gemini_available:
        
        # ============================================================
        # BETTER RELEVANCE CHECK
        # ============================================================
        
        # Get words from both question and context
        question_words = set(question.lower().split())
        context_words = set(context.lower().split())
        word_overlap = question_words & context_words
        
        # Check if context contains Nepali text (Devanagari script)
        # If yes, it's almost certainly relevant since all our data is from Bharatpur site
        has_nepali_context = any(ord(c) > 2304 for c in context[:500])
        # ord(c) > 2304 — Checks for Devanagari Unicode characters
        
        # Count meaningful English word matches
        meaningful_overlap = [w for w in word_overlap if len(w) > 2]
        
        # Consider it relevant if:
        # - At least 1 meaningful English word matches, OR
        # - The context contains Nepali text (our scraped data)
        is_relevant = len(meaningful_overlap) >= 1 or has_nepali_context
        
        # ============================================================
        # SYSTEM PROMPT: Based on relevance
        # ============================================================
        
        if is_relevant:
            # MODE 1: Answer from YOUR scraped data
            system_prompt = (
                "You are a helpful assistant for Bharatpur Metropolitan City, Nepal. "
                "Your role is to provide ACCURATE municipal information.\n\n"
                
                "CRITICAL RULES:\n"
                "1. Use the provided context as your PRIMARY source.\n"
                "2. Preserve exact details: names, fees, phone numbers, dates.\n"
                "3. LANGUAGE: Answer in the SAME language as the question.\n"
                "   - If question is in English → Translate and answer in English\n"
                "   - If question is in Nepali → Answer in Nepali\n"
                "4. FORMAT clearly:\n"
                "   - Plain text for service names (no ## or **)\n"
                "   - Bullet points (•) for details\n"
                "   - **Bold** only for phone numbers, fees, amounts\n"
                "5. Be concise and well-organized.\n"
                "6. Do NOT mention 'the context' or 'the provided text'.\n"
                "7. Answer as the official municipal assistant.\n\n"
                
                "IMPORTANT: The context contains official data from the municipality website. "
                "Use it even if you need to translate from Nepali to English."
            )
        else:
            # MODE 2: No relevant context — use general knowledge
            system_prompt = (
                "You are a helpful assistant. The user is asking about "
                "Bharatpur Metropolitan City, Nepal.\n\n"
                
                "The knowledge base did NOT find matching official information "
                "for this specific question.\n\n"
                
                "RULES:\n"
                "1. START YOUR ANSWER WITH:\n"
                "   '⚠️ यो जानकारी हाम्रो आधिकारिक डाटाबेसमा फेला परेन।'\n"
                "   '(This information was not found in our official database.)'\n"
                "2. Then provide the best general knowledge answer you can.\n"
                "3. Be clear this is NOT official municipal data.\n"
                "4. LANGUAGE: Answer in the SAME language as the question.\n"
                "5. FORMAT: Use bullet points (•) for lists."
            )
        
        # ============================================================
        # LANGUAGE DETECTION
        # ============================================================
        
        has_nepali_question = any(ord(c) > 2304 for c in question)
        lang_instruction = (
            "Answer in NEPALI only."
            if has_nepali_question 
            else "Answer in ENGLISH only."
        )
        
        # ============================================================
        # BUILD USER PROMPT
        # ============================================================
        
        if is_relevant:
            user_prompt = (
                f"OFFICIAL MUNICIPAL CONTEXT:\n{context}\n\n"
                f"QUESTION: {question}\n\n"
                f"LANGUAGE: {lang_instruction}\n\n"
                f"Please answer based primarily on the context above. "
                f"Translate information to match the question language if needed."
            )
        else:
            user_prompt = (
                f"QUESTION: {question}\n\n"
                f"LANGUAGE: {lang_instruction}\n\n"
                f"The knowledge base did not have this information. "
                f"Please help with general knowledge about Bharatpur."
            )
        
        # ============================================================
        # CALL GEMINI
        # ============================================================
        
        try:
            response = gemini_model.generate_content(
                f"{system_prompt}\n\n{user_prompt}"
            )
            answer = response.text.strip()
        except Exception as e:
            answer = f"माफ गर्नुहोस्, जवाफ उत्पन्न गर्न सकिएन। (Error: {str(e)})"
        
        # Return answer with sources (only if from our data)
        return {
            "answer": answer,
            "sources": sources if is_relevant else []
        }
    
    # Step 3: No AI — return raw search results (offline mode)
    return {
        "answer": context,
        "sources": sources
    }


# ============================================================
# TEST RUNNER: Simple terminal interface for testing
# ============================================================

if __name__ == "__main__":
    
    print("\n" + "="*50)
    print("🇳🇵 Bharatpur Municipality Chatbot")
    print("="*50)
    
    if gemini_available:
        print("AI Mode: Google Gemini 3.6 Flash (Free Cloud AI) ✅")
    else:
        print("AI Mode: Offline Only ⚠️")
    
    print("Type 'quit' to exit")
    print("Type 'ai on' for AI-enhanced answers")
    print("Type 'ai off' for offline mode")
    print("="*50 + "\n")
    
    ai_mode = False
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            print("Goodbye! 🙏")
            break
        
        if user_input.lower() == 'ai on':
            if gemini_available:
                ai_mode = True
                print("🤖 AI mode enabled (Gemini 3.6 Flash - Free Cloud)\n")
            else:
                print("❌ Gemini not available. Check your API key.\n")
            continue
        
        if user_input.lower() == 'ai off':
            ai_mode = False
            print("📚 Offline mode (knowledge base only)\n")
            continue
        
        result = ask_question(user_input, use_ai=ai_mode)
        
        print(f"\nBot: {result['answer']}\n")
        
        if result['sources']:
            print("Sources:")
            for s in result['sources']:
                print(f"  • {s['url']}")
            print()