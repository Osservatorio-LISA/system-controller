from flask import Blueprint, render_template, request, jsonify
from time import sleep, time
import os
import signal

from ext_interface import put_cmd, get_response_buff

# creating blueprint
_here = os.path.dirname(os.path.abspath(__file__))
gui_bp = Blueprint('gui', __name__,
                   template_folder=os.path.join(_here, 'webGui'),
                   static_folder=os.path.join(_here, 'webGui', 'static'),
                   static_url_path='/webGuiStatic')

@gui_bp.route('/')
def home():
    print("_here:", _here)
    print("static_folder exists:", os.path.isdir(os.path.join(_here, 'webGui', 'static')))
    print("files in static:", os.listdir(os.path.join(_here, 'webGui', 'static')))  
    return render_template('index.html')

@gui_bp.route('/api/terminal', methods=['POST'])
def receive_command():
    data = request.json
    cmd_text = data.get('command', '').strip()
    
    if not cmd_text:
        return jsonify({"status": "error", "message": "Comando vuoto"}), 400
        
    # Inseriamo il comando nella coda che legge il cmd_parser
    put_cmd(cmd_text)
    return jsonify({"status": "received"})

@gui_bp.route('/api/terminal', methods=['GET'])
def get_responses():
    deadline = time() + 5.0          # timeout massimo 5 secondi
    while time() < deadline:
        responses = get_response_buff()
        if responses:
            return jsonify({'responses': responses})
        sleep(0.1)
    return jsonify({'responses': []})
    

@gui_bp.route('/shutdown', methods=['POST'])
def shutdown():
    print("[ INFO ] EXITING from web interface and program...")
    # Invia un segnale di interruzione al processo principale (pari a premere Ctrl+C)
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({'messaggio': 'Server in fase di spegnimento...'})