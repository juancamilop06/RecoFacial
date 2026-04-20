import os
import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HTML = '''
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Firma con cámara</title>
    <style>
      body { font-family: Arial, sans-serif; margin:0; padding:0; display:flex; flex-direction:column; height:100vh }
      .controls { padding:10px; display:flex; gap:8px; align-items:center; background:#f7f7f7 }
      button { padding:8px 12px }
      .stage { position:relative; flex:1; display:block }
      video, canvas#sig { position:absolute; left:0; top:0; width:100%; height:100%; }
      canvas#sig { touch-action: none; background: transparent }
      #status { margin-left:8px }
    </style>
  </head>
  <body>
    <div class="controls">
      <button id="startRec">Iniciar grabación</button>
      <button id="stopRec" disabled>Detener grabación</button>
      <button id="clear">Limpiar</button>
      <span id="status"></span>
    </div>
    <div class="stage">
      <video id="cam" playsinline autoplay muted></video>
      <canvas id="sig"></canvas>
    </div>

    <script>
    const video = document.getElementById('cam');
    const sig = document.getElementById('sig');
    const status = document.getElementById('status');
    let sigCtx = sig.getContext('2d');

    let stream = null;
    let drawing = false;
    let allowSigning = false; // only allow when recording

    function resize() {
      // keep canvas CSS sized to container; do not change pixel size here
      sig.style.width = '100%';
      sig.style.height = '100%';
      sigCtx.lineWidth = 2;
      sigCtx.lineCap = 'round';
      sigCtx.strokeStyle = '#000';
    }

    window.addEventListener('resize', resize);

    async function startCamera(){
      if(stream) return;
      try{
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = stream;
        await video.play();
        // set canvas pixel size to match actual video resolution
        const vw = video.videoWidth || video.clientWidth;
        const vh = video.videoHeight || video.clientHeight;
        sig.width = vw;
        sig.height = vh;
        resize();
      }catch(e){ status.textContent = 'Error cámara: '+e.message; }
    }

    function getPointerPos(e){
      const rect = sig.getBoundingClientRect();
      const x = (e.clientX - rect.left) * (sig.width / rect.width);
      const y = (e.clientY - rect.top) * (sig.height / rect.height);
      return { x, y };
    }

    sig.addEventListener('pointerdown', e=>{ if(!allowSigning) return; sig.setPointerCapture(e.pointerId); drawing = true; const p=getPointerPos(e); sigCtx.beginPath(); sigCtx.moveTo(p.x,p.y); });
    sig.addEventListener('pointermove', e=>{ if(!drawing) return; const p=getPointerPos(e); sigCtx.lineTo(p.x,p.y); sigCtx.stroke(); });
    sig.addEventListener('pointerup', e=>{ drawing=false; });
    sig.addEventListener('pointercancel', e=>{ drawing=false; });

    document.getElementById('clear').addEventListener('click', ()=>{ sigCtx.clearRect(0,0,sig.width,sig.height); status.textContent=''; });

    // Composite recording: draw video + signature into an offscreen canvas
    let recorder = null;
    let recordedChunks = [];
    let drawInterval = null;

    document.getElementById('startRec').addEventListener('click', async ()=>{
      // start camera and only then allow signing
      await startCamera();
      allowSigning = true;
      sig.style.pointerEvents = 'auto';
      recordedChunks = [];
      const off = document.createElement('canvas');
      // ensure offscreen matches video resolution
      off.width = video.videoWidth || sig.width || 640;
      off.height = video.videoHeight || sig.height || 480;
      const offCtx = off.getContext('2d');

      // draw loop to composite video frame + signature
      drawInterval = setInterval(()=>{
        try{
          offCtx.drawImage(video, 0, 0, off.width, off.height);
          // draw signature scaling to offscreen if sizes differ
          offCtx.drawImage(sig, 0, 0, off.width, off.height);
        }catch(e){ /* ignore while sizing */ }
      }, 33);

      const s = off.captureStream(30);
      let options = { mimeType: 'video/webm;codecs=vp9' };
      if(!MediaRecorder.isTypeSupported(options.mimeType)) options = { mimeType: 'video/webm' };
      recorder = new MediaRecorder(s, options);
      recorder.ondataavailable = e=>{ if(e.data && e.data.size) recordedChunks.push(e.data); };
      recorder.onstop = async ()=>{
        clearInterval(drawInterval);
        allowSigning = false;
        sig.style.pointerEvents = 'none';
        // create video blob
        const videoBlob = new Blob(recordedChunks, { type: recordedChunks[0]?.type || 'video/webm' });

        // get signature image at time of stop
        sig.toBlob(async (imgBlob)=>{
          status.textContent = 'Guardando video...';
          try{
            const fd = new FormData();
            fd.append('file', videoBlob, 'signature_record.webm');
            const res = await fetch('/upload_video', { method:'POST', body: fd });
            const j = await res.json();
            if(j.success){
              status.textContent = 'Video guardado: '+j.filename + ' — Guardando imagen...';
            }else{
              status.textContent = 'Error video';
            }
          }catch(e){ status.textContent = 'Error al subir video'; }

          // then upload image
          try{
            const fd2 = new FormData();
            fd2.append('file', imgBlob, 'signature.png');
            const res2 = await fetch('/upload_image', { method:'POST', body: fd2 });
            const j2 = await res2.json();
            if(j2.success){
              status.textContent = 'Grabación y firma guardadas: '+j2.filename;
            }else{
              status.textContent = 'Error guardando imagen';
            }
          }catch(e){ status.textContent = 'Error al subir imagen final'; }

        }, 'image/png');

        // stop camera tracks
        if(stream){ stream.getTracks().forEach(t=>t.stop()); stream = null; }
        document.getElementById('startRec').disabled = false;
        document.getElementById('stopRec').disabled = true;
      };

      recorder.start();
      document.getElementById('startRec').disabled = true;
      document.getElementById('stopRec').disabled = false;
      status.textContent = 'Grabando...';
    });

    document.getElementById('stopRec').addEventListener('click', ()=>{
      if(recorder && recorder.state === 'recording') recorder.stop();
      status.textContent = 'Deteniendo...';
    });

    </script>
  </body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/signature')
def signature():
    return render_template_string(HTML)


@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        f = request.files.get('file')
        if f is None:
            # try raw data
            data = request.get_data()
            if not data:
                return jsonify({'success': False, 'error': 'No file'})
            filename = f'signature_{int(time.time())}.png'
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'wb') as fh:
                fh.write(data)
        else:
            filename = f'signature_{int(time.time())}.png'
            path = os.path.join(DATA_DIR, filename)
            f.save(path)

        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        f = request.files.get('file')
        if f is None:
            data = request.get_data()
            if not data:
                return jsonify({'success': False, 'error': 'No file'})
            filename = f'signature_{int(time.time())}.webm'
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'wb') as fh:
                fh.write(data)
        else:
            filename = f'signature_{int(time.time())}.webm'
            path = os.path.join(DATA_DIR, filename)
            f.save(path)

        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def run_server(host='127.0.0.1', port=5000):
    # For simple local use; runs until program exits
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_server()
