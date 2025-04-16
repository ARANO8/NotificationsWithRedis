function actualizarMensajes() {
    $.get("/messages", function(data) {
        $("#messages-list").empty();
        data.forEach(function(mensaje) {
            $("#messages-list").append("<li>" + mensaje + "</li>");
        });
    });
}

setInterval(actualizarMensajes, 2000);