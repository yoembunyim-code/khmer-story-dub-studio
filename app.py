"""KHMER STORY DUB STUDIO - ONE FILE (server + website). Run: uvicorn app:app --host 0.0.0.0 --port 8000"""
import asyncio, json, shutil, subprocess, uuid, threading
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DATA = Path("projects"); DATA.mkdir(exist_ok=True)
MAX_MB = 500; MAX_SEC = 30 * 60; SR = 44100
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
HTML = r'''<!doctype html><html lang="km"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Khmer Story Dub Studio</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0d1a;--card:#151933;--fg:#e8eaff;--mut:#8f95c7;--ac:#6d5dfc;--ac2:#2f7bff;--ok:#2ecc71;--err:#ff5d6c}
:root.light{--bg:#f3f4ff;--card:#fff;--fg:#14163a;--mut:#5b6090}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px 'Noto Sans Khmer',system-ui,sans-serif}
header{display:flex;gap:8px;align-items:center;padding:14px 18px;background:linear-gradient(90deg,#14163a,#3a1d7a);color:#fff}
header h1{font-size:18px;margin:0;flex:1}
main{max-width:980px;margin:auto;padding:14px}
.card{background:var(--card);border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 12px #0003}
h2{margin:0 0 10px;font-size:16px}
button,select,input,textarea{font:inherit;color:var(--fg);background:transparent;border:1px solid #6d5dfc55;border-radius:10px;padding:10px}
button{background:linear-gradient(90deg,var(--ac),var(--ac2));color:#fff;border:0;min-height:44px;cursor:pointer;font-weight:600}
button.sec{background:#6d5dfc33;color:var(--fg)}button:disabled{opacity:.5}
#drop{border:2px dashed var(--ac);border-radius:14px;padding:28px;text-align:center;cursor:pointer;color:var(--mut)}
video{width:100%;max-height:300px;border-radius:10px;background:#000;margin-top:10px}
.bar{height:12px;background:#6d5dfc33;border-radius:8px;overflow:hidden;margin:8px 0}.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--ac),var(--ac2));transition:.3s}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.row>*{flex:1 1 140px}
.seg{display:grid;grid-template-columns:70px 1fr 1fr 70px;gap:6px;margin-bottom:8px;font-size:14px}
.seg textarea{width:100%;min-height:54px}.mut{color:var(--mut);font-size:13px}.err{color:var(--err)}
@media(max-width:700px){.seg{grid-template-columns:1fr}}
</style></head><body>
<header><h1>🎙 KHMER STORY DUB STUDIO</h1>
<input id="api" placeholder="Server: http://192.168.x.x:8000" style="max-width:230px;color:#fff"><button class="sec" id="lang">EN</button><button class="sec" id="theme">☀/🌙</button></header>
<main>
<div class="card"><h2 data-t="s1">1. Upload Video</h2>
<div id="drop" data-t="drop">ទម្លាក់វីដេអូនៅទីនេះ ឬចុចដើម្បីជ្រើស (MP4, MOV, MKV, WEBM)</div>
<input type="file" id="file" accept=".mp4,.mov,.mkv,.webm,video/*" hidden>
<div id="info" class="mut"></div><video id="vid" controls hidden></video>
<div class="row" style="margin-top:10px"><button id="go" disabled data-t="go">ស្តាប់ និងបកប្រែជាខ្មែរ</button><button class="sec" id="rm" disabled data-t="rm">លុបវីដេអូ</button></div></div>
<div class="card"><h2 data-t="prog">Progress</h2><div class="bar"><i id="pb"></i></div><div id="pm" class="mut">–</div></div>
<div class="card" id="edit" hidden><h2 data-t="s2">2. កែអត្ថបទ / Edit Transcript</h2>
<div id="segs"></div>
<div class="row"><button class="sec" id="cpO">Copy Original</button><button class="sec" id="cpK">Copy Khmer</button><button class="sec" id="dlT">Download TXT</button></div></div>
<div class="card" id="voice" hidden><h2 data-t="s3">3. Voice Studio</h2>
<p class="mut" id="honest"></p><div id="spk"></div>
<div class="row"><label>BG volume <input type="range" id="bgv" min="0" max="1" step=".05" value=".25"></label>
<label><input type="checkbox" id="sep"> Separate music (Demucs)</label>
<label><input type="checkbox" id="burn"> Burn subtitles</label></div>
<div class="row" style="margin-top:10px"><button id="dub" data-t="dub">បង្កើតវីដេអូដាក់សំឡេងខ្មែរ</button></div></div>
<div class="card" id="dl" hidden><h2 data-t="s4">4. Download</h2><video id="out" controls></video>
<div class="row" style="margin-top:10px"><button onclick="D('mp4')">MP4</button><button onclick="D('mp3')">MP3</button><button onclick="D('wav')">WAV</button><button onclick="D('srt')">SRT</button><button onclick="D('txt')">Transcript</button></div></div>
</main>
<script>
const $=s=>document.querySelector(s);let API=(localStorage.getItem('api')||'').replace(/\/$/,'');let PID=null,SEGS=[],CAPS={},L='km';
const T={km:{s1:'1. អាប់ឡូតវីដេអូ',drop:'ទម្លាក់វីដេអូនៅទីនេះ ឬចុចដើម្បីជ្រើស (MP4, MOV, MKV, WEBM)',go:'ស្តាប់ និងបកប្រែជាខ្មែរ',rm:'លុបវីដេអូ',prog:'ដំណើរការ',s2:'2. កែអត្ថបទ',s3:'3. ស្ទូឌីយោសំឡេង',dub:'បង្កើតវីដេអូដាក់សំឡេងខ្មែរ',s4:'4. ទាញយក'},
en:{s1:'1. Upload Video',drop:'Drop a video here or click (MP4, MOV, MKV, WEBM)',go:'Transcribe & Translate to Khmer',rm:'Remove Video',prog:'Progress',s2:'2. Edit Transcript',s3:'3. Voice Studio',dub:'Create Khmer Dubbed Video',s4:'4. Download'}};
function tr(){document.querySelectorAll('[data-t]').forEach(e=>e.textContent=T[L][e.dataset.t]);$('#lang').textContent=L=='km'?'EN':'ខ្មែរ'}
$('#lang').onclick=()=>{L=L=='km'?'en':'km';tr()};$('#theme').onclick=()=>document.documentElement.classList.toggle('light');$('#api').value=API;$('#api').onchange=e=>{API=e.target.value.trim().replace(/\/$/,'');localStorage.setItem('api',API);location.reload()};tr();
const err=m=>{$('#pm').innerHTML='<span class=err>'+m+'</span>'};
fetch(API+'/api/capabilities').then(r=>r.json()).then(c=>{CAPS=c;
 $('#honest').textContent='Offline voice (MMS-TTS Khmer) has ONE voice; Deep/Soft only shift pitch. '+(c.edge_tts?'Online male/female voices (Microsoft Edge TTS) send your text to Microsoft.':'Install edge-tts for real male/female voices (online).')+' Lip-sync of mouth movement is NOT provided; only speech timing.';
 $('#sep').disabled=!c.demucs;if(!c.ffmpeg)err('FFmpeg not found on server')});
$('#drop').onclick=()=>$('#file').click();
['dragover','drop'].forEach(e=>$('#drop').addEventListener(e,ev=>{ev.preventDefault();if(e=='drop')up(ev.dataTransfer.files[0])}));
$('#file').onchange=e=>up(e.target.files[0]);
function up(f){if(!f)return;const fd=new FormData();fd.append('file',f);const x=new XMLHttpRequest();x.open('POST',API+'/api/upload');
 x.upload.onprogress=e=>{$('#pb').style.width=(e.loaded/e.total*100)+'%';$('#pm').textContent='Upload '+Math.round(e.loaded/e.total*100)+'%'};
 x.onload=()=>{if(x.status!=200)return err(JSON.parse(x.responseText).detail);const r=JSON.parse(x.responseText);PID=r.id;
  $('#info').textContent=`${r.name} · ${(r.size/1048576).toFixed(1)} MB · ${Math.round(r.duration)}s`;$('#vid').src=API+r.video_url;$('#vid').hidden=false;$('#go').disabled=$('#rm').disabled=false;$('#pm').textContent='Uploaded'};x.send(fd)}
$('#rm').onclick=async()=>{await fetch(API+'/api/project/'+PID,{method:'DELETE'});PID=null;$('#vid').hidden=true;$('#info').textContent='';$('#go').disabled=$('#rm').disabled=true;$('#edit,#voice,#dl').forEach?0:0;['#edit','#voice','#dl'].forEach(s=>$(s).hidden=true)};
function poll(cb){const t=setInterval(async()=>{const s=await (await fetch(API+'/api/status/'+PID)).json();$('#pb').style.width=s.pct+'%';$('#pm').textContent=s.msg+' ('+s.pct+'%)';
 if(s.error){clearInterval(t);err(s.msg)}if(s.done){clearInterval(t);cb(s)}},1500)}
$('#go').onclick=async()=>{await fetch(API+'/api/transcribe/'+PID,{method:'POST'});poll(s=>{SEGS=s.segments;render()})};
function render(){$('#edit').hidden=$('#voice').hidden=false;$('#segs').innerHTML='';
 SEGS.forEach((s,i)=>{const d=document.createElement('div');d.className='seg';
  d.innerHTML=`<div class=mut>${s.start}s<br><select>${[1,2,3].map(n=>`<option ${n==s.speaker?'selected':''}>${n}</option>`).join('')}</select></div><textarea readonly>${s.text}</textarea><textarea>${s.khmer}</textarea><button class=sec>▶</button>`;
  d.querySelector('select').onchange=e=>s.speaker=+e.target.value;d.querySelectorAll('textarea')[1].oninput=e=>s.khmer=e.target.value;
  d.querySelector('button').onclick=()=>{$('#vid').currentTime=s.start;$('#vid').play()};$('#segs').appendChild(d)});
 $('#spk').innerHTML=[1,2,3].map(n=>`<div class=row><b>Speaker ${n}</b><select id=e${n}><option value=mms>Offline MMS</option>${CAPS.edge_tts?'<option value=edge>Online Edge</option>':''}</select>
 <select id=v${n}><option value="km-KH-PisethNeural">Male (Piseth, online)</option><option value="km-KH-SreymomNeural">Female (Sreymom, online)</option></select>
 <select id=p${n}><option value=1>Normal</option><option value=.85>Deep</option><option value=1.12>Soft</option></select>
 <label>Speed<input id=r${n} type=number step=.1 min=.7 max=1.6 value=1></label></div>`).join('')}
const copy=t=>navigator.clipboard.writeText(t);
$('#cpO').onclick=()=>copy(SEGS.map(s=>s.text).join('\n'));$('#cpK').onclick=()=>copy(SEGS.map(s=>s.khmer).join('\n'));
$('#dlT').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([SEGS.map(s=>s.text).join('\n')]));a.download='transcript.txt';a.click()};
$('#dub').onclick=async()=>{const speakers={};[1,2,3].forEach(n=>speakers[n]={engine:$('#e'+n).value,voice:$('#v'+n).value,pitch:+$('#p'+n).value,speed:+$('#r'+n).value,volume:1});
 await fetch(API+'/api/dub/'+PID,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({segments:SEGS,speakers,bg_volume:+$('#bgv').value,separate:$('#sep').checked,burn:$('#burn').checked})});
 poll(()=>{$('#dl').hidden=false;$('#out').src=API+'/api/download/'+PID+'/mp4'})};
function D(k){location.href=API+'/api/download/'+PID+'/'+k}
</script></body></html>
'''
JOBS: dict = {}
_models: dict = {}

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode: raise RuntimeError(r.stderr[-600:])
    return r.stdout

