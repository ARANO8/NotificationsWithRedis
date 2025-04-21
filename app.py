from flask import Flask, render_template
from flask_socketio import SocketIO
from controllers.notification_controller import (
    send_normal_notification,
    send_priority_notification,
    show_messages,
    handle_request_messages,
    get_updated_messages
)
import threading
import signal
import sys
from models.redis_model import subscribe_to_channel

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

channels = ["canal_general", "canal_alertas"]
stop_threads = False
threads = []  # List to keep track of threads

def signal_handler(sig, frame):
    global stop_threads
    stop_threads = True
    print("Stopping threads...")
    # No need to join daemon threads; they stop automatically
    print("Threads stopped. Exiting application.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def start_listening():
    def callback(data):
        # Emitir el mensaje recibido a todos los clientes conectados
        socketio.emit('new_message', data.decode('utf-8') if isinstance(data, bytes) else data)

        # Emitir las listas actualizadas a los clientes
        emit_updated_messages()

    for channel in channels:
        thread = threading.Thread(target=subscribe_to_channel, args=(channel, callback))
        thread.daemon = True  # Ensure threads exit when the main program exits
        threads.append(thread)
        thread.start()

def emit_updated_messages():
    """Emitir las listas actualizadas a todos los clientes conectados."""
    updated_messages = get_updated_messages()
    socketio.emit('update_messages', updated_messages)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_normal', methods=['POST'])
def send_normal():
    return send_normal_notification()

@app.route('/send_priority', methods=['POST'])
def send_priority():
    return send_priority_notification()

@app.route('/messages')
def messages():
    return show_messages()

@socketio.on('request_messages')
def request_messages():
    handle_request_messages()

@socketio.on('connect')
def handle_connect():
    print("Un cliente se ha conectado.")

@socketio.on('disconnect')
def handle_disconnect():
    print("Un cliente se ha desconectado.")

start_listening()

if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
