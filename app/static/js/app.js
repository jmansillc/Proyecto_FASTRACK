/**
 * Fastrack — Validador de Precios | Movistar
 * ============================================
 * Lógica del frontend para la carga, validación, auto-corrección
 * y edición inline de archivos Excel.
 */

/**
 * Referencias a elementos del DOM.
 */
const DOM = {
    zonaDrop: document.getElementById("zonaDrop"),
    inputArchivo: document.getElementById("inputArchivo"),
    archivoInfo: document.getElementById("archivoInfo"),
    textoArchivo: document.getElementById("textoArchivo"),
    botonValidar: document.getElementById("botonValidar"),
    barraProgreso: document.getElementById("barraProgreso"),
    panelResumen: document.getElementById("panelResumen"),
    panelCorrecciones: document.getElementById("panelCorrecciones"),
    listaValidaciones: document.getElementById("listaValidaciones"),
    accionesFinales: document.getElementById("accionesFinales"),
    botonDescargarCorregido: document.getElementById("botonDescargarCorregido"),
    // Nuevos elementos para flujo de carga
    accionesCargar: document.getElementById("accionesCargar"),
    botonCargar: document.getElementById("botonCargar"),
    barraCargar: document.getElementById("barraCargar"),
    panelCargaExitosa: document.getElementById("panelCargaExitosa"),
    textoCargaExitosa: document.getElementById("textoCargaExitosa"),
    bodyMisCargas: document.getElementById("bodyMisCargas"),
    tablaMisCargas: document.getElementById("tablaMisCargas"),
    sinCargas: document.getElementById("sinCargas"),
};

/** Archivo actualmente seleccionado. */
let archivoSeleccionado = null;

/** Datos de la última validación. */
let ultimaValidacion = null;

// =================================================================
// EVENTOS DE SELECCIÓN DE ARCHIVO
// =================================================================

DOM.inputArchivo.addEventListener("change", function (e) {
    if (e.target.files.length > 0) seleccionarArchivo(e.target.files[0]);
});

DOM.zonaDrop.addEventListener("dragover", function (e) {
    e.preventDefault();
    DOM.zonaDrop.classList.add("arrastrando");
});

DOM.zonaDrop.addEventListener("dragleave", function () {
    DOM.zonaDrop.classList.remove("arrastrando");
});

DOM.zonaDrop.addEventListener("drop", function (e) {
    e.preventDefault();
    DOM.zonaDrop.classList.remove("arrastrando");
    if (e.dataTransfer.files.length > 0) seleccionarArchivo(e.dataTransfer.files[0]);
});

/**
 * Procesa el archivo seleccionado.
 * @param {File} archivo
 */
function seleccionarArchivo(archivo) {
    if (!archivo.name.endsWith(".xlsx")) {
        alert("Solo se permiten archivos .xlsx");
        return;
    }
    archivoSeleccionado = archivo;
    DOM.textoArchivo.textContent = archivo.name;
    DOM.archivoInfo.style.display = "flex";
    DOM.botonValidar.style.display = "block";
    DOM.botonValidar.disabled = false;
    limpiarResultados();
}

// =================================================================
// ENVÍO AL BACKEND
// =================================================================

DOM.botonValidar.addEventListener("click", async function () {
    if (!archivoSeleccionado) return;

    DOM.botonValidar.disabled = true;
    DOM.botonValidar.textContent = "Validando...";
    DOM.barraProgreso.style.display = "block";
    limpiarResultados();

    try {
        const form = new FormData();
        form.append("archivo", archivoSeleccionado);

        const resp = await fetch("/validar", { method: "POST", body: form });
        const datos = await resp.json();

        if (datos.error) {
            mostrarError(datos.error);
        } else {
            ultimaValidacion = datos;
            mostrarResultados(datos);
        }
    } catch (err) {
        mostrarError("No se pudo conectar con el servidor. Verifique que la API esté corriendo.");
    } finally {
        DOM.botonValidar.disabled = false;
        DOM.botonValidar.textContent = "Validar archivo";
        DOM.barraProgreso.style.display = "none";
    }
});

