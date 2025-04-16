from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import redis
from redis_config import get_redis_connection
import threading
import signal
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Configurar CORS para permitir conexiones desde dominios externos
socketio = SocketIO(app, cors_allowed_origins="*")
redis_client = get_redis_connection()

# Lista de canales de notificación
channels = ["canal_general", "canal_alertas"]

# Nombre de la lista en Redis donde se almacenarán los mensajes
REDIS_LIST_NAME = 'notificaciones_list'

# Variable global para controlar la ejecución de los hilos
stop_threads = False

# Mejorar el manejo de cierre de hilos y evitar mensajes redundantes
signal_handled = False  # Variable para evitar múltiples ejecuciones del manejador de señales

def signal_handler(sig, frame):
    global stop_threads, signal_handled

    if signal_handled:
        return  # Evitar múltiples ejecuciones

    signal_handled = True
    print("Deteniendo el servidor y los hilos...")
    stop_threads = True

    # Esperar a que los hilos terminen
    for thread in threading.enumerate():
        if thread is not threading.main_thread():
            print(f"Esperando a que termine el hilo: {thread.name}")
            thread.join(timeout=1)

    # Cerrar la conexión de Redis
    try:
        redis_client.close()
        print("Conexión a Redis cerrada correctamente.")
    except Exception as e:
        print(f"Error al cerrar la conexión a Redis: {e}")

    sys.exit(0)

# Registrar el manejador de señales para detener el servidor de forma segura
signal.signal(signal.SIGINT, signal_handler)

# Modificar la función subscribe_to_channel para manejar el cierre de Redis
def subscribe_to_channel(channel):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)

    try:
        for message in pubsub.listen():
            if stop_threads or redis_client.connection_pool.connection_kwargs.get('host') is None:
                print(f"Deteniendo la escucha en el canal {channel}.")
                break
            if message['type'] == 'message':
                print(f"Mensaje recibido en Redis: {message['data']}")
                print("Emitiendo mensaje a los clientes conectados...")
                socketio.emit('new_message', message['data'])
                print(f"Mensaje emitido a los clientes: {message['data']}")
    except Exception as e:
        if not stop_threads:
            print(f"Error en la suscripción al canal {channel}: {e}")

# Hilo para escuchar mensajes en segundo plano
def start_listening():
    for channel in channels:
        threading.Thread(target=subscribe_to_channel, args=(channel,)).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send_notification():
    """Publicar notificación en el canal 'canal_general' y almacenar en la lista de Redis."""
    message = request.json.get('message')
    if message:
        # Almacenar el mensaje en la lista de Redis
        redis_client.lpush(REDIS_LIST_NAME, message)

        # Publicar el mensaje en Redis (esto es opcional si deseas transmitirlo en tiempo real)
        redis_client.publish('canal_general', message)

        return jsonify({"status": "success", "message": message}), 200
    return jsonify({"status": "error", "message": "Mensaje vacío"}), 400

# Eliminar la decodificación innecesaria de mensajes
@app.route('/messages')
def show_messages():
    """Mostrar los mensajes almacenados en Redis en una nueva ventana del navegador."""
    # Leer los mensajes almacenados en la lista de Redis
    messages = redis_client.lrange(REDIS_LIST_NAME, 0, -1)  # Obtener todos los elementos de la lista
    # No es necesario decodificar los mensajes, ya están en formato de cadena
    return render_template('messages.html', messages=messages)

# Corregir los eventos connect y disconnect
@socketio.on('connect')
def handle_connect(sid):
    print(f"Un cliente se ha conectado. Session ID: {sid}")

@socketio.on('disconnect')
def handle_disconnect(sid):
    print(f"Un cliente se ha desconectado. Session ID: {sid}")

# Iniciar los hilos de escucha
start_listening()

if __name__ == "__main__":
    # Iniciar el servidor Flask con SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
