from flask import Flask, request, jsonify, render_template
from chatbot import ask_question
import os

# ============================================================
# FLASK APP SETUP
# ============================================================

app = Flask(__name__)
# Creates the Flask web application


# ============================================================
# ROUTE 1: Homepage - Serves the chat interface
# ============================================================

@app.route("/")
def index():
    """
    When someone visits http://127.0.0.1:5000/
    Show them the chat interface (index.html)
    """
    return render_template("index.html")
    # render_template looks in the "templates" folder for index.html


# ============================================================
# ROUTE 2: Chat API - Handles messages from the frontend
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():
    """
    Receives a message from the user, processes it through
    the chatbot, and returns the answer with sources as JSON.
    
    Frontend sends: { "message": "user's question", "use_ai": true/false }
    Backend returns: { "reply": "formatted answer", "sources": [...] }
    """
    
    # Step 1: Get the JSON data from the frontend
    data = request.get_json()
    # request.get_json() — Reads the JSON body of the POST request
    
    # Step 2: Extract the message and AI preference
    user_message = data.get("message", "")
    use_ai = data.get("use_ai", False)
    # .get("message", "") — Gets the message, returns "" if not found
    # .get("use_ai", False) — Gets AI mode, defaults to False (offline)
    
    # Step 3: Validate the message
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
        # 400 status code means "Bad Request"
    
    # Step 4: Get the answer from the chatbot
    try:
        # ask_question() returns a dict: { "answer": "...", "sources": [...] }
        result = ask_question(user_message, use_ai=use_ai)
        # Calls your chatbot function from chatbot.py
        # use_ai=True → AI-enhanced formatted answer
        # use_ai=False → Raw knowledge base results
        
        # Step 5: Send the answer and sources back to the frontend
        return jsonify({
            "reply": result["answer"],
            "sources": result.get("sources", [])
        })
        # jsonify converts Python dict to JSON
        # Frontend receives: 
        # {
        #     "reply": "The formatted answer text",
        #     "sources": [
        #         {"title": "...", "url": "https://...", "document": "..."},
        #         ...
        #     ]
        # }
        
    except Exception as e:
        # If anything goes wrong, tell the frontend
        return jsonify({"error": str(e)}), 500
        # 500 status code means "Internal Server Error"


# ============================================================
# RUN THE APP
# ============================================================

if __name__ == "__main__":
    # This only runs when you execute app.py directly
    
    # Check if the templates folder exists
    if not os.path.exists("templates"):
        print("⚠️  Warning: 'templates' folder not found!")
        print("   Create a 'templates' folder and add index.html")
    
    # Check if the chroma_db folder exists
    if not os.path.exists("chroma_db"):
        print("⚠️  Warning: 'chroma_db' folder not found!")
        print("   Run 'python build_kb.py' first to create the knowledge base")
    
    # Start the server
    print("\n" + "="*50)
    print("🇳🇵  Bharatpur Municipality Chatbot Server")
    print("="*50)
    print("Open your browser and go to: http://127.0.0.1:5050")
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5050)
    # debug=True — Auto-reloads when you change code
    # port=5050 — The server runs on http://127.0.0.1:5050