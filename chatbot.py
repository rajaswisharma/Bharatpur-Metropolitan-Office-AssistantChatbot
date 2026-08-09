import chromadb
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

# ============================================================
# SETUP: Load API keys and models ONCE (not on every question)
# ============================================================

# Load variables from .env file (like API keys)
load_dotenv()
# load_dotenv() — Reads the .env file where you store secret keys

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# os.getenv("OPENAI_API_KEY") — Gets the API key. Returns None if not set

# Try to import OpenAI, but don't crash if not installed
try:
    from openai import OpenAI
    # Create OpenAI client only if a key exists
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    
    if openai_client:
        print("✅ OpenAI ready — AI-enhanced answers available.")
    else:
        print("⚠️  No API key found — running in offline mode.")
except ImportError:
    # If openai package isn't even installed, set to None
    openai_client = None
    print("⚠️  OpenAI not installed — running in offline mode.")

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
# SEARCH FUNCTION: Find relevant content in the knowledge base
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
    # Convert the user's question into an embedding (numerical representation)
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
# ANSWER FUNCTION: Generate an answer (offline or AI-enhanced)
# ============================================================

def ask_question(question, use_ai=False):
    """
    Answer a question using the knowledge base.
    
    Parameters:
        question (str): The user's question (Nepali or English)
        use_ai (bool): If True, use OpenAI for a natural answer.
                       If False (default), return raw search results.
    
    Returns:
        str: The answer to the question
    """
    # Step 1: ALWAYS search the knowledge base first
    # This ensures answers are based on the official website, not made up
    chunks = get_relevant_chunks(question)
    # get_relevant_chunks(question) — Finds the 3 best-matching text pieces
    
    context = "\n\n".join(chunks)
    # "\n\n".join(chunks) — Combines the chunks into one block of text
    
    # Step 2 & 3 will be added next (AI or offline response)
    
        # Step 2: If AI is requested AND available, enhance the answer
    if use_ai and openai_client:
        # System prompt tells the AI how to behave
        system_prompt = (
            "You are a helpful assistant for Bharatpur Metropolitan City. "
            "Answer questions using ONLY the provided context. "
            "If the answer is not in the context, say "
            "'यो जानकारी उपलब्ध छैन' (This information is not available). "
            "Respond in the same language as the question (Nepali or English). "
            "Do not make up information."
        )
        # system_prompt — Rules the AI must follow:
        # 1. Only use the context we provide
        # 2. If answer isn't there, admit it in Nepali
        # 3. Reply in the same language as the question
        # 4. Never make up facts
        
        # User prompt combines context and the question
        user_prompt = f"Context from official website:\n{context}\n\nQuestion: {question}\nAnswer:"
        # user_prompt — Packages the context + question together for the AI
        
        # Send to OpenAI and get the response
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        # model="gpt-3.5-turbo" — Fast and cheap OpenAI model
        # temperature=0.3 — Low creativity = sticks to facts (0.0-2.0)
        # max_tokens=300 — Max length of the answer
        
        return response.choices[0].message.content.strip()
        # Returns the AI's natural-sounding answer
    
    # Step 3: If no AI, return raw search results (offline mode)
    return context
    # Returns the raw chunks from the knowledge base



# ============================================================
# TEST RUNNER: Simple terminal interface for testing
# ============================================================

if __name__ == "__main__":
    # This code only runs when you execute chatbot.py directly
    
    print("\n" + "="*50)
    print("🇳🇵 Bharatpur Municipality Chatbot")
    print("="*50)
    print("Type 'quit' to exit")
    print("Type 'ai on' to enable AI-enhanced answers")
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
            if openai_client:
                ai_mode = True
                print("🤖 AI mode enabled\n")
            else:
                print("❌ OpenAI not available. Check your API key.\n")
            continue
        
        if user_input.lower() == 'ai off':
            ai_mode = False
            print("📚 Offline mode (knowledge base only)\n")
            continue
        
        # Get the answer
        answer = ask_question(user_input, use_ai=ai_mode)
        
        # Display the answer
        print(f"\nBot: {answer}\n")