/**
 * Fastrack — Panel TI
 * ====================
 * Carga y gestiona archivos pendientes de procesar.
 */

// =================================================================
// INICIALIZACIÓN
// =================================================================

document.addEventListener("DOMContentLoaded", function () {
    cargarPendientes();
    cargarProcesados();
});

// =================================================================
// CARGAR ARCHIVOS PENDIENTES
// =================================================================

async function cargarPendientes() {
    try {
        const resp = await fetch("/cargas/pendientes");
        if (!resp.ok) throw new Error("Error al cargar pendientes");
        const datos = await resp.json();

        const panel = document.getElementById("panelConteo");
        const texto = document.getElementById("textoPendientes");
        const tabla = document.getElementById("tablaArchivos");
        const body = document.getElementById("bodyArchivos");
        const vacio = document.getElementById("sinPendientes");

        panel.style.display = "block";

        if (datos.length === 0) {
            texto.textContent = "No hay archivos pendientes";
            vacio.style.display = "block";
            tabla.style.display = "none";
            return;
        }

        texto.textContent = datos.length + " archivo" + (datos.length > 1 ? "s" : "") + " pendiente" + (datos.length > 1 ? "s" : "");
        vacio.style.display = "none";
        tabla.style.display = "table";
        body.innerHTML = "";

        datos.forEach(function (carga) {
            const tr = document.createElement("tr");
            tr.innerHTML =
                '<td class="celda-fila">' + carga.id + '</td>' +
                '<td>' + escapeHtml(carga.nombre_archivo) + '</td>' +
                '<td>' + escapeHtml(carga.subido_por) + '</td>' +
                '<td class="celda-fila">' + (carga.total_filas || 0) + '</td>' +
                '<td>' + formatearFecha(carga.fecha_subida) + '</td>' +
                '<td class="celda-acciones">' +
                    '<button class="boton-accion boton-procesar" onclick="procesarCarga(' + carga.id + ')">Procesar</button>' +
                    ' <a href="/cargas/descargar/' + carga.id + '" class="boton-accion boton-descargar-sm">Descargar</a>' +
                '</td>';
            body.appendChild(tr);
        });

    } catch (err) {
        console.error("Error:", err);
    }
}

// =================================================================
// PROCESAR ARCHIVO
// =================================================================

async function procesarCarga(id) {
    if (!confirm("Marcar este archivo como procesado?")) return;

    try {
        const resp = await fetch("/cargas/procesar/" + id, { method: "POST" });
        const datos = await resp.json();

        if (resp.ok) {
            cargarPendientes();
            cargarProcesados();
        } else {
            alert(datos.error || "Error al procesar");
        }
    } catch (err) {
        alert("Error de conexion con el servidor");
    }
}

// =================================================================
// CARGAR HISTORIAL PROCESADOS
// =================================================================

async function cargarProcesados() {
    try {
        const resp = await fetch("/cargas/procesados");
        if (!resp.ok) return;
        const datos = await resp.json();

        const tabla = document.getElementById("tablaProcesados");
        const body = document.getElementById("bodyProcesados");
        const vacio = document.getElementById("sinProcesados");

        if (datos.length === 0) {
            tabla.style.display = "none";
            vacio.style.display = "block";
            return;
        }

        tabla.style.display = "table";
        vacio.style.display = "none";
        body.innerHTML = "";

        datos.forEach(function (carga) {
            const tr = document.createElement("tr");
            tr.innerHTML =
                '<td class="celda-fila">' + carga.id + '</td>' +
                '<td>' + escapeHtml(carga.nombre_archivo) + '</td>' +
                '<td>' + escapeHtml(carga.subido_por || "—") + '</td>' +
                '<td>' + formatearFecha(carga.fecha_carga_bd) + '</td>' +
                '<td><span class="badge-estado estado-procesado">Procesado</span></td>';
            body.appendChild(tr);
        });

    } catch (err) {
        console.error("Error:", err);
    }
}

// =================================================================
// UTILIDADES
// =================================================================

function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}

function formatearFecha(iso) {
    if (!iso) return "—";
    try {
        var d = new Date(iso);
        return d.toLocaleDateString("es-CO") + " " + d.toLocaleTimeString("es-CO", {hour: "2-digit", minute: "2-digit"});
    } catch (e) {
        return iso;
    }
}
