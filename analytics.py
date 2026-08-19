"""
Módulo 8: Reportes y análisis — versión enriquecida.

Cada gráfica regresa: imagen (base64), titulo, subtitulo, eje_x, eje_y,
datos crudos y una conclusion generada automáticamente a partir de los
propios datos (no texto fijo), para que cada reporte se explique solo.
"""
import base64
import io
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from flask import Blueprint, jsonify
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

from extensions import db

reportes_bp = Blueprint("reportes", __name__, url_prefix="/api/reportes")

ROJO = "#E30613"
ROJO_OSCURO = "#A30000"
GRIS = "#4A4A4A"
GRIS_CLARO = "#B8B8B8"
VERDE = "#2E8B57"

plt.rcParams.update({
    "font.size": 11,
    "axes.edgecolor": "#888888",
    "axes.grid": True,
    "grid.color": "#E5E5E5",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
})


def leer_tabla(query):
    return pd.read_sql(query, db.engine)


def _figura_a_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def grafico_barras(labels, valores, *, titulo, subtitulo, eje_x, eje_y,
                    conclusion, color=ROJO, horizontal=False):
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    if horizontal:
        barras = ax.barh(labels, valores, color=color)
        ax.invert_yaxis()
        ax.bar_label(barras, padding=3, fontsize=9)
        ax.set_xlabel(eje_y)
        ax.set_ylabel(eje_x)
    else:
        barras = ax.bar(labels, valores, color=color)
        ax.bar_label(barras, padding=3, fontsize=9)
        ax.set_xlabel(eje_x)
        ax.set_ylabel(eje_y)
        plt.xticks(rotation=30, ha="right")

    fig.suptitle(titulo, fontsize=14, fontweight="bold", x=0.02, ha="left", color="#1A1A1A")
    ax.set_title(subtitulo, fontsize=10, color=GRIS, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    return {
        "imagen_base64": _figura_a_base64(fig),
        "titulo": titulo,
        "subtitulo": subtitulo,
        "eje_x": eje_x,
        "eje_y": eje_y,
        "conclusion": conclusion,
        "datos": [{"etiqueta": str(l), "valor": float(v)} for l, v in zip(labels, valores)],
    }


def grafico_pastel(labels, valores, *, titulo, subtitulo, conclusion):
    colores = [ROJO, GRIS, GRIS_CLARO, ROJO_OSCURO, "#D9A400", "#8C8C8C"]
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.pie(valores, labels=labels, autopct="%1.1f%%", startangle=90,
           colors=colores[: len(labels)], textprops={"fontsize": 10})
    fig.suptitle(titulo, fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title(subtitulo, fontsize=10, color=GRIS)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return {
        "imagen_base64": _figura_a_base64(fig),
        "titulo": titulo,
        "subtitulo": subtitulo,
        "eje_x": None,
        "eje_y": None,
        "conclusion": conclusion,
        "datos": [{"etiqueta": str(l), "valor": float(v)} for l, v in zip(labels, valores)],
    }


# ---------------------------------------------------------------------------
# Indicadores generales
# ---------------------------------------------------------------------------

@reportes_bp.route("/indicadores", methods=["GET"])
def indicadores():
    citas = leer_tabla("SELECT * FROM citas")
    hospitalizaciones = leer_tabla("SELECT * FROM hospitalizaciones")
    pagos = leer_tabla("SELECT * FROM pagos")
    pacientes = leer_tabla("SELECT * FROM pacientes")

    total_citas = len(citas)
    canceladas = int((citas["estado"] == "cancelada").sum())
    tasa_cancelacion = round(canceladas / total_citas * 100, 1) if total_citas else 0

    return jsonify({
        "total_pacientes": len(pacientes),
        "total_citas": total_citas,
        "citas_canceladas": canceladas,
        "tasa_cancelacion_pct": tasa_cancelacion,
        "hospitalizados_actualmente": int((hospitalizaciones["estado"] == "hospitalizado").sum()),
        "ingresos_totales": round(float(pagos["monto"].sum()), 2) if not pagos.empty else 0,
        "ingreso_promedio_por_pago": round(float(pagos["monto"].mean()), 2) if not pagos.empty else 0,
    })


# ---------------------------------------------------------------------------
# 1. Especialidades con mayor demanda
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/especialidades-demanda", methods=["GET"])
def grafico_especialidades_demanda():
    df = leer_tabla("""
        SELECT e.nombre AS especialidad, COUNT(*) AS total
        FROM citas c JOIN medicos m ON c.medico_id = m.id
        JOIN especialidades e ON m.especialidad_id = e.id
        GROUP BY e.nombre ORDER BY total DESC
    """)
    top = df.iloc[0]
    pct = round(top["total"] / df["total"].sum() * 100, 1)
    return jsonify(grafico_barras(
        df["especialidad"], df["total"],
        titulo="Especialidades con mayor demanda",
        subtitulo="Número de citas registradas por especialidad médica",
        eje_x="Especialidad", eje_y="Número de citas",
        conclusion=f"{top['especialidad']} concentra la mayor demanda con {int(top['total'])} citas "
                    f"({pct}% del total registrado). Esto puede orientar la asignación de médicos y consultorios.",
    ))


# ---------------------------------------------------------------------------
# 2. Demanda de servicios médicos (Urgencias / Consultas / Hospitalización / Estudios)
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/demanda-servicios", methods=["GET"])
def grafico_demanda_servicios():
    urgencias = leer_tabla("SELECT COUNT(*) AS n FROM citas WHERE tipo_atencion = 'Urgencia'")["n"][0]
    consultas = leer_tabla("SELECT COUNT(*) AS n FROM citas WHERE tipo_atencion = 'Consulta'")["n"][0]
    seguimientos = leer_tabla("SELECT COUNT(*) AS n FROM citas WHERE tipo_atencion = 'Seguimiento'")["n"][0]
    hospitalizacion = leer_tabla("SELECT COUNT(*) AS n FROM hospitalizaciones")["n"][0]
    estudios = leer_tabla("SELECT COUNT(*) AS n FROM estudios_clinicos")["n"][0]

    servicios = ["Urgencias", "Consultas", "Hospitalización", "Estudios clínicos", "Seguimientos"]
    valores = [int(urgencias), int(consultas), int(hospitalizacion), int(estudios), int(seguimientos)]
    total = sum(valores)
    idx_top = int(np.argmax(valores))

    return jsonify(grafico_barras(
        servicios, valores,
        titulo="Demanda de servicios médicos",
        subtitulo="Volumen de atención por tipo de servicio hospitalario",
        eje_x="Tipo de servicio", eje_y="Número de casos",
        conclusion=f"El servicio más demandado es {servicios[idx_top]} con {valores[idx_top]} casos "
                    f"({round(valores[idx_top]/total*100,1)}% del total). Las urgencias representan "
                    f"{round(urgencias/total*100,1)}% de la atención, lo que ayuda a dimensionar personal de guardia.",
        horizontal=True,
    ))


# ---------------------------------------------------------------------------
# 3. Estudios clínicos por tipo (sangre, orina, heces, etc.)
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/estudios-clinicos", methods=["GET"])
def grafico_estudios_clinicos():
    df = leer_tabla("SELECT tipo, COUNT(*) AS total FROM estudios_clinicos GROUP BY tipo ORDER BY total DESC")
    if df.empty:
        return jsonify({"error": "Aún no hay estudios clínicos registrados."}), 400
    top = df.iloc[0]
    return jsonify(grafico_barras(
        df["tipo"], df["total"],
        titulo="Estudios clínicos más solicitados",
        subtitulo="Frecuencia por tipo de estudio (sangre, orina, heces fecales, imagenología)",
        eje_x="Tipo de estudio", eje_y="Número de estudios",
        conclusion=f"El estudio más solicitado es \"{top['tipo']}\" con {int(top['total'])} órdenes. "
                    f"Priorizar insumos y reactivos para este estudio reduce tiempos de espera.",
        horizontal=True,
    ))


@reportes_bp.route("/grafico/frecuencia-enfermedades", methods=["GET"])
def grafico_frecuencia_enfermedades():
    df = leer_tabla("""
        SELECT descripcion, COUNT(*) AS total FROM diagnosticos
        GROUP BY descripcion ORDER BY total DESC LIMIT 8
    """)
    if df.empty:
        return jsonify({"error": "Aún no hay diagnósticos registrados."}), 400
    top = df.iloc[0]
    return jsonify(grafico_barras(
        df["descripcion"], df["total"],
        titulo="Enfermedades más frecuentes",
        subtitulo="Diagnósticos con mayor número de casos registrados",
        eje_x="Diagnóstico", eje_y="Número de casos",
        conclusion=f"\"{top['descripcion']}\" es el diagnóstico más frecuente ({int(top['total'])} casos). "
                    f"Vale la pena reforzar campañas de prevención enfocadas en esta condición.",
        horizontal=True,
    ))


# ---------------------------------------------------------------------------
# 4. Heatmap de horarios saturados (día x hora)
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/heatmap-horarios", methods=["GET"])
def heatmap_horarios():
    df = leer_tabla("SELECT fecha, hora FROM citas")
    if df.empty:
        return jsonify({"error": "No hay citas registradas."}), 400

    df["fecha"] = pd.to_datetime(df["fecha"])
    dias_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    df["dia"] = df["fecha"].dt.dayofweek.map(lambda d: dias_nombre[d])
    horas_orden = sorted(df["hora"].unique())

    tabla_pivote = (
        df.groupby(["dia", "hora"]).size().unstack(fill_value=0)
        .reindex(index=dias_nombre, columns=horas_orden, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(9, 4.6))
    # Verde = libre, Rojo = saturado
    mapa = ax.imshow(tabla_pivote.values, cmap="RdYlGn_r", aspect="auto")
    ax.set_xticks(range(len(horas_orden)))
    ax.set_xticklabels(horas_orden, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(dias_nombre)))
    ax.set_yticklabels(dias_nombre, fontsize=9)
    for i in range(tabla_pivote.shape[0]):
        for j in range(tabla_pivote.shape[1]):
            valor = tabla_pivote.values[i, j]
            if valor > 0:
                ax.text(j, i, int(valor), ha="center", va="center", fontsize=8,
                        color="white" if valor >= tabla_pivote.values.max() * 0.5 else "#333333")

    cbar = fig.colorbar(mapa, ax=ax, shrink=0.85)
    cbar.set_label("Número de citas (verde = libre, rojo = saturado)", fontsize=9)
    fig.suptitle("Mapa de calor de horarios", fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title("Concentración de citas por día de la semana y horario", fontsize=10, color=GRIS, loc="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    suma_por_dia = tabla_pivote.sum(axis=1)
    dia_mas_saturado = suma_por_dia.idxmax()
    dia_mas_libre = suma_por_dia.idxmin()
    idx_max = np.unravel_index(np.argmax(tabla_pivote.values), tabla_pivote.values.shape)
    hora_pico = horas_orden[idx_max[1]]

    return jsonify({
        "imagen_base64": _figura_a_base64(fig),
        "titulo": "Mapa de calor de horarios",
        "subtitulo": "Concentración de citas por día de la semana y horario",
        "eje_x": "Horario",
        "eje_y": "Día de la semana",
        "conclusion": f"{dia_mas_saturado} es el día más saturado (pico a las {hora_pico} hrs), mientras que "
                       f"{dia_mas_libre} tiene la menor demanda. Conviene reforzar personal los "
                       f"{dia_mas_saturado.lower()}s por la mañana y usar {dia_mas_libre.lower()} para mantenimiento o citas de seguimiento.",
    })


# ---------------------------------------------------------------------------
# 5. Medicamentos: uso, precio vs demanda, y caducidad
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/uso-medicamentos", methods=["GET"])
def grafico_uso_medicamentos():
    df = leer_tabla("""
        SELECT med.nombre AS medicamento, COUNT(*) AS total
        FROM tratamientos t JOIN medicamentos med ON t.medicamento_id = med.id
        GROUP BY med.nombre ORDER BY total DESC
    """)
    top = df.iloc[0]
    return jsonify(grafico_barras(
        df["medicamento"], df["total"],
        titulo="Medicamentos más utilizados",
        subtitulo="Número de veces recetado por medicamento",
        eje_x="Medicamento", eje_y="Veces recetado",
        conclusion=f"\"{top['medicamento']}\" es el medicamento más recetado ({int(top['total'])} veces), "
                    f"por lo que su abasto debe vigilarse con mayor frecuencia que el resto del catálogo.",
        horizontal=True,
    ))


@reportes_bp.route("/grafico/medicamentos-precio-demanda", methods=["GET"])
def grafico_medicamentos_precio_demanda():
    df = leer_tabla("""
        SELECT med.nombre AS medicamento, med.precio_unitario AS precio,
               COUNT(t.id) AS demanda
        FROM medicamentos med LEFT JOIN tratamientos t ON t.medicamento_id = med.id
        GROUP BY med.id
    """)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.scatter(df["precio"], df["demanda"], s=90, color=ROJO, edgecolors=ROJO_OSCURO, zorder=3)
    for _, fila in df.iterrows():
        ax.annotate(fila["medicamento"].split()[0], (fila["precio"], fila["demanda"]),
                    fontsize=8, xytext=(5, 4), textcoords="offset points", color=GRIS)
    ax.set_xlabel("Precio unitario ($)")
    ax.set_ylabel("Veces recetado (demanda)")
    fig.suptitle("Medicamentos: precio vs. demanda", fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title("Relación entre el costo unitario y la frecuencia de uso", fontsize=10, color=GRIS, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    correlacion = df["precio"].corr(df["demanda"]) if len(df) > 2 else 0
    if pd.isna(correlacion):
        correlacion = 0
    tendencia = "inversa (a mayor precio, menor demanda)" if correlacion < -0.2 else (
        "directa (a mayor precio, mayor demanda)" if correlacion > 0.2 else "poco clara"
    )

    return jsonify({
        "imagen_base64": _figura_a_base64(fig),
        "titulo": "Medicamentos: precio vs. demanda",
        "subtitulo": "Relación entre el costo unitario y la frecuencia de uso",
        "eje_x": "Precio unitario ($)", "eje_y": "Veces recetado",
        "conclusion": f"La relación entre precio y demanda es {tendencia} (correlación de {round(correlacion,2)}). "
                       f"Esto ayuda a anticipar si el costo del medicamento influye en su prescripción.",
        "datos": df.to_dict(orient="records"),
    })


@reportes_bp.route("/grafico/medicamentos-caducidad", methods=["GET"])
def grafico_medicamentos_caducidad():
    df = leer_tabla("SELECT nombre, fecha_caducidad, stock FROM medicamentos WHERE fecha_caducidad IS NOT NULL")
    if df.empty:
        return jsonify({"error": "No hay fechas de caducidad registradas."}), 400

    df["fecha_caducidad"] = pd.to_datetime(df["fecha_caducidad"])
    hoy = pd.Timestamp(date.today())
    df["dias_restantes"] = (df["fecha_caducidad"] - hoy).dt.days
    df = df.sort_values("dias_restantes")

    colores = [ROJO if d < 0 else (ROJO_OSCURO if d < 30 else VERDE) for d in df["dias_restantes"]]

    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    barras = ax.barh(df["nombre"], df["dias_restantes"], color=colores)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.bar_label(barras, padding=3, fontsize=9, fmt=lambda v: f"{int(v)} días")
    ax.invert_yaxis()
    ax.set_xlabel("Días restantes para caducar (negativo = ya caducado)")
    ax.set_ylabel("Medicamento")
    fig.suptitle("Vigencia de medicamentos en inventario", fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title("Rojo = caducado, rojo oscuro = caduca en <30 días, verde = vigente", fontsize=9.5, color=GRIS, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    caducados = int((df["dias_restantes"] < 0).sum())
    por_caducar = int(((df["dias_restantes"] >= 0) & (df["dias_restantes"] < 30)).sum())

    return jsonify({
        "imagen_base64": _figura_a_base64(fig),
        "titulo": "Vigencia de medicamentos en inventario",
        "subtitulo": "Días restantes para caducar por medicamento",
        "eje_x": "Días restantes", "eje_y": "Medicamento",
        "conclusion": f"{caducados} medicamento(s) ya caducaron y deben retirarse del inventario; "
                       f"{por_caducar} más caducan en menos de 30 días y deben priorizarse en consumo o reposición.",
        "datos": df[["nombre", "dias_restantes", "stock"]].to_dict(orient="records"),
    })


# ---------------------------------------------------------------------------
# Gráficas específicas por módulo (para mostrar dentro de cada entidad,
# no solo en Reportes y análisis)
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/pacientes-sexo", methods=["GET"])
def grafico_pacientes_sexo():
    df = leer_tabla("""
        SELECT COALESCE(NULLIF(sexo, ''), 'No especificado') AS sexo, COUNT(*) AS total
        FROM pacientes GROUP BY sexo ORDER BY total DESC
    """)
    if df.empty:
        return jsonify({"error": "Aún no hay pacientes registrados."}), 400
    top = df.iloc[0]
    return jsonify(grafico_pastel(
        df["sexo"], df["total"],
        titulo="Pacientes por sexo",
        subtitulo="Distribución de pacientes registrados según sexo",
        conclusion=f"La mayoría de los pacientes registrados son \"{top['sexo']}\" "
                    f"({int(top['total'])} de {int(df['total'].sum())}). Esto ayuda a planear "
                    f"servicios y campañas de salud dirigidas.",
    ))


@reportes_bp.route("/grafico/medicos-especialidad", methods=["GET"])
def grafico_medicos_especialidad():
    df = leer_tabla("""
        SELECT e.nombre AS especialidad, COUNT(*) AS total
        FROM medicos m JOIN especialidades e ON m.especialidad_id = e.id
        GROUP BY e.nombre ORDER BY total DESC
    """)
    if df.empty:
        return jsonify({"error": "Aún no hay médicos con especialidad asignada."}), 400
    top = df.iloc[0]
    return jsonify(grafico_barras(
        df["especialidad"], df["total"],
        titulo="Médicos por especialidad",
        subtitulo="Número de médicos registrados en cada especialidad",
        eje_x="Especialidad", eje_y="Número de médicos",
        conclusion=f"\"{top['especialidad']}\" es la especialidad con más médicos registrados "
                    f"({int(top['total'])}). Especialidades con pocos médicos pueden necesitar "
                    f"contratación adicional si tienen alta demanda de citas.",
        horizontal=True,
    ))


@reportes_bp.route("/grafico/consultorios-uso", methods=["GET"])
def grafico_consultorios_uso():
    df = leer_tabla("""
        SELECT co.numero AS consultorio, COUNT(c.id) AS total
        FROM consultorios co LEFT JOIN citas c ON c.consultorio_id = co.id
        GROUP BY co.id ORDER BY total DESC
    """)
    if df.empty:
        return jsonify({"error": "Aún no hay consultorios registrados."}), 400
    top = df.iloc[0]
    return jsonify(grafico_barras(
        "Consultorio " + df["consultorio"].astype(str), df["total"],
        titulo="Uso de consultorios",
        subtitulo="Número de citas atendidas por consultorio",
        eje_x="Consultorio", eje_y="Número de citas",
        conclusion=f"El consultorio {top['consultorio']} es el más utilizado, con {int(top['total'])} "
                    f"citas registradas. Consultorios con poco uso podrían reasignarse a especialidades "
                    f"con más demanda.",
        horizontal=True,
    ))


@reportes_bp.route("/grafico/pagos-metodo", methods=["GET"])
def grafico_pagos_metodo():
    df = leer_tabla("""
        SELECT COALESCE(NULLIF(metodo_pago, ''), 'No especificado') AS metodo, SUM(monto) AS total
        FROM pagos GROUP BY metodo ORDER BY total DESC
    """)
    if df.empty:
        return jsonify({"error": "Aún no hay pagos registrados."}), 400
    top = df.iloc[0]
    return jsonify(grafico_pastel(
        df["metodo"], df["total"],
        titulo="Ingresos por método de pago",
        subtitulo="Distribución del monto total cobrado según método de pago",
        conclusion=f"\"{top['metodo']}\" concentra la mayor parte de los ingresos, con "
                    f"${top['total']:,.2f} cobrados. Es el canal de pago que conviene mantener "
                    f"siempre disponible y sin fallas.",
    ))


# ---------------------------------------------------------------------------
# Distribución de citas / ocupación (se conservan, con formato enriquecido)
# ---------------------------------------------------------------------------

@reportes_bp.route("/grafico/estado-citas", methods=["GET"])
def grafico_estado_citas():
    df = leer_tabla("SELECT estado, COUNT(*) AS total FROM citas GROUP BY estado")
    canceladas = df.loc[df["estado"] == "cancelada", "total"].sum()
    pct_cancel = round(canceladas / df["total"].sum() * 100, 1)
    return jsonify(grafico_pastel(
        df["estado"], df["total"],
        titulo="Distribución de citas por estado",
        subtitulo="Proporción de citas atendidas, canceladas, confirmadas y pendientes",
        conclusion=f"El {pct_cancel}% de las citas terminan canceladas. Reducir esta tasa (por ejemplo con "
                    f"recordatorios automáticos) mejora directamente la ocupación de los consultorios.",
    ))


@reportes_bp.route("/grafico/ocupacion-hospitalaria", methods=["GET"])
def grafico_ocupacion_hospitalaria():
    df = leer_tabla("SELECT estado, COUNT(*) AS total FROM hospitalizaciones GROUP BY estado")
    hospitalizados = df.loc[df["estado"] == "hospitalizado", "total"].sum()
    return jsonify(grafico_pastel(
        df["estado"], df["total"],
        titulo="Ocupación hospitalaria",
        subtitulo="Pacientes hospitalizados actualmente vs. dados de alta",
        conclusion=f"Actualmente hay {int(hospitalizados)} paciente(s) hospitalizados. Este dato, revisado a diario, "
                    f"permite anticipar la disponibilidad de camas.",
    ))


# ---------------------------------------------------------------------------
# Machine Learning: segmentación de pacientes (clustering)
# ---------------------------------------------------------------------------

@reportes_bp.route("/ml/segmentacion-pacientes", methods=["GET"])
def segmentacion_pacientes():
    df = leer_tabla("""
        SELECT p.id AS paciente_id, p.nombre || ' ' || p.apellido_paterno AS nombre,
               COUNT(DISTINCT co.id) AS num_consultas, COALESCE(SUM(pa.monto), 0) AS gasto_total
        FROM pacientes p
        LEFT JOIN consultas co ON co.paciente_id = p.id
        LEFT JOIN pagos pa ON pa.paciente_id = p.id
        GROUP BY p.id
    """)
    if len(df) < 4:
        return jsonify({"error": "Se necesitan al menos 4 pacientes con datos para segmentar."}), 400

    X = df[["num_consultas", "gasto_total"]].values
    X_esc = StandardScaler().fit_transform(X)
    k = 3 if len(df) >= 6 else 2
    modelo = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster"] = modelo.fit_predict(X_esc)

    fig, ax = plt.subplots(figsize=(6.5, 5))
    colores_cluster = [ROJO, GRIS, "#D9A400"]
    for c in sorted(df["cluster"].unique()):
        sub = df[df["cluster"] == c]
        ax.scatter(sub["num_consultas"], sub["gasto_total"], s=70,
                   color=colores_cluster[c % len(colores_cluster)], label=f"Cluster {c}", edgecolors="white")
    ax.set_xlabel("Número de consultas")
    ax.set_ylabel("Gasto total ($)")
    ax.legend(frameon=False, fontsize=9)
    fig.suptitle("Segmentación de pacientes (K-Means)", fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title("Agrupación por frecuencia de uso y gasto", fontsize=10, color=GRIS, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    resumen = df.groupby("cluster")[["num_consultas", "gasto_total"]].mean().round(1).reset_index()
    cluster_alto = resumen.loc[resumen["gasto_total"].idxmax()]

    return jsonify({
        "imagen_base64": _figura_a_base64(fig),
        "titulo": "Segmentación de pacientes (K-Means)",
        "subtitulo": "Agrupación de pacientes por frecuencia de uso y gasto total",
        "eje_x": "Número de consultas", "eje_y": "Gasto total ($)",
        "conclusion": f"El cluster {int(cluster_alto['cluster'])} agrupa a los pacientes de mayor gasto promedio "
                       f"(${cluster_alto['gasto_total']:.0f}) y {cluster_alto['num_consultas']:.1f} consultas en promedio: "
                       f"son el perfil de paciente frecuente/alto costo al que conviene dar seguimiento cercano.",
        "resumen_por_cluster": resumen.to_dict(orient="records"),
        "pacientes": df.to_dict(orient="records"),
    })


# ---------------------------------------------------------------------------
# Machine Learning: predicción de cancelación de citas (clasificación)
# ---------------------------------------------------------------------------

@reportes_bp.route("/ml/prediccion-cancelacion", methods=["GET"])
def prediccion_cancelacion():
    df = leer_tabla("""
        SELECT c.hora, c.fecha, c.estado, e.nombre AS especialidad
        FROM citas c JOIN medicos m ON c.medico_id = m.id
        JOIN especialidades e ON m.especialidad_id = e.id
        WHERE c.estado IN ('atendida', 'cancelada')
    """)
    if df["estado"].nunique() < 2 or len(df) < 15:
        return jsonify({"error": "No hay suficientes datos con ambas clases (atendida/cancelada) para entrenar el modelo."}), 400

    df["fecha"] = pd.to_datetime(df["fecha"])
    df["dia_semana"] = df["fecha"].dt.dayofweek
    df["hora_num"] = df["hora"].str.slice(0, 2).astype(int)
    df["cancelada"] = (df["estado"] == "cancelada").astype(int)

    le = LabelEncoder()
    df["especialidad_cod"] = le.fit_transform(df["especialidad"])
    X = df[["especialidad_cod", "hora_num", "dia_semana"]]
    y = df["cancelada"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if y.nunique() > 1 else None
    )
    modelo = LogisticRegression(max_iter=1000)
    modelo.fit(X_train, y_train)
    predicciones = modelo.predict(X_test)

    exactitud = round(accuracy_score(y_test, predicciones) * 100, 1)
    reporte = classification_report(y_test, predicciones, output_dict=True, zero_division=0)
    coeficientes = dict(zip(["especialidad", "hora", "dia_semana"], modelo.coef_[0].round(3).tolist()))
    variable_influyente = max(coeficientes, key=lambda k: abs(coeficientes[k]))

    return jsonify({
        "modelo": "Regresión logística",
        "titulo": "Predicción de cancelación de citas",
        "subtitulo": "Clasificación supervisada según especialidad, hora y día de la semana",
        "muestras_entrenamiento": len(X_train),
        "muestras_prueba": len(X_test),
        "exactitud_pct": exactitud,
        "reporte_clasificacion": reporte,
        "influencia_variables": coeficientes,
        "conclusion": f"El modelo alcanza {exactitud}% de exactitud sobre datos de prueba. La variable con mayor "
                       f"influencia sobre la cancelación es \"{variable_influyente}\". Con datos históricos reales "
                       f"del hospital (en vez de datos sintéticos) la exactitud mejoraría al reflejar patrones reales de cancelación.",
    })
