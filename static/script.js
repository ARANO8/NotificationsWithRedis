function actualizarMensajes() {
    $.get("/messages", function(data) {
        $("#messages-list").empty();
        data.forEach(function(mensaje) {
            $("#messages-list").append("<li>" + mensaje + "</li>");
        });
    });
}

setInterval(actualizarMensajes, 2000);

const socket = io.connect(window.location.origin);

// Escuchar el evento 'new_message' para actualizar las listas en tiempo real
socket.on("new_message", function (message) {
    console.log("Mensaje recibido:", message);
    const listaNotificaciones = document.getElementById("notificaciones-lista");
    const listaPrioridad = document.getElementById("notificaciones-prioridad");

    let mensajeTexto = "";
    let prioridad = null;

    // Si el mensaje es un objeto con prioridad (estructura JSON)
    try {
        const parsedMessage = JSON.parse(message);
        if (parsedMessage.mensaje && parsedMessage.prioridad !== undefined) {
            mensajeTexto = `${parsedMessage.mensaje} (Prioridad: ${parsedMessage.prioridad})`;
            prioridad = parseInt(parsedMessage.prioridad);
        } else {
            mensajeTexto = message; // Fallback si no es JSON válido
        }
    } catch (e) {
        mensajeTexto = message; // Fallback si no es JSON
    }

    const notification = document.createElement("li");
    notification.textContent = mensajeTexto;

    // Asignar color si hay prioridad
    if (prioridad !== null) {
        if (prioridad <= 3) {
            notification.style.color = "red";
        } else if (prioridad <= 7) {
            notification.style.color = "orange";
        } else {
            notification.style.color = "green";
        }

        // Insertar en la lista de prioridad ordenadamente
        let inserted = false;
        for (let i = 0; i < listaPrioridad.children.length; i++) {
            const li = listaPrioridad.children[i];
            const match = li.textContent.match(/\(Prioridad: (\d+)\)/);
            if (match) {
                const prioridadExistente = parseInt(match[1]);
                if (prioridad < prioridadExistente) {
                    listaPrioridad.insertBefore(notification, li);
                    inserted = true;
                    break;
                }
            }
        }

        if (!inserted) {
            listaPrioridad.appendChild(notification);
        }
    } else {
        // Mensaje normal (sin prioridad) va a la lista de notificaciones
        listaNotificaciones.appendChild(notification);
    }
});

// Escuchar el evento 'update_messages' para actualizar ambas listas en tiempo real
socket.on("update_messages", function (data) {
    console.log("Actualización de mensajes recibida:", data);

    // Actualizar la lista de mensajes normales
    const listaNotificaciones = document.getElementById("notificaciones-lista");
    listaNotificaciones.innerHTML = ""; // Limpiar la lista
    data.list_messages.forEach((message) => {
        const li = document.createElement("li");
        li.textContent = message.mensaje;
        listaNotificaciones.appendChild(li);
    });

    // Actualizar la lista de mensajes con prioridad
    const listaPrioridad = document.getElementById("notificaciones-prioridad");
    listaPrioridad.innerHTML = ""; // Limpiar la lista
    data.sorted_set_messages.forEach((message) => {
        const li = document.createElement("li");
        li.textContent = `${message.mensaje} (Prioridad: ${message.prioridad})`;

        // Asignar color según la prioridad
        if (message.prioridad <= 3) {
            li.style.color = "red";
        } else if (message.prioridad <= 7) {
            li.style.color = "orange";
        } else {
            li.style.color = "green";
        }

        listaPrioridad.appendChild(li);
    });
});