def pdir(pid):
    p = DATA / pid
    if not p.exists(): raise HTTPException(404, "Project not found")
    return p

def duration(path):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)]).strip())

def job(pid, pct, msg, **kw): JOBS[pid] = {"pct": pct, "msg": msg, **kw}

# ---------- upload / project ----------
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".mkv", ".webm"}: raise HTTPException(400, "Use MP4, MOV, MKV or WEBM")
    pid = uuid.uuid4().hex[:10]; p = DATA / pid; p.mkdir()
    dst = p / f"input{ext}"; size = 0
    with open(dst, "wb") as f:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_MB << 20: shutil.rmtree(p); raise HTTPException(413, f"Max {MAX_MB} MB")
            f.write(chunk)
    d = duration(dst)
    if d > MAX_SEC: shutil.rmtree(p); raise HTTPException(413, "Max 30 minutes")
    return {"id": pid, "name": file.filename, "size": size, "duration": d, "video_url": f"/api/file/{pid}/input{ext}"}

@app.get("/api/file/{pid}/{name}")
def get_file(pid: str, name: str):
    f = pdir(pid) / Path(name).name
    if not f.exists(): raise HTTPException(404)
    return FileResponse(f)

@app.delete("/api/project/{pid}")
def delete(pid: str): shutil.rmtree(pdir(pid)); JOBS.pop(pid, None); return {"ok": True}