// =================================================================
// DESCARGA DE EXCEL CORREGIDO
// =================================================================

DOM.botonDescargarCorregido.addEventListener("click", function () {
    window.location.href = "/descargar-corregido";
});

// =================================================================
// FLUJO DE CARGA FINAL A BD
// =================================================================

DOM.botonCargar.addEventListener("click", async function () {
    if (!ultimaValidacion || !archivoSeleccionado) return;

    if (!confirm("Esta seguro de cargar este archivo? Una vez cargado, TI podra procesarlo.")) {
        return;
    }

    DOM.botonCargar.disabled = true;
    DOM.barraCargar.style.display = "block";

    try {
        const resp = await fetch("/cargas/subir", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nombre_archivo: archivoSeleccionado.name,
                total_filas: ultimaValidacion.resumen.total_registros || 0,
                total_errores: ultimaValidacion.resumen.validaciones_fallidas || 0,
                resultado_validacion: ultimaValidacion
            })
        });

        const datos = await resp.json();

        if (resp.ok) {
            DOM.accionesCargar.style.display = "none";
            DOM.panelCargaExitosa.style.display = "block";
            DOM.textoCargaExitosa.textContent = `Archivo "${archivoSeleccionado.name}" enviado a TI correctamente. ID: ${datos.id}`;
            // Limpiar seleccion para evitar doble carga
            archivoSeleccionado = null;
            DOM.botonValidar.disabled = true;
            cargarMisCargas();
        } else {
            alert(datos.error || "Error al subir carga");
            DOM.botonCargar.disabled = false;
        }
    } catch (err) {
        alert("Error de conexion");
        DOM.botonCargar.disabled = false;
    } finally {
        DOM.barraCargar.style.display = "none";
    }
});

// =================================================================
// CARGAR HISTORIAL DE USUARIO
// =================================================================

async function cargarMisCargas() {
    try {
        const resp = await fetch("/cargas/mis-cargas");
        if (!resp.ok) return;
        const datos = await resp.json();

        if (datos.length === 0) {
            DOM.tablaMisCargas.style.display = "none";
            DOM.sinCargas.style.display = "block";
            return;
        }

        DOM.tablaMisCargas.style.display = "table";
        DOM.sinCargas.style.display = "none";
        DOM.bodyMisCargas.innerHTML = "";

        datos.forEach(function (c) {
            const tr = document.createElement("tr");
            const claseEstado = "estado-" + c.estado;
            tr.innerHTML = `
                <td class="celda-fila">${c.id}</td>
                <td>${escapeHtml(c.nombre_archivo)}</td>
                <td class="celda-fila">${c.total_filas || 0}</td>
                <td class="celda-fila">${c.total_errores || 0}</td>
                <td><span class="badge-estado ${claseEstado}">${c.estado}</span></td>
                <td>${formatearFecha(c.fecha_subida)}</td>
            `;
            DOM.bodyMisCargas.appendChild(tr);
        });
    } catch (err) {
        console.error("Error al cargar historial:", err);
    }
}

function formatearFecha(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleDateString("es-CO") + " " + d.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
}

// Cargar historial al inicio
document.addEventListener("DOMContentLoaded", cargarMisCargas);

// =================================================================
// RENDERIZADO
// =================================================================

/**
 * Muestra todos los resultados.
 * @param {Object} datos
 */
