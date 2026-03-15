/**
 * Fastrack — Gestión de Perfil y Utilidades
 * ========================================
 * Lógica para cambio de contraseña y modales de confirmación.
 */

// --- MODAL PASS ---
function abrirModalPass() {
    const m = document.getElementById("modalPass");
    if (m) m.classList.add("activo");
}

function cerrarModalPass() {
    const m = document.getElementById("modalPass");
    if (m) {
        m.classList.remove("activo");
        document.getElementById("formCambiarPass").reset();
        document.getElementById("mensajePass").style.display = "none";
    }
}

// --- MODAL CONFIRMACION GENERICO ---
let callbackConfirmacion = null;

function mostrarConfirmacion(titulo, mensaje, textoBoton, esPeligroso, callback) {
    const modal = document.getElementById("modalConfirmacion");
    if (!modal) return;

    document.getElementById("tituloConfirm").textContent = titulo;
    document.getElementById("mensajeConfirm").textContent = mensaje;
    const btn = document.getElementById("btnConfirmar");
    btn.textContent = textoBoton;
    btn.className = "boton-movistar " + (esPeligroso ? "boton-confirmar-eliminar" : "");
    
    callbackConfirmacion = callback;
    modal.classList.add("activo");
}

function cerrarConfirmacion() {
    const modal = document.getElementById("modalConfirmacion");
    if (modal) modal.classList.remove("activo");
    callbackConfirmacion = null;
}

function ejecutarConfirmacion() {
    if (callbackConfirmacion) callbackConfirmacion();
    cerrarConfirmacion();
}

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("formCambiarPass");
    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();
            const actual = document.getElementById("passActual").value;
            const nueva = document.getElementById("passNueva").value;

            try {
                const resp = await fetch("/perfil/cambiar-contrasena", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ actual, nueva })
                });

                const datos = await resp.json();
                const msgDiv = document.getElementById("mensajePass");
                msgDiv.textContent = datos.mensaje || datos.error;
                msgDiv.className = "form-mensaje " + (resp.ok ? "mensaje-exito" : "mensaje-error");
                msgDiv.style.display = "block";

                if (resp.ok) {
                    setTimeout(cerrarModalPass, 2000);
                }
            } catch (err) {
                alert("Error de conexion");
            }
        });
    }
});