@app.get("/api/status/{pid}")
def status(pid: str): return JOBS.get(pid, {"pct": 0, "msg": "idle"})

@app.get("/api/capabilities")
def caps():
    def has(m):
        try: __import__(m); return True
        except Exception: return False
    return {"edge_tts": has("edge_tts"), "demucs": shutil.which("demucs") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None}

# ---------- step 1: transcribe + translate ----------
def whisper():
    if "w" not in _models:
        from faster_whisper import WhisperModel
        _models["w"] = WhisperModel("small", compute_type="int8")
    return _models["w"]

NLLB = {"en":"eng_Latn","zh":"zho_Hans","ja":"jpn_Jpan","ko":"kor_Hang","th":"tha_Thai","vi":"vie_Latn",
        "fr":"fra_Latn","es":"spa_Latn","de":"deu_Latn","ru":"rus_Cyrl","hi":"hin_Deva","id":"ind_Latn","km":"khm_Khmr"}

def translate(texts, lang):
    if "t" not in _models:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        n = "facebook/nllb-200-distilled-600M"
        _models["t"] = (AutoTokenizer.from_pretrained(n), AutoModelForSeq2SeqLM.from_pretrained(n))
    tok, m = _models["t"]; tok.src_lang = NLLB.get(lang, "eng_Latn"); out = []
    for t in texts:
        x = tok(t, return_tensors="pt", truncation=True, max_length=256)
        y = m.generate(**x, forced_bos_token_id=tok.convert_tokens_to_ids("khm_Khmr"), max_new_tokens=256, num_beams=4)
        out.append(tok.batch_decode(y, skip_special_tokens=True)[0])
    return out

