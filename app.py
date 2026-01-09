from flask import Flask, render_template, request, jsonify
import subprocess
import os
import base64
import uuid

app = Flask(__name__)

TEMP_DIR = "/tmp/wasm_compiler"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def run_command(cmd_list):
    try:
        # Timeout'u 120 saniyede tutuyoruz
        proc = subprocess.run(cmd_list, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            return False, proc.stderr + "\n" + proc.stdout
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Error: Compilation timed out."
    except Exception as e:
        return False, str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_code():
    lang = request.form.get('language')
    code = request.form.get('code')
    
    unique_id = str(uuid.uuid4())
    base_path = os.path.join(TEMP_DIR, unique_id)
    
    extensions = {
        'cpp': '.cpp',
        'rust': '.rs',
        'assemblyscript': '.ts',
        'go': '.go'
    }
    
    src_file = base_path + extensions.get(lang, '.txt')
    wasm_file = base_path + ".wasm"
    wat_file = base_path + ".wat"

    with open(src_file, "w") as f:
        f.write(code)

    error_msg = None
    success = False

    env = os.environ.copy()
    env["GOCACHE"] = "/tmp/go-cache"
    if not os.path.exists("/tmp/go-cache"):
        os.makedirs("/tmp/go-cache")

    try:
        if lang == 'cpp':
            cmd = ['clang', '--target=wasm32', '-O3', '-nostdlib', '-Wl,--no-entry', '-Wl,--export-all', '-o', wasm_file, src_file]
            success, error_msg = run_command(cmd)

        elif lang == 'rust':
            cmd = ['rustc', '--target=wasm32-unknown-unknown', '--crate-type=cdylib', '-O', '-o', wasm_file, src_file]
            success, error_msg = run_command(cmd)

        elif lang == 'assemblyscript':
            cmd = ['asc', src_file, '-o', wasm_file, '--optimize', '--noAssert']
            success, error_msg = run_command(cmd)
            
        elif lang == 'go':
            cmd = [
                'tinygo', 'build', 
                '-o', wasm_file, 
                '-target=wasm', 
                '-scheduler=none', 
                '-gc=leaking',
                '-no-debug', 
                src_file
            ]
            
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
                if proc.returncode != 0:
                    success = False
                    error_msg = proc.stderr + "\n" + proc.stdout
                else:
                    success = True
            except subprocess.TimeoutExpired:
                success = False
                error_msg = "Error: TinyGo Compilation timed out."

        else:
            return jsonify({'status': 'error', 'output': 'Unsupported language'})

        if not success:
            return jsonify({'status': 'error', 'output': error_msg})

        cmd_wat = ['wasm2wat', wasm_file, '-o', wat_file]
        success_wat, error_wat = run_command(cmd_wat)
        
        if not success_wat:
             return jsonify({'status': 'error', 'output': 'WASM generated but WAT conversion failed:\n' + error_wat})

        with open(wat_file, "r") as f:
            wat_output = f.read()

        with open(wasm_file, "rb") as f:
            wasm_b64 = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({'status': 'success', 'wat': wat_output, 'wasm_b64': wasm_b64})

    except Exception as e:
        return jsonify({'status': 'error', 'output': str(e)})
    
    finally:
        if os.path.exists(src_file): os.remove(src_file)
        if os.path.exists(wasm_file): os.remove(wasm_file)
        if os.path.exists(wat_file): os.remove(wat_file)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
