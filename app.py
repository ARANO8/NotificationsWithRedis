from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import redis
from redis_config import get_redis_connection
import threading
import signal
import sys
import json
from json import loads
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Configurar CORS para permitir conexiones desde dominios externos
socketio = SocketIO(app, cors_allowed_origins="*")
redis_client = get_redis_connection()

# Lista de canales de notificación
channels = ["canal_general", "canal_alertas"]

# Nombre de la lista en Redis donde se almacenarán los mensajes
REDIS_LIST_NAME = 'notificaciones_list'
REDIS_SORTED_SET_NAME = 'notificaciones_sorted_set'

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
                data = message['data']
                print(f"Mensaje recibido en Redis: {data}")

                # Decodificar si es byte
                if isinstance(data, bytes):
                    data = data.decode('utf-8')

                try:
                    # Intentar parsear como JSON
                    parsed = json.loads(data)

                    # Emitir como objeto si tiene 'mensaje' y 'prioridad'
                    if isinstance(parsed, dict) and 'mensaje' in parsed and 'prioridad' in parsed:
                        print("Emitiendo mensaje con prioridad estructurado a los clientes conectados...")
                        socketio.emit('new_message', parsed)
                        continue
                except Exception as e:
                    pass  # No es JSON válido, seguirá como string plano

                # Emitir mensaje plano
                print("Emitiendo mensaje plano a los clientes conectados...")
                socketio.emit('new_message', data)

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

# Modificar la ruta para manejar mensajes normales y con prioridad
@app.route('/send_normal', methods=['POST'])
def send_normal_notification():
    """Publicar notificación en el canal 'canal_general' y almacenar en la lista de Redis."""
    message = request.json.get('message')

    if message:
        # Almacenar el mensaje en la lista de Redis
        redis_client.lpush(REDIS_LIST_NAME, message)

        # Publicar el mensaje en Redis
        redis_client.publish('canal_general', message)

        return jsonify({"status": "success", "message": message}), 200
    return jsonify({"status": "error", "message": "Mensaje vacío"}), 400

@app.route('/send_priority', methods=['POST'])
def send_priority_notification():
    """Publicar notificación en el canal 'canal_general' y almacenar en el Sorted Set de Redis."""
    message = request.json.get('message')
    priority = request.json.get('priority', 0)  # Prioridad por defecto: 0

    if message:
        # Usar la prioridad como puntuación en el Sorted Set
        score = int(priority)
        redis_client.zadd(REDIS_SORTED_SET_NAME, {message: score})

        # Publicar el mensaje en Redis
        payload = json.dumps({
            'mensaje': message,
            'prioridad': score
        })
        redis_client.publish('canal_general', payload)

        return jsonify({"status": "success", "message": message, "priority": priority}), 200
    return jsonify({"status": "error", "message": "Mensaje vacío"}), 400

@socketio.on('request_messages')
def handle_request_messages():
    # Obtener mensajes de la lista
    list_messages = redis_client.lrange(REDIS_LIST_NAME, 0, -1)

    # No necesitas decodificar si ya vienen como strings en tu caso
    list_messages = [msg for msg in list_messages]

    # Obtener mensajes del sorted set con puntuación
    sorted_set_messages = redis_client.zrange(REDIS_SORTED_SET_NAME, 0, -1, withscores=True)

    # Los mensajes deben venir como [mensaje, puntuación] (ambos tipos compatibles con JS)
    # Si los mensajes son bytes, conviértelos a strings
    formatted_sorted_set = []
    for msg, score in sorted_set_messages:
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8')
        formatted_sorted_set.append([msg, score])

    emit('update_messages', {
        'list_messages': list_messages,
        'sorted_set_messages': formatted_sorted_set
    })


# Eliminar la decodificación innecesaria de mensajes
@app.route('/messages')
def show_messages():
    """Mostrar los mensajes almacenados en Redis en una nueva ventana del navegador."""
    # Leer los mensajes almacenados en la lista de Redis
    list_messages = redis_client.lrange(REDIS_LIST_NAME, 0, -1)  # Obtener todos los elementos de la lista

    # Leer los mensajes almacenados en el Sorted Set de Redis
    sorted_set_messages = redis_client.zrange(REDIS_SORTED_SET_NAME, 0, -1, withscores=True)  # Obtener todos los elementos con sus puntuaciones

    return render_template('messages.html', list_messages=list_messages, sorted_set_messages=sorted_set_messages)

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