def do_transcribe(pid):
    try:
        p = DATA / pid; src = next(p.glob("input.*"))
        job(pid, 5, "Extract Audio"); run(["ffmpeg","-y","-i",str(src),"-vn","-ac","1","-ar","16000",str(p/"audio16k.wav")])
        job(pid, 15, "Detect Language + Speech Recognition (first run downloads model)")
        segs, info = whisper().transcribe(str(p/"audio16k.wav"), vad_filter=True)
        segs = [{"id": i, "start": round(s.start,2), "end": round(s.end,2), "text": s.text.strip(), "speaker": 1}
                for i, s in enumerate(segs) if s.text.strip()]
        job(pid, 40, f"Translate to Khmer ({info.language})")
        if info.language == "km": kh = [s["text"] for s in segs]
        else: kh = translate([s["text"] for s in segs], info.language)
        for s, k in zip(segs, kh): s["khmer"] = k
        (p/"segments.json").write_text(json.dumps(segs, ensure_ascii=False))
        job(pid, 100, "Done", done=True, language=info.language, segments=segs)
    except Exception as e: job(pid, 0, f"Error: {e}", error=True)

@app.post("/api/transcribe/{pid}")
def transcribe(pid: str):
    pdir(pid); threading.Thread(target=do_transcribe, args=(pid,), daemon=True).start(); job(pid, 1, "Starting"); return {"ok": True}

# ---------- step 2: TTS + sync + mix ----------
def tts_mms(text, out):
    if "tts" not in _models:
        from transformers import VitsModel, AutoTokenizer
        n = "facebook/mms-tts-khm"
        _models["tts"] = (VitsModel.from_pretrained(n), AutoTokenizer.from_pretrained(n))
    import torch
    m, tok = _models["tts"]
    with torch.no_grad(): w = m(**tok(text, return_tensors="pt")).waveform[0].numpy()
    wavfile.write(out, m.config.sampling_rate, w)

def tts_edge(text, voice, out):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, voice).save(out))

PITCH = {"normal": 1.0, "deep": 0.85, "soft": 1.12}  # MMS has ONE voice; presets only shift pitch

def make_segment(seg, spk, tmp, i):
    raw = str(tmp / f"r{i}.mp3"); fin = tmp / f"s{i}.wav"
    if spk["engine"] == "edge": tts_edge(seg["khmer"], spk["voice"], raw)
    else: raw = raw.replace(".mp3", ".wav"); tts_mms(seg["khmer"], raw)
    pitch = float(spk.get("pitch", 1.0)); slot = max(seg["end"] - seg["start"], 0.3)
    d = duration(raw) / pitch
    tempo = min(max(d / slot, float(spk.get("speed", 1.0))), 1.6)  # speed up to fit slot, never above 1.6x
    f = f"asetrate={SR*pitch},aresample={SR},atempo={tempo:.3f},volume={spk.get('volume',1.0)}"
    run(["ffmpeg","-y","-i",raw,"-af",f,"-ac","1","-ar",str(SR),str(fin)])
    return fin