function mostrarResultados(datos) {
    const r = datos.resumen;
    const ok = r.es_valido_global;

    // Metadatos
    const ahora = new Date().toLocaleString("es-CO");
    const nombreArchivo = archivoSeleccionado ? archivoSeleccionado.name : "";

    // Panel de resumen
    DOM.panelResumen.className = `panel-resumen ${ok ? "exito" : "error"}`;
    DOM.panelResumen.innerHTML = `
        <div class="resumen-cabecera">
            <div class="resumen-icono">${ok ? "✅" : "⚠️"}</div>
            <div>
                <div class="resumen-titulo">${r.mensaje}</div>
                <div class="resumen-meta">📁 ${escapeHtml(nombreArchivo)} · 🕐 ${ahora}</div>
            </div>
        </div>
        <div class="metricas">
            <div class="metrica exito">
                <div class="numero">${r.validaciones_exitosas}</div>
                <div class="etiqueta">Exitosas</div>
            </div>
            <div class="metrica error">
                <div class="numero">${r.validaciones_fallidas || 0}</div>
                <div class="etiqueta">Fallidas</div>
            </div>
            <div class="metrica total">
                <div class="numero">${r.total_validaciones}</div>
                <div class="etiqueta">Total</div>
            </div>
        </div>
    `;
    DOM.panelResumen.style.display = "block";

    // Panel de correcciones automáticas
    if (datos.correcciones_automaticas) {
        if (datos.correcciones_automaticas.hubo_correcciones) {
            mostrarCorrecciones(datos.correcciones_automaticas);
            DOM.accionesFinales.style.display = "block";
            DOM.botonDescargarCorregido.textContent = "⬇️ Descargar Excel con correcciones automáticas aplicadas";
        } else {
            // No hubo correcciones — mostrar mensaje informativo
            DOM.panelCorrecciones.innerHTML = `
                <div class="correcciones-cabecera">
                    <div class="correcciones-icono">✅</div>
                    <div>
                        <div class="correcciones-titulo" style="color: var(--movistar-verde);">
                            Sin correcciones automáticas necesarias
                        </div>
                        <div class="correcciones-sub">
                            Las columnas de valor fijo (SEGMENTO, MONEDA, TARIFA_SOCIAL) ya tienen los valores correctos.
                        </div>
                    </div>
                </div>
            `;
            DOM.panelCorrecciones.style.display = "block";
        }
    }

    // Tarjetas individuales de validación
    const checks = [
        { clave: "estructura", datos: datos.estructura },
        { clave: "nulos", datos: datos.nulos },
        { clave: "duplicados", datos: datos.duplicados },
        { clave: "unicos", datos: datos.unicos },
        { clave: "precios", datos: datos.precios },
        { clave: "fechas", datos: datos.fechas },
        { clave: "coherencia_fechas", datos: datos.coherencia_fechas },
        { clave: "espacios_en_blanco", datos: datos.espacios_en_blanco },
        { clave: "longitud", datos: datos.longitud },
        { clave: "valores_permitidos", datos: datos.valores_permitidos },
    ];

    checks.forEach(function (v, i) {
        if (!v.datos) return;
        const tarjeta = crearTarjeta(v.datos, i);
        DOM.listaValidaciones.appendChild(tarjeta);
    });

    // --- Mostrar boton de carga final si todo esta OK ---
    if (ok) {
        DOM.accionesCargar.style.display = "block";
        DOM.botonCargar.disabled = false;
    } else {
        DOM.accionesCargar.style.display = "none";
    }
}

/**
 * Muestra el panel de correcciones automáticas.
 */
