from flask import Flask, request, jsonify
from groq import Groq
import os

# ── Configuration ────────────────────────────────────────────────
# ⚠️ Security: never hardcode API keys. Use environment variables.
# Local:    export GROQ_API_KEY="gsk_..."
# Vercel:   Project Settings → Environment Variables → GROQ_API_KEY
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

try:
    client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception:
    client = None

app = Flask(__name__)

# ── Load Documents ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_knowledge_folder():
    """Works both on Vercel (api/knowledge_base) and local runs."""
    candidates = [
        os.path.join(BASE_DIR, "knowledge_base"),          # api/knowledge_base (Vercel)
        os.path.join(BASE_DIR, "..", "knowledge_base"),    # project_root/knowledge_base
        "knowledge_base",                                  # cwd
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def load_knowledge_base():
    knowledge = ""
    folder = find_knowledge_folder()
    if not folder:
        return ""
    for filename in sorted(os.listdir(folder)):
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
    "- IMPORTANT: The knowledge base contains a TRAINING STATUS section with aggregate workforce data (total operators, completed training, completion percentage, pending operators, departments needing support). Questions about 'my team', 'our team', 'the team', 'our department', 'workforce', or 'training completion status' refer to THIS data — always answer from it.\n"
    "- IMPORTANT: Only refuse when the documents truly have NOTHING relevant to the question. If a document section covers the topic, answer with the available information and clearly state what is not available. Do not refuse just because the question mentions 'my' or 'our'.\n"
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

# ── HTML Interface — Modern Dark + Glass ─────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TataBot</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; }
body {
  font-family:'Segoe UI', system-ui, -apple-system, sans-serif;
  background:linear-gradient(135deg,#0b1020 0%,#141b33 55%,#0e1528 100%);
  color:#fff; display:flex; flex-direction:column; height:100vh; position:relative; overflow:hidden;
}
body::before {
  content:""; position:absolute; width:420px; height:420px; border-radius:50%;
  background:radial-gradient(circle,rgba(99,102,241,.30),transparent 70%);
  top:-140px; right:-120px; pointer-events:none;
}
body::after {
  content:""; position:absolute; width:380px; height:380px; border-radius:50%;
  background:radial-gradient(circle,rgba(34,211,238,.18),transparent 70%);
  bottom:-140px; left:-110px; pointer-events:none;
}

.header {
  background:rgba(255,255,255,.05); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  padding:14px 22px; display:flex; align-items:center; gap:14px;
  border-bottom:1px solid rgba(255,255,255,.09); position:relative; z-index:5;
}
.logo {
  width:44px; height:44px; border-radius:13px;
  background:linear-gradient(135deg,#6366f1,#22d3ee);
  display:flex; align-items:center; justify-content:center;
  font-size:15px; font-weight:800; color:#fff;
  box-shadow:0 6px 20px rgba(99,102,241,.45);
}
.header h1 { font-size:18px; font-weight:700; letter-spacing:.2px; }
.header p { font-size:11.5px; color:#94a3b8; margin-top:2px; }
.status { margin-left:auto; font-size:11.5px; color:#34d399; white-space:nowrap; }
.clearbtn {
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.14);
  color:#a5b4fc; padding:8px 14px; border-radius:11px; font-size:12px;
  cursor:pointer; transition:.2s;
}
.clearbtn:hover { background:rgba(99,102,241,.25); color:#fff; border-color:rgba(99,102,241,.5); }

.chat {
  flex:1; overflow-y:auto; padding:22px; display:flex; flex-direction:column; gap:14px;
  position:relative; z-index:1;
}
.chat::-webkit-scrollbar { width:5px; }
.chat::-webkit-scrollbar-thumb { background:rgba(99,102,241,.55); border-radius:3px; }
.chat::-webkit-scrollbar-track { background:transparent; }

.welcome {
  background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.12);
  border-radius:18px; padding:26px 22px; text-align:center; margin:6px auto;
  max-width:520px; backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
  box-shadow:0 10px 40px rgba(0,0,0,.25);
}
.welcome .wicon {
  width:58px; height:58px; margin:0 auto 12px; border-radius:17px;
  background:linear-gradient(135deg,#6366f1,#22d3ee);
  display:flex; align-items:center; justify-content:center; font-size:24px;
  box-shadow:0 8px 26px rgba(99,102,241,.5);
}
.welcome h2 {
  font-size:17px; margin-bottom:8px;
  background:linear-gradient(90deg,#a5b4fc,#22d3ee);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.welcome p { color:#94a3b8; font-size:13px; line-height:1.65; }
.welcome .chips { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:14px; }
.welcome .chip {
  background:rgba(99,102,241,.16); border:1px solid rgba(99,102,241,.35);
  color:#a5b4fc; font-size:11px; padding:6px 12px; border-radius:20px;
}

.msg { display:flex; gap:10px; max-width:82%; animation:pop .25s ease; }
@keyframes pop { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
.msg.user { align-self:flex-end; flex-direction:row-reverse; }
.msg.bot { align-self:flex-start; }
.av {
  width:34px; height:34px; border-radius:11px; display:flex; align-items:center;
  justify-content:center; font-size:10.5px; font-weight:800; flex-shrink:0;
}
.user .av { background:#4f46e5; color:#fff; }
.bot .av { background:linear-gradient(135deg,#6366f1,#22d3ee); color:#fff; }
.bubblewrap { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bub { padding:11px 15px; border-radius:16px; font-size:13.5px; line-height:1.65; position:relative; }
.user .bub {
  background:linear-gradient(135deg,#6366f1,#4f46e5); color:#fff;
  border-bottom-right-radius:5px; box-shadow:0 6px 18px rgba(79,70,229,.35);
}
.bot .bub {
  background:rgba(255,255,255,.07); color:#e2e8f0;
  border:1px solid rgba(255,255,255,.12); border-bottom-left-radius:5px;
  backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
}
.bot .bub b { color:#fff; }
.bot .bub code {
  background:rgba(34,211,238,.14); color:#67e8f9; padding:1px 6px;
  border-radius:6px; font-size:12px;
}
.roletag { font-size:9.5px; color:#22d3ee; font-weight:700; letter-spacing:.6px; text-transform:uppercase; margin-bottom:5px; }
.meta { display:flex; gap:10px; align-items:center; font-size:10px; color:#64748b; padding:0 6px; }
.user .meta { justify-content:flex-end; }
.copybtn {
  background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.13);
  color:#94a3b8; font-size:10px; padding:2px 9px; border-radius:8px;
  cursor:pointer; transition:.2s;
}
.copybtn:hover { color:#22d3ee; border-color:rgba(34,211,238,.5); }

.quick { display:flex; flex-wrap:wrap; gap:8px; padding:8px 22px; position:relative; z-index:1; }
.qbtn {
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.14);
  color:#a5b4fc; padding:7px 14px; border-radius:20px; font-size:11.5px;
  cursor:pointer; transition:.2s;
}
.qbtn:hover { background:rgba(99,102,241,.28); color:#fff; border-color:rgba(99,102,241,.55); transform:translateY(-1px); }

.inputrow {
  background:rgba(255,255,255,.05); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  padding:14px 22px 18px; border-top:1px solid rgba(255,255,255,.09);
  display:flex; gap:10px; position:relative; z-index:5;
}
.inputrow input {
  flex:1; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.13);
  border-radius:13px; padding:13px 16px; color:#fff; font-size:14px; outline:none;
  transition:.2s;
}
.inputrow input::placeholder { color:#64748b; }
.inputrow input:focus { border-color:rgba(99,102,241,.65); box-shadow:0 0 0 3px rgba(99,102,241,.22); }
.sendbtn {
  background:linear-gradient(135deg,#6366f1,#22d3ee); color:#fff; border:none;
  border-radius:13px; padding:13px 22px; font-size:14px; font-weight:700;
  cursor:pointer; transition:.2s; box-shadow:0 6px 18px rgba(99,102,241,.4);
}
.sendbtn:hover { transform:translateY(-1px); box-shadow:0 10px 26px rgba(99,102,241,.55); }

.typing { display:flex; gap:5px; padding:12px 16px; align-items:center; }
.typing span {
  width:7px; height:7px; background:#22d3ee; border-radius:50%;
  animation:bounce 1.2s infinite; box-shadow:0 0 8px rgba(34,211,238,.8);
}
.typing span:nth-child(2) { animation-delay:.2s; }
.typing span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { 0%,80%,100% { transform:scale(.75); opacity:.45; } 40% { transform:scale(1.25); opacity:1; } }

@media (max-width:600px) {
  .header { padding:11px 14px; gap:10px; }
  .header p { display:none; }
  .logo { width:38px; height:38px; border-radius:11px; font-size:13px; }
  .header h1 { font-size:15px; }
  .chat { padding:14px; }
  .msg { max-width:94%; }
  .quick { padding:6px 14px; }
  .inputrow { padding:11px 14px 14px; }
  .sendbtn { padding:13px 16px; }
}
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
  <button class="clearbtn" onclick="clearChat()">🗑 Clear Chat</button>
</div>

<div class="chat" id="chat">
  <div class="welcome" id="welcome">
    <div class="wicon">🤖</div>
    <h2>Welcome to TataBot</h2>
    <p>Main aapka AI Knowledge Assistant hoon — Learning &amp; Development ke liye.<br>
    Safety, training modules ya equipment troubleshooting ke baare mein poochho!</p>
    <div class="chips">
      <div class="chip">🦺 Safety Procedures</div>
      <div class="chip">📚 Training Modules</div>
      <div class="chip">🔧 Troubleshooting</div>
    </div>
  </div>
</div>

<div class="quick">
  <button class="qbtn" onclick="ask('What PPE is required in furnace area?')">🦺 PPE Requirements</button>
  <button class="qbtn" onclick="ask('I am a new operator. What should I learn first?')">📚 New Operator Guide</button>
  <button class="qbtn" onclick="ask('Error code E-47 on rolling mill')">🔧 Error E-47</button>
  <button class="qbtn" onclick="ask('Show training completion status for my team')">📊 Training Status</button>
  <button class="qbtn" onclick="ask('What is the LOTO procedure?')">🔒 LOTO Procedure</button>
</div>

<div class="inputrow">
  <input type="text" id="inp" placeholder="Type your question here..." />
  <button class="sendbtn" id="sendbtn">Send</button>
</div>

<script>
var NL = String.fromCharCode(10);
var inp = document.getElementById('inp');
var btn = document.getElementById('sendbtn');
var chat = document.getElementById('chat');
var chatHistory = [];

btn.addEventListener('click', function() { sendMsg(); });
inp.addEventListener('keydown', function(e) { if(e.key === 'Enter') sendMsg(); });

function esc(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function md(text) {
  var h = esc(text);
  h = h.replace(/\\*{2}([^*]+)\\*{2}/g, '<b>$1</b>');
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
  return h.split(NL).join('<br>');
}

function nowTime() {
  return new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
}

function clearChat() {
  chatHistory = [];
  chat.innerHTML = '';
  var w = document.createElement('div');
  w.className = 'welcome';
  w.innerHTML = '<div class="wicon">🤖</div>' +
    '<h2>Welcome to TataBot</h2>' +
    '<p>Main aapka AI Knowledge Assistant hoon — Learning &amp; Development ke liye.<br>' +
    'Safety, training modules ya equipment troubleshooting ke baare mein poochho!</p>' +
    '<div class="chips">' +
    '<div class="chip">🦺 Safety Procedures</div>' +
    '<div class="chip">📚 Training Modules</div>' +
    '<div class="chip">🔧 Troubleshooting</div>' +
    '</div>';
  chat.appendChild(w);
}

function ask(text) {
  inp.value = text;
  sendMsg();
}

function sendMsg() {
  var text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  var w = document.getElementById('welcome');
  if (w) w.remove();
  addMsg(text, 'user', '');
  chatHistory.push({role: 'user', content: text});
  var tid = addTyping();

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/chat', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      removeTyping(tid);
      var replyText = '';
      try {
        var data = JSON.parse(xhr.responseText);
        replyText = data.reply;
        if (xhr.status === 200) {
          chatHistory.push({role: 'assistant', content: data.reply});
          addMsg(data.reply, 'bot', data.role);
          return;
        }
      } catch (e) {}
      addMsg(replyText || 'Sorry, something went wrong. Please try again.', 'bot', '');
    }
  };
  xhr.send(JSON.stringify({message: text, history: chatHistory.slice(0, -1)}));
}

function addMsg(text, type, role) {
  var div = document.createElement('div');
  div.className = 'msg ' + type;

  var av = document.createElement('div');
  av.className = 'av';
  av.textContent = type === 'user' ? 'You' : 'TB';

  var wrap = document.createElement('div');
  wrap.className = 'bubblewrap';

  var bub = document.createElement('div');
  bub.className = 'bub';

  if (type === 'bot' && role) {
    var rt = document.createElement('div');
    rt.className = 'roletag';
    rt.textContent = 'Responding as: ' + role;
    bub.appendChild(rt);
  }

  var content = document.createElement('div');
  content.innerHTML = md(text);
  bub.appendChild(content);
  wrap.appendChild(bub);

  var meta = document.createElement('div');
  meta.className = 'meta';
  var t = document.createElement('span');
  t.textContent = nowTime();
  meta.appendChild(t);
  if (type === 'bot') {
    var cb = document.createElement('button');
    cb.className = 'copybtn';
    cb.textContent = 'Copy';
    cb.addEventListener('click', function() {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
          cb.textContent = '✓ Copied';
          setTimeout(function() { cb.textContent = 'Copy'; }, 1300);
        });
      }
    });
    meta.appendChild(cb);
  }
  wrap.appendChild(meta);

  div.appendChild(av);
  div.appendChild(wrap);
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
    return HTML


@app.route("/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({
            "reply": "⚠️ Server configuration error: GROQ_API_KEY is not set. "
                     "Add it in Vercel → Project Settings → Environment Variables.",
            "role": ""
        }), 500

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"reply": "Please type a question.", "role": ""}), 400

    history = data.get("history") or []
    role = detect_role(user_message)
    enhanced = "[User type: " + role + "]\n" + user_message

    # Build messages: system prompt + recent client history + new message
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-12:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": str(m["content"])[:2000]})
    messages.append({"role": "user", "content": enhanced})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply, "role": role})
    except Exception as e:
        return jsonify({
            "reply": "⚠️ AI service error: " + str(e)[:200] +
                     " — Please try again or contact the administrator.",
            "role": role
        }), 502


# ── Local Run (optional) ─────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("   TATABOT Web Interface Starting...")
    print("   Open your browser and go to:")
    print("   http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, host="127.0.0.1", port=5000)
