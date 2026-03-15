/**
 * Fastrack — Panel Admin
 * =======================
 * CRUD de usuarios del sistema.
 */

// =================================================================
// INICIALIZACIÓN
// =================================================================

document.addEventListener("DOMContentLoaded", function () {
    cargarUsuarios();

    document.getElementById("formularioUsuario").addEventListener("submit", function (e) {
        e.preventDefault();
        crearUsuario();
    });
});

// =================================================================
// CARGAR USUARIOS
// =================================================================

async function cargarUsuarios() {
    try {
        const resp = await fetch("/admin/usuarios");
        if (!resp.ok) throw new Error("Error al cargar usuarios");
        const datos = await resp.json();

        const body = document.getElementById("bodyUsuarios");
        body.innerHTML = "";

        datos.forEach(function (u) {
            const tr = document.createElement("tr");
            const claseEstado = u.activo ? "estado-activo" : "estado-inactivo";
            const textoEstado = u.activo ? "Activo" : "Inactivo";
            const textoBoton = u.activo ? "Desactivar" : "Activar";
            const claseBoton = u.activo ? "boton-desactivar" : "boton-activar";

            tr.innerHTML =
                '<td class="celda-fila">' + u.id + '</td>' +
                '<td>' + escapeHtml(u.nombre) + '</td>' +
                '<td>' + escapeHtml(u.correo) + '</td>' +
                '<td><span class="badge-rol rol-' + u.rol + '">' + u.rol + '</span></td>' +
                '<td><span class="badge-estado ' + claseEstado + '">' + textoEstado + '</span></td>' +
                '<td>' + formatearFecha(u.fecha_creacion) + '</td>' +
                '<td>' + formatearFecha(u.fecha_creacion) + '</td>' +
                '<td class="celda-acciones">' +
                    '<button class="boton-accion ' + claseBoton + '" onclick="toggleEstado(' + u.id + ', ' + (u.activo ? 'false' : 'true') + ')" title="' + textoBoton + '">' +
                        '<i class="icon">' + (u.activo ? 'De-act' : 'Activar') + '</i>' +
                    '</button>' +
                    '<button class="boton-accion boton-reset" onclick="resetPassword(' + u.id + ')" title="Resetear Contrasena">Reset</button>' +
                    '<button class="boton-accion boton-eliminar" onclick="borrarUsuario(' + u.id + ', \'' + u.correo + '\')" title="Eliminar Usuario">Eliminar</button>' +
                '</td>';
            body.appendChild(tr);
        });

    } catch (err) {
        console.error("Error:", err);
    }
}

// =================================================================
// CREAR USUARIO
// =================================================================

async function crearUsuario() {
    const nombre = document.getElementById("nuevoNombre").value.trim();
    const correo = document.getElementById("nuevoCorreo").value.trim();
    const rol = document.getElementById("nuevoRol").value;
    const contrasena = document.getElementById("nuevaContrasena").value;

    if (!nombre || !correo || !rol || !contrasena) {
        mostrarMensaje("Complete todos los campos", "error");
        return;
    }

    try {
        const resp = await fetch("/admin/usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nombre: nombre,
                correo: correo,
                rol: rol,
                contrasena: contrasena
            })
        });

        const datos = await resp.json();

        if (resp.ok) {
            mostrarMensaje("Usuario creado: " + correo, "exito");
            document.getElementById("formularioUsuario").reset();
            cargarUsuarios();
        } else {
            mostrarMensaje(datos.error || "Error al crear usuario", "error");
        }

    } catch (err) {
        mostrarMensaje("Error de conexion con el servidor", "error");
    }
}

// =================================================================
// TOGGLE ESTADO
// =================================================================

async function toggleEstado(id, activar) {
    try {
        const resp = await fetch("/admin/usuarios/" + id + "/estado", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ activo: activar })
        });

        if (resp.ok) {
            cargarUsuarios();
        } else {
            const datos = await resp.json();
            alert(datos.error || "Error al cambiar estado");
        }
    } catch (err) {
        alert("Error de conexion");
    }
}

// =================================================================
// RESET PASSWORD
// =================================================================

async function resetPassword(id) {
    mostrarConfirmacion(
        "Resetear Contraseña",
        "¿Desea resetear la contrasena de este usuario a 'Fastrack123* '?",
        "Resetear",
        false,
        async function () {
            try {
                const resp = await fetch("/admin/usuarios/" + id + "/reset-password", {
                    method: "PUT"
                });
                const datos = await resp.json();
                if (resp.ok) {
                    alert(datos.mensaje);
                } else {
                    alert(datos.error || "Error al resetear");
                }
            } catch (err) {
                alert("Error de conexion");
            }
        }
    );
}

// =================================================================
// BORRAR USUARIO
// =================================================================

async function borrarUsuario(id, correo) {
    mostrarConfirmacion(
        "Eliminar Usuario",
        "¿ESTA SEGURO de eliminar PERMANENTEMENTE al usuario " + correo + "?",
        "Eliminar",
        true,
        async function () {
            try {
                const resp = await fetch("/admin/usuarios/" + id, {
                    method: "DELETE"
                });
                const datos = await resp.json();
                if (resp.ok) {
                    alert(datos.mensaje);
                    cargarUsuarios();
                } else {
                    alert(datos.error || "Error al eliminar");
                }
            } catch (err) {
                alert("Error de conexion");
            }
        }
    );
}

// =================================================================
// UTILIDADES
// =================================================================

function mostrarMensaje(texto, tipo) {
    const div = document.getElementById("mensajeCrear");
    div.textContent = texto;
    div.className = "form-mensaje " + (tipo === "exito" ? "mensaje-exito" : "mensaje-error");
    div.style.display = "block";

    setTimeout(function () {
        div.style.display = "none";
    }, 5000);
}

function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}

function formatearFecha(iso) {
    if (!iso) return "—";
    try {
        var d = new Date(iso);
        return d.toLocaleDateString("es-CO");
    } catch (e) {
        return iso;
    }
}