def srt_time(t): return f"{int(t//3600):02}:{int(t%3600//60):02}:{int(t%60):02},{int(t%1*1000):03}"
def build_srt(segs, key="khmer"):
    return "\n".join(f"{i+1}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s[key]}\n" for i, s in enumerate(segs))

def do_dub(pid, req):
    try:
        p = DATA / pid; src = next(p.glob("input.*")); tmp = p/"tmp"; tmp.mkdir(exist_ok=True)
        segs = sorted(req["segments"], key=lambda s: s["start"]); spks = req["speakers"]; total = duration(src)
        (p/"segments.json").write_text(json.dumps(segs, ensure_ascii=False))
        (p/"subs.srt").write_text(build_srt(segs), encoding="utf-8")
        (p/"transcript.txt").write_text("\n".join(f"[{s['start']:.1f}] {s['text']}" for s in segs), encoding="utf-8")
        track = np.zeros(int((total + 5) * SR), dtype=np.float32); cursor = 0.0
        for i, s in enumerate(segs):
            job(pid, 5 + int(70 * i / len(segs)), f"Generate Khmer Voice {i+1}/{len(segs)}")
            f = make_segment(s, spks[str(s.get("speaker", 1))], tmp, i)
            _, a = wavfile.read(f); a = a.astype(np.float32) / 32768
            st = max(s["start"], cursor)  # no overlap between lines
            o = int(st * SR); track[o:o+len(a)] += a[:len(track)-o]; cursor = st + len(a) / SR
        track = np.clip(track, -1, 1); wavfile.write(p/"khmer.wav", SR, (track*32767).astype(np.int16))
        job(pid, 80, "Mix Audio")
        bg = None
        if req.get("separate") and shutil.which("demucs"):
            job(pid, 82, "Separate music (Demucs, slow)")
            run(["ffmpeg","-y","-i",str(src),"-vn","-ar","44100",str(p/"orig.wav")])
            run(["demucs","--two-stems=vocals","-o",str(p/"sep"),str(p/"orig.wav")])
            bg = next((p/"sep").rglob("no_vocals.wav"), None)
        bgvol = float(req.get("bg_volume", 0.25)); fade = float(req.get("fade", 0.5))
        if bg is None and req.get("separate"): bgvol = min(bgvol, 0.15)  # fallback: original speech stays faintly audible
        bgin = ["-i", str(bg)] if bg else ["-i", str(src)]
        fc = f"[0:a]volume={bgvol}[b];[1:a]volume=1[d];[b][d]amix=inputs=2:duration=first:normalize=0,afade=t=in:d={fade},afade=t=out:st={max(total-fade,0)}:d={fade}[a]"
        run(["ffmpeg","-y",*bgin,"-i",str(p/"khmer.wav"),"-filter_complex",fc,"-map","[a]",str(p/"mix.wav")])
        run(["ffmpeg","-y","-i",str(p/"mix.wav"),"-b:a","192k",str(p/"khmer.mp3")])
        job(pid, 90, "Render Final Video")
        vf = []
        if req.get("burn"):
            sz = int(req.get("font_size", 22)); col = req.get("font_color", "FFFFFF")
            vf = ["-vf", f"subtitles=subs.srt:force_style='FontName=Noto Sans Khmer,FontSize={sz},PrimaryColour=&H{col[4:6]}{col[2:4]}{col[0:2]}&,BorderStyle=3'"]
        run(["ffmpeg","-y","-i",src.name,"-i","mix.wav","-map","0:v:0","-map","1:a",*vf,"-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","192k","-shortest","dubbed.mp4"], cwd=p)
        shutil.rmtree(tmp, ignore_errors=True)
        job(pid, 100, "Download Result", done=True)
    except Exception as e: job(pid, 0, f"Error: {e}", error=True)

@app.post("/api/dub/{pid}")
def dub(pid: str, req: dict):
    pdir(pid); threading.Thread(target=do_dub, args=(pid, req), daemon=True).start(); job(pid, 1, "Starting"); return {"ok": True}

NAMES = {"mp4": "dubbed.mp4", "mp3": "khmer.mp3", "wav": "khmer.wav", "srt": "subs.srt", "txt": "transcript.txt"}
@app.get("/api/download/{pid}/{kind}")
def download(pid: str, kind: str):
    f = pdir(pid) / NAMES.get(kind, "x")
    if not f.exists(): raise HTTPException(404, "Not generated yet")
    return FileResponse(f, filename=f"khmer-dub-{pid}{f.suffix}")

@app.get("/", response_class=HTMLResponse)
def home(): return HTML
