from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import os

# ── Configuration ────────────────────────────────────────────────
API_KEY = ""  # Your gsk_... key

app = Flask(__name__)
client = Groq(api_key=API_KEY)

# ── Load Documents ───────────────────────────────────────────────
def load_knowledge_base():
    knowledge = ""
    folder = "knowledge_base"
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                knowledge += "\n\n=== " + filename.upper() + " ===\n" + f.read()
    return knowledge

KNOWLEDGE = load_knowledge_base()

SYSTEM_PROMPT = (
    "You are TataBot, an AI Knowledge Assistant for Tata Steel Learning and Development.\n"
    
    "You help:\n"
    "1. New Operators\n"
    "2. Maintenance Technicians\n"
    "3. L&D Managers\n\n"

    "IMPORTANT RULES:\n"
    "- Answer ONLY from the knowledge base provided below.\n"
    "- Do NOT use outside knowledge.\n"
    "- Do NOT guess or invent information.\n"
    "- Do NOT create SOP numbers, manual versions, equipment details, safety procedures, or troubleshooting steps that are not present in the documents.\n"
    "- If a user asks about an error code, machine, procedure, SOP, or training module that is not explicitly mentioned in the knowledge base, do not assume or infer the answer.\n"
    "- If the answer is not available in the knowledge base, reply exactly:\n"
    "  'I could not find this information in the available Tata Steel documents.'\n"
    "- Always prioritize safety information.\n"
    "- Keep answers clear, concise, and actionable.\n"
    "- End with a helpful follow-up question when appropriate.\n\n"

    "FORMAT RULES:\n"
"- For safety answers start with: 🦺 SAFETY INFORMATION\n"
"- For maintenance answers start with: 🔧 TROUBLESHOOTING GUIDE\n"
"- For training answers start with: 📚 TRAINING GUIDANCE\n"
"- Use ✓ for bullet points.\n"
"- Use ⚠️ for warnings.\n"
"- Use ✅ for recommended actions.\n"
"- At the end of every answer mention the source document used.\n"
"- Format: Source: filename.txt\n"
"- Do not overuse emojis.\n\n"

    "KNOWLEDGE BASE:\n" + KNOWLEDGE
)

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

# ── Role Detection ───────────────────────────────────────────────
def detect_role(text):
    t = text.lower()
    if any(w in t for w in ["new operator", "new joiner", "what should i learn", "first day"]):
        return "New Operator"
    elif any(w in t for w in ["error code", "machine", "maintenance", "troubleshoot", "repair"]):
        return "Maintenance Technician"
    elif any(w in t for w in ["training status", "report", "department", "completion", "team"]):
        return "L&D Manager"
    else:
        return "Shopfloor Employee"

