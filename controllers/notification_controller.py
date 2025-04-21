from flask import jsonify, render_template, request
from flask_socketio import emit
import json
from models.redis_model import (
    save_message_to_list,
    save_message_to_sorted_set,
    get_list_messages,
    get_sorted_set_messages,
    publish_message
)

def send_normal_notification():
    message = request.json.get('message')
    if message:
        save_message_to_list(message)
        publish_message('canal_general', message)
        return jsonify({"status": "success", "message": message}), 200
    return jsonify({"status": "error", "message": "Mensaje vacío"}), 400

def send_priority_notification():
    message = request.json.get('message')
    priority = request.json.get('priority', 0)
    if message:
        save_message_to_sorted_set(message, int(priority))
        payload = json.dumps({'mensaje': message, 'prioridad': int(priority)})
        publish_message('canal_general', payload)
        return jsonify({"status": "success", "message": message, "priority": priority}), 200
    return jsonify({"status": "error", "message": "Mensaje vacío"}), 400

def show_messages():
    # Obtener mensajes de la lista
    list_messages = get_list_messages()

    # Obtener mensajes del sorted set
    sorted_set_messages = get_sorted_set_messages()

    # Decodificar y formatear los mensajes de la lista
    formatted_list_messages = [
        {"mensaje": msg.decode('utf-8') if isinstance(msg, bytes) else msg}
        for msg in list_messages
    ]

    # Decodificar y formatear los mensajes del sorted set
    formatted_sorted_set_messages = [
        {
            "mensaje": msg.decode('utf-8') if isinstance(msg, bytes) else msg,
            "prioridad": int(score)
        }
        for msg, score in sorted_set_messages
    ]

    # Ordenar los mensajes del sorted set por prioridad ascendente
    formatted_sorted_set_messages.sort(key=lambda x: x["prioridad"])

    # Pasar los mensajes formateados a la plantilla
    return render_template(
        'messages.html',
        list_messages=formatted_list_messages,
        sorted_set_messages=formatted_sorted_set_messages
    )

def handle_request_messages():
    # Obtener mensajes de la lista
    list_messages = get_list_messages()

    # Obtener mensajes del sorted set
    sorted_set_messages = get_sorted_set_messages()

    # Decodificar y formatear los mensajes de la lista
    formatted_list_messages = [
        {"mensaje": msg.decode('utf-8') if isinstance(msg, bytes) else msg}
        for msg in list_messages
    ]

    # Decodificar y formatear los mensajes del sorted set
    formatted_sorted_set_messages = [
        {
            "mensaje": msg.decode('utf-8') if isinstance(msg, bytes) else msg,
            "prioridad": int(score)
        }
        for msg, score in sorted_set_messages
    ]

    # Emitir los mensajes al cliente, separando las listas
    emit('update_messages', {
        'list_messages': formatted_list_messages,
        'sorted_set_messages': formatted_sorted_set_messages
    })

def get_updated_messages():
    """Obtener las listas actualizadas desde Redis."""
    # Obtener mensajes de la lista
    list_messages = get_list_messages()

    # Obtener mensajes del sorted set
    sorted_set_messages = get_sorted_set_messages()

    # Decodificar y formatear los mensajes de la lista
    formatted_list_messages = [
        {"mensaje": msg.decode('utf-8') if isinstance(msg, bytes) else msg}
        for msg in list_messages
    ]

    # Decodificar y formatear los mensajes del sorted set
    formatted_sorted_set_messages = [
        {
            "mensaje": msg.decode('utf-8') if isinstance(msg, bytes) else msg,
            "prioridad": int(score)
        }
        for msg, score in sorted_set_messages
    ]

    # Ordenar los mensajes del sorted set por prioridad ascendente
    formatted_sorted_set_messages.sort(key=lambda x: x["prioridad"])

    return {
        'list_messages': formatted_list_messages,
        'sorted_set_messages': formatted_sorted_set_messages
    }