function mostrarCorrecciones(reporte) {
    let html = `
        <div class="correcciones-cabecera">
            <div class="correcciones-icono">🔧</div>
            <div>
                <div class="correcciones-titulo">Correcciones Automáticas Aplicadas</div>
                <div class="correcciones-sub">${reporte.total_correcciones} celdas corregidas en ${reporte.columnas_corregidas.length} columnas</div>
            </div>
        </div>
    `;

    // Tabla por columna
    for (const [col, info] of Object.entries(reporte.resumen_por_columna)) {
        html += `
            <div class="bloque-correccion">
                <div class="titulo-correccion">
                    📌 ${col} — ${info.filas_corregidas} filas corregidas → valor correcto: <strong>${escapeHtml(info.valor_esperado)}</strong>
                </div>
                <table class="tabla-correcciones">
                    <thead>
                        <tr>
                            <th>Fila Excel</th>
                            <th>Valor Original</th>
                            <th></th>
                            <th>Valor Corregido</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        info.ejemplos.forEach(function (ej) {
            html += `
                <tr>
                    <td class="celda-fila">${ej.fila_excel}</td>
                    <td class="celda-valor-original">${escapeHtml(ej.valor_original)}</td>
                    <td class="celda-flecha">→</td>
                    <td class="celda-valor-corregido">${escapeHtml(info.valor_esperado)}</td>
                </tr>
            `;
        });

        if (info.filas_corregidas > 20) {
            html += `<tr><td colspan="4" class="celda-mas">... y ${info.filas_corregidas - 20} correcciones más</td></tr>`;
        }

        html += `</tbody></table></div>`;
    }

    DOM.panelCorrecciones.innerHTML = html;
    DOM.panelCorrecciones.style.display = "block";
}

/**
 * Crea una tarjeta de validación.
 * @param {Object} datos
 * @param {number} idx
 * @returns {HTMLElement}
 */
function crearTarjeta(datos, idx) {
    const ok = datos.es_valido;
    const cls = ok ? "ok" : "fallo";
    const nombre = datos.nombre_validacion || "Estructura del Archivo";

    // Conteo de errores
    let totalErrores = 0;
    if (datos.errores && typeof datos.errores === "object") {
        totalErrores = Object.keys(datos.errores).length;
    }
    if (datos.total_filas_duplicadas) totalErrores = datos.total_filas_duplicadas;
    if (datos.total_filas_invertidas) totalErrores = datos.total_filas_invertidas;
    if (datos.total_inconsistencias) totalErrores = datos.total_inconsistencias;

    const badgeTexto = ok ? "PASÓ" : (totalErrores > 0 ? `${totalErrores} ERROR${totalErrores > 1 ? "ES" : ""}` : "FALLÓ");

    const tarjeta = document.createElement("div");
    tarjeta.className = "tarjeta";
    tarjeta.style.animationDelay = `${idx * 0.06}s`;

    // Auto-expandir tarjetas fallidas
    if (!ok) {
        tarjeta.classList.add("abierta");
    }

    const cabecera = document.createElement("div");
    cabecera.className = "cabecera";
    cabecera.innerHTML = `
        <div class="info-izquierda">
            <span class="punto-estado ${cls}"></span>
            <span class="nombre-validacion">${nombre}</span>
        </div>
        <div class="info-derecha">
            <span class="badge ${cls}">${badgeTexto}</span>
            <span class="flecha-expandir">▼</span>
        </div>
    `;
    cabecera.addEventListener("click", function () {
        tarjeta.classList.toggle("abierta");
    });

    const detalle = document.createElement("div");
    detalle.className = "panel-detalle";
    detalle.innerHTML = `<div class="detalle-interior">${generarDetalle(datos)}</div>`;

    tarjeta.appendChild(cabecera);
    tarjeta.appendChild(detalle);
    return tarjeta;
}

// =================================================================
// TABLAS DE FILAS CON ERROR
// =================================================================

/**
 * Genera una tabla HTML con las filas afectadas.
 */
function generarTablaFilas(filasExcel, columna, tipoError) {
    if (!filasExcel || filasExcel.length === 0) return "";

    // Para longitud, mostrar columna de longitud
    const tieneLen = filasExcel[0] && filasExcel[0].longitud !== undefined;

    let html = `<table class="tabla-errores">
        <thead>
            <tr>
                <th>Fila Excel</th>
                <th>Columna</th>
                <th>Valor Actual</th>
                ${tieneLen ? "<th>Longitud</th><th>Máximo</th>" : ""}
                <th>Error</th>
            </tr>
        </thead>
        <tbody>`;

    filasExcel.forEach(function (item) {
        const valor = item.valor !== undefined ? item.valor : "—";
        html += `<tr>
            <td class="celda-fila">${item.fila_excel}</td>
            <td>${columna}</td>
            <td class="celda-valor">${escapeHtml(String(valor))}</td>
            ${tieneLen ? `<td class="celda-fila">${item.longitud}</td><td class="celda-fila">${item.maximo}</td>` : ""}
            <td class="celda-error">${tipoError}</td>
        </tr>`;
    });

    html += `</tbody></table>`;
    return html;
}

/**
 * Genera tabla para coherencia de fechas.
 */
function generarTablaFechasInvertidas(filasExcel) {
    if (!filasExcel || filasExcel.length === 0) return "";

    let html = `<table class="tabla-errores">
        <thead>
            <tr>
                <th>Fila Excel</th>
                <th>Fecha Inicio</th>
                <th>Fecha Fin</th>
                <th>Error</th>
            </tr>
        </thead>
        <tbody>`;

    filasExcel.forEach(function (item) {
        html += `<tr>
            <td class="celda-fila">${item.fila_excel}</td>
            <td>${escapeHtml(String(item.fecha_inicio || "—"))}</td>
            <td>${escapeHtml(String(item.fecha_fin || "—"))}</td>
            <td class="celda-error">Fin anterior a inicio</td>
        </tr>`;
    });

    html += `</tbody></table>`;
    return html;
}

/**
 * Genera tabla para escalamiento de precios.
 */
function generarTablaEscalamiento(inconsistencias) {
    if (!inconsistencias || inconsistencias.length === 0) return "";

    let html = `<table class="tabla-errores">
        <thead>
            <tr>
                <th>Fila Excel</th>
                <th>Columna Mayor</th>
                <th>Valor</th>
                <th>Columna Menor</th>
                <th>Valor</th>
            </tr>
        </thead>
        <tbody>`;

    inconsistencias.forEach(function (item) {
        const fila = item.fila_excel !== undefined ? item.fila_excel : (item.fila + 2);
        html += `<tr>
            <td class="celda-fila">${fila}</td>
            <td>${item.columna_mayor}</td>
            <td class="celda-valor">${item.valor_mayor}</td>
            <td>${item.columna_menor}</td>
            <td class="celda-valor">${item.valor_menor}</td>
        </tr>`;
    });

    html += `</tbody></table>`;
    return html;
}

/**
 * Genera tabla para duplicados.
 */
function generarTablaDuplicados(ejemplos, filasExcel) {
    let html = "";

    // Tabla de combinaciones duplicadas
    if (ejemplos && ejemplos.length > 0) {
        const cols = Object.keys(ejemplos[0]);
        html += `<div class="subtitulo-detalle">Combinaciones duplicadas:</div>`;
        html += `<table class="tabla-errores">
            <thead><tr>`;
        cols.forEach(function (c) { html += `<th>${c}</th>`; });
        html += `</tr></thead><tbody>`;
        ejemplos.forEach(function (ej) {
            html += "<tr>";
            cols.forEach(function (c) { html += `<td>${escapeHtml(String(ej[c]))}</td>`; });
            html += "</tr>";
        });
        html += `</tbody></table>`;
    }

    // Filas Excel afectadas
    if (filasExcel && filasExcel.length > 0) {
        const filas = filasExcel.map(function (f) {
            return typeof f === "number" ? f : f.fila_excel;
        });
        html += `<div class="subtitulo-detalle">Filas Excel afectadas:</div>`;
        html += `<div class="filas-lista">${filas.join(", ")}</div>`;
    }

    return html;
}

/**
 * Escapa caracteres HTML para prevenir XSS.
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// =================================================================
// GENERACIÓN DE DETALLE
// =================================================================

/**
 * Genera el HTML del detalle de una validación.
 * @param {Object} d - Datos de la validación
 * @returns {string} HTML
 */
function generarDetalle(d) {
    let h = "";

    // --- Métricas generales ---
    if (d.total_registros !== undefined) {
        h += `<div class="fila-dato"><span class="clave">Total de registros</span><span class="valor">${d.total_registros.toLocaleString()}</span></div>`;
    }
    if (d.total_filas_duplicadas !== undefined) {
        h += `<div class="fila-dato"><span class="clave">Filas duplicadas</span><span class="valor" style="color:${d.total_filas_duplicadas > 0 ? 'var(--movistar-rojo)' : 'var(--movistar-verde)'}">${d.total_filas_duplicadas.toLocaleString()}</span></div>`;
    }
    if (d.total_combinaciones_duplicadas !== undefined) {
        h += `<div class="fila-dato"><span class="clave">Combinaciones duplicadas</span><span class="valor">${d.total_combinaciones_duplicadas}</span></div>`;
    }
    if (d.total_filas_invertidas !== undefined) {
        h += `<div class="fila-dato"><span class="clave">Fechas invertidas</span><span class="valor" style="color:${d.total_filas_invertidas > 0 ? 'var(--movistar-rojo)' : 'var(--movistar-verde)'}">${d.total_filas_invertidas}</span></div>`;
    }
    if (d.total_inconsistencias !== undefined) {
        h += `<div class="fila-dato"><span class="clave">Inconsistencias precio</span><span class="valor" style="color:${d.total_inconsistencias > 0 ? 'var(--movistar-rojo)' : 'var(--movistar-verde)'}">${d.total_inconsistencias}</span></div>`;
    }

    // --- Errores por columna con tabla de filas ---
    if (d.errores && Object.keys(d.errores).length > 0) {
        for (const [col, info] of Object.entries(d.errores)) {
            const msg = typeof info === "string"
                ? info
                : (info.mensaje || JSON.stringify(info));

            h += `<div class="bloque-error">
                <div class="titulo-error">📌 ${col} — ${msg}</div>`;

            // Tabla de filas detallada
            if (info.filas_excel && info.filas_excel.length > 0) {
                h += generarTablaFilas(info.filas_excel, col, msg);
            }

            // Detalle anidado (para precios que tienen sub-errores)
            if (info.detalle && typeof info.detalle === "object") {
                for (const [tipo, subInfo] of Object.entries(info.detalle)) {
                    const subMsg = subInfo.mensaje || tipo;
                    if (subInfo.filas_excel && subInfo.filas_excel.length > 0) {
                        h += `<div class="subtitulo-detalle">${subMsg}:</div>`;
                        h += generarTablaFilas(subInfo.filas_excel, col, subMsg);
                    }
                }
            }

            // Valores encontrados (para validación de únicos)
            if (info.valores_encontrados && info.valores_encontrados.length > 0) {
                h += `<div class="subtitulo-detalle">Valores encontrados: <strong>${info.valores_encontrados.join(", ")}</strong></div>`;
            }

            h += `</div>`;
        }
    }

    // --- Error general (string) ---
    if (d.error && typeof d.error === "string") {
        h += `<div class="bloque-error"><div class="titulo-error">⛔ Error</div><div>${d.error}</div></div>`;
    }

    // --- Duplicados con tabla ---
    if (d.ejemplo_duplicados && d.ejemplo_duplicados.length > 0) {
        h += generarTablaDuplicados(d.ejemplo_duplicados, d.filas_excel_duplicadas);
    }

    // --- Coherencia de fechas con tabla ---
    if (d.filas_excel && d.filas_excel.length > 0 && d.total_filas_invertidas !== undefined) {
        h += generarTablaFechasInvertidas(d.filas_excel);
    }

    // --- Escalamiento de precios con tabla ---
    if (d.inconsistencias && d.inconsistencias.length > 0) {
        h += generarTablaEscalamiento(d.inconsistencias);
    }

    // --- Sin errores ---
    if (h === "" || (d.es_valido && h.indexOf("bloque-error") === -1 && h.indexOf("tabla-errores") === -1)) {
        h += `<div style="color: var(--movistar-verde); font-size: 0.88rem; padding: 4px 0;">Sin errores encontrados ✅</div>`;
    }

    return h;
}

/**
 * Muestra un error general.
 * @param {string} msg
 */
function mostrarError(msg) {
    DOM.panelResumen.className = "panel-resumen error";
    DOM.panelResumen.innerHTML = `
        <div class="resumen-cabecera">
            <div class="resumen-icono">⛔</div>
            <div class="resumen-titulo">${msg}</div>
        </div>
    `;
    DOM.panelResumen.style.display = "block";
}

function limpiarResultados() {
    DOM.panelResumen.style.display = "none";
    DOM.panelResumen.innerHTML = "";
    DOM.panelCorrecciones.style.display = "none";
    DOM.panelCorrecciones.innerHTML = "";
    DOM.listaValidaciones.innerHTML = "";
    DOM.accionesFinales.style.display = "none";
    DOM.accionesCargar.style.display = "none";
    DOM.panelCargaExitosa.style.display = "none";
    ultimaValidacion = null;
}
