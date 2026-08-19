from groq import Groq
import os

# ── Configuration ────────────────────────────────────────────────
API_KEY = ""  # Your gsk_... key

client = Groq(api_key=API_KEY)

# ── Load Real Documents ──────────────────────────────────────────
def load_knowledge_base():
    knowledge = ""
    folder = "knowledge_base"
    
    if not os.path.exists(folder):
        print("❌ knowledge_base folder not found!")
        return ""
    
    files_loaded = []
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                knowledge += f"\n\n=== {filename.upper()} ===\n{content}"
                files_loaded.append(filename)
    
    print(f"✅ Loaded {len(files_loaded)} documents:")
    for f in files_loaded:
        print(f"   📄 {f}")
    print()
    
    return knowledge

# ── System Prompt ────────────────────────────────────────────────
def build_system_prompt(knowledge):
    return f"""
You are TataBot, an AI Knowledge Assistant for Tata Steel's
Learning & Development department.

You help three types of users:
1. New Operators — need safety and basic training guidance
2. Maintenance Technicians — need technical troubleshooting help  
3. L&D Managers — need training reports and workforce insights

IMPORTANT RULES:
- Always answer from the documents provided below
- Keep answers clear, simple and actionable
- Always prioritize safety information
- Detect the user's role from their question and respond accordingly
- End with a helpful follow-up question when appropriate
- If something is not in the documents, say so honestly

HERE ARE YOUR KNOWLEDGE BASE DOCUMENTS:
{knowledge}
"""

# ── Role Detection ───────────────────────────────────────────────
def detect_role(user_input):
    text = user_input.lower()
    
    if any(word in text for word in ["new operator", "new joiner", 
                                      "first day", "just joined", 
                                      "what should i learn"]):
        return "New Operator"
    
    elif any(word in text for word in ["error code", "machine", 
                                        "maintenance", "troubleshoot",
                                        "not working", "repair"]):
        return "Maintenance Technician"
    
    elif any(word in text for word in ["training status", "report", 
                                        "department", "completion",
                                        "workforce", "team"]):
        return "L&D Manager"
    
    else:
        return "Shopfloor Employee"

# ── Chat Interface ───────────────────────────────────────────────
def run_tatabot():
    print("=" * 55)
    print("   TATABOT — AI Knowledge Assistant | Tata Steel")
    print("   Powered by Real L&D Documents")
    print("=" * 55)
    
    # Load documents at startup
    knowledge = load_knowledge_base()
    
    if not knowledge:
        print("❌ No documents found. Please check knowledge_base folder.")
        return
    
    system_prompt = build_system_prompt(knowledge)
    
    # Chat history
    chat_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    print("Type your question and press Enter.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("\nTataBot: Thank you! Stay safe on the shopfloor.")
            break

        # Detect user role
        role = detect_role(user_input)
        
        # Add role context to message
        enhanced_input = f"[User type detected: {role}]\n{user_input}"
        
        chat_history.append({
            "role": "user",
            "content": enhanced_input
        })

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=chat_history,
                max_tokens=500,
                temperature=0.7
            )

            reply = response.choices[0].message.content

            chat_history.append({
                "role": "assistant",
                "content": reply
            })

            print(f"\n🤖 TataBot [{role}]: {reply}\n")
            print("-" * 55)

        except Exception as e:
            print(f"\n❌ Error: {e}\n")

# ── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_tatabot()