# ── HTML Interface ───────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TataBot</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',sans-serif; background:#0D1B2A; color:white; display:flex; flex-direction:column; height:100vh; }
.header { background:#1B4F72; padding:16px 24px; display:flex; align-items:center; gap:14px; border-bottom:3px solid #F39C12; }
.logo { width:44px; height:44px; background:#F39C12; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:bold; color:#0D1B2A; }
.header h1 { font-size:18px; }
.header p { font-size:12px; color:#AED6F1; margin-top:2px; }
.status { margin-left:auto; font-size:12px; color:#2ECC71; }
.chat { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:14px; }
.welcome { background:#1B3A5C; border:1px solid #2E86C1; border-radius:10px; padding:16px; text-align:center; }
.welcome h2 { color:#F39C12; margin-bottom:6px; font-size:15px; }
.welcome p { color:#AED6F1; font-size:13px; line-height:1.5; }
.msg { display:flex; gap:10px; max-width:85%; }
.msg.user { align-self:flex-end; flex-direction:row-reverse; }
.msg.bot { align-self:flex-start; }
.av { width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:bold; flex-shrink:0; }
.user .av { background:#2E86C1; color:white; }
.bot .av { background:#F39C12; color:#0D1B2A; }
.bub { padding:11px 15px; border-radius:10px; font-size:13.5px; line-height:1.6; }
.user .bub { background:#2E86C1; color:white; border-bottom-right-radius:3px; }
.bot .bub { background:#1B3A5C; color:#F0F4F8; border:1px solid #2E86C1; border-bottom-left-radius:3px; }
.roletag { font-size:10px; color:#F39C12; font-weight:bold; margin-bottom:4px; text-transform:uppercase; }
.quick { display:flex; flex-wrap:wrap; gap:8px; padding:8px 20px; }
.qbtn { background:#1B3A5C; border:1px solid #2E86C1; color:#AED6F1; padding:6px 12px; border-radius:20px; font-size:11px; cursor:pointer; }
.qbtn:hover { background:#2E86C1; color:white; }
.inputrow { background:#1B3A5C; padding:14px 20px; border-top:1px solid #2E86C1; display:flex; gap:10px; }
.inputrow input { flex:1; background:#0D1B2A; border:1px solid #2E86C1; border-radius:8px; padding:11px 14px; color:white; font-size:14px; outline:none; }
.inputrow input:focus { border-color:#F39C12; }
.sendbtn { background:#F39C12; color:#0D1B2A; border:none; border-radius:8px; padding:11px 20px; font-size:14px; font-weight:bold; cursor:pointer; }
.sendbtn:hover { background:#E67E22; }
.typing { display:flex; gap:4px; padding:8px 12px; align-items:center; }
.typing span { width:7px; height:7px; background:#AED6F1; border-radius:50%; animation:bounce 1.2s infinite; }
.typing span:nth-child(2) { animation-delay:.2s; }
.typing span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { 0%,80%,100%{transform:scale(.8);opacity:.5} 40%{transform:scale(1.2);opacity:1} }
.chat::-webkit-scrollbar { width:4px; }
.chat::-webkit-scrollbar-thumb { background:#2E86C1; border-radius:2px; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">TB</div>
  <div>
    <h1>TataBot</h1>
    <p>AI Knowledge Assistant — Tata Steel L&D</p>
  </div>
  <div class="status">● Online</div>
  <button class="sendbtn" onclick="clearChat()" style="margin-left:10px;">
    🗑 Clear Chat
</button>
</div>

<div class="chat" id="chat">
  <div class="welcome">
    <h2>Welcome to TataBot</h2>
    <p>I am your AI Knowledge Assistant for Learning and Development.<br>
    Ask me about safety, training modules, or equipment troubleshooting.</p>
  </div>
</div>

<div class="quick">
  <button class="qbtn" onclick="ask('What PPE is required in furnace area?')">PPE Requirements</button>
  <button class="qbtn" onclick="ask('I am a new operator. What should I learn first?')">New Operator Guide</button>
  <button class="qbtn" onclick="ask('Error code E-47 on rolling mill')">Error E-47</button>
  <button class="qbtn" onclick="ask('Show training completion status for my team')">Training Status</button>
  <button class="qbtn" onclick="ask('What is the LOTO procedure?')">LOTO Procedure</button>
</div>

<div class="inputrow">
  <input type="text" id="inp" placeholder="Type your question here..." />
  <button class="sendbtn" id="sendbtn">Send</button>
</div>

<script>
var inp = document.getElementById('inp');
var btn = document.getElementById('sendbtn');
var chat = document.getElementById('chat');

btn.addEventListener('click', function() { sendMsg(); });
inp.addEventListener('keydown', function(e) { if(e.key === 'Enter') sendMsg(); });

function clearChat() {

    chat.innerHTML = `
        <div class="welcome">
            <h2>Welcome to TataBot</h2>
            <p>
                I am your AI Knowledge Assistant for Learning and Development.<br>
                Ask me about safety, training modules, or equipment troubleshooting.
            </p>
        </div>
    `;
}

function ask(text) {
  inp.value = text;
  sendMsg();
}

function sendMsg() {
  var text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  addMsg(text, 'user', '');
  var tid = addTyping();

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/chat', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      removeTyping(tid);
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        addMsg(data.reply, 'bot', data.role);
      } else {
        addMsg('Sorry, something went wrong. Please try again.', 'bot', '');
      }
    }
  };
  xhr.send(JSON.stringify({message: text}));
}

function addMsg(text, type, role) {
  var div = document.createElement('div');
  div.className = 'msg ' + type;

  var av = document.createElement('div');
  av.className = 'av';
  av.textContent = type === 'user' ? 'You' : 'TB';

  var bub = document.createElement('div');
  bub.className = 'bub';

  if (type === 'bot' && role) {
    var rt = document.createElement('div');
    rt.className = 'roletag';
    rt.textContent = 'Responding as: ' + role;
    bub.appendChild(rt);
  }

  var content = document.createElement('div');
content.style.whiteSpace = "pre-wrap";
content.textContent = text;
bub.appendChild(content);

  div.appendChild(av);
  div.appendChild(bub);

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function addTyping() {
  var id = 'typing_' + Date.now();
  var div = document.createElement('div');
  div.className = 'msg bot';
  div.id = id;
  var av = document.createElement('div');
  av.className = 'av';
  av.textContent = 'TB';
  var bub = document.createElement('div');
  bub.className = 'bub typing';
  bub.innerHTML = '<span></span><span></span><span></span>';
  div.appendChild(av);
  div.appendChild(bub);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return id;
}

function removeTyping(id) {
  var el = document.getElementById(id);
  if (el) el.remove();
}
</script>

</body>
</html>"""

# ── Routes ───────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    role = detect_role(user_message)
    enhanced = "[User type: " + role + "]\n" + user_message
    chat_history.append({"role": "user", "content": enhanced})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=chat_history,
        max_tokens=500,
        temperature=0.7
    )
    reply = response.choices[0].message.content
    chat_history.append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply, "role": role})

# ── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("   TATABOT Web Interface Starting...")
    print("   Open your browser and go to:")
    print("   http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, host="127.0.0.1", port=5000)
