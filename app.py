import os, base64, json, requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY", "")

HTML = r"""<!doctype html>
<html lang="hi"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAS Copy Checker</title>
<style>
body{font-family:system-ui;margin:0;background:#f3f5f8;color:#17202a}.box{max-width:800px;margin:auto;padding:14px}
.card{background:white;padding:16px;margin:12px 0;border-radius:14px;box-shadow:0 2px 10px #0001}
input,select,textarea{width:100%;box-sizing:border-box;padding:11px;border:1px solid #ccd4dc;border-radius:8px;font:inherit}
button{width:100%;padding:13px;border:0;border-radius:9px;background:#17213b;color:white;font-weight:700;margin-top:10px}
.upload{border:2px dashed #9da9b5;padding:25px;text-align:center;border-radius:12px}
.row{display:flex;gap:8px}.row>*{flex:1}.score{font-size:45px;font-weight:800}.small{font-size:12px;color:#66727e}
</style><body><div class=box>
<div class=card><h2>RAS Handwritten Copy Checker</h2>
<p class=small>Question अलग से देना जरूरी नहीं। Copy में लिखा question AI पढ़ने की कोशिश करेगा.</p>
<label>Question (optional)</label><textarea id=q rows=2 placeholder="खाली छोड़ सकते हो"></textarea>
<div class=row><div><label>Marks</label><select id=m><option>5</option><option selected>10</option><option>15</option><option>20</option></select></div>
<div><label>Word limit</label><input id=w type=number value=150></div></div></div>
<div class=card><div class=upload onclick="f.click()">📸 Copy के pages चुनें<input id=f type=file accept="image/*" multiple hidden></div>
<div id=p class=small></div><button onclick="go()">🔎 Copy Check करें</button></div>
<div class=card id=r><h3>Result</h3><p class=small>Pages upload करके check करें.</p></div>
</div>
<script>
const f=document.getElementById('f');f.onchange=()=>p.textContent=f.files.length+' page(s) selected';
function b64(x){return new Promise((a,b)=>{let r=new FileReader();r.onload=()=>a(r.result.split(',')[1]);r.onerror=b;r.readAsDataURL(x)})}
async function go(){
 if(!f.files.length)return alert('कम से कम 1 page upload करो');
 r.innerHTML='<h3>Checking…</h3><p>AI copy पढ़ रहा है और marks निकाल रहा है.</p>';
 let fd=new FormData();fd.append('question',q.value);fd.append('marks',m.value);fd.append('limit',w.value);
 for(const x of f.files)fd.append('pages',x);
 try{let z=await fetch('/evaluate',{method:'POST',body:fd}),j=await z.json();if(!z.ok)throw Error(j.error||'Error');
 r.innerHTML='<h3>Estimated Marks</h3><div class=score>'+j.marks+'/'+j.max_marks+'</div>'+
 '<h3>Question</h3><p>'+j.question+'</p><h3>Assessment</h3><p>'+j.assessment+'</p>'+
 '<h3>Strengths</h3><ul>'+j.strengths.map(x=>'<li>'+x+'</li>').join('')+'</ul>'+
 '<h3>Mistakes / Missing</h3><ul>'+j.missing.map(x=>'<li>'+x+'</li>').join('')+'</ul>'+
 '<h3>How to improve</h3><ul>'+j.improve.map(x=>'<li>'+x+'</li>').join('')+'</ul>';
 }catch(e){r.innerHTML='<h3>Problem</h3><p>'+e.message+'</p>'}
}
</script></body></html>"""

@app.get("/")
def home():
    return render_template_string(HTML)

@app.post("/evaluate")
def evaluate():
    if not API_KEY:
        return jsonify(error="Server में GEMINI_API_KEY सेट नहीं है."), 500
    files=request.files.getlist("pages")
    if not files: return jsonify(error="No pages uploaded"),400
    max_marks=int(request.form.get("marks","10"))
    limit=request.form.get("limit","150")
    manual=request.form.get("question","").strip()
    parts=[{"text":f"""You are a strict but fair RAS/RPSC Mains practice examiner.
The question may be written on the uploaded page. Read it yourself if visible. Manual question is optional: {manual or '[none]'}.
Maximum marks: {max_marks}; target words: {limit}.
Evaluate ONLY what is actually written. Do not invent unreadable text.
Check question demand, factual correctness, relevance, introduction, dimensions, analysis, examples/data, Rajasthan-specific value addition where relevant, structure, conclusion, presentation and word-limit.
This is a practice simulation, NOT official RPSC marking.
Return ONLY JSON:
{{"question":"...","marks":0,"max_marks":{max_marks},"assessment":"...","strengths":["..."],"missing":["..."],"improve":["..."]}}
"""}]
    for f in files[:20]:
        data=f.read()
        mime=f.mimetype or "image/jpeg"
        if mime.startswith("image/"):
            parts.append({"inline_data":{"mime_type":mime,"data":base64.b64encode(data).decode()}})
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    payload={"contents":[{"parts":parts}],"generationConfig":{"responseMimeType":"application/json","temperature":0.1}}
    try:
        rr=requests.post(url,json=payload,timeout=180)
        if not rr.ok:
            return jsonify(error="Gemini error: "+rr.text[:500]),502
        text=rr.json()["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify(json.loads(text))
    except Exception as e:
        return jsonify(error=str(e)),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
