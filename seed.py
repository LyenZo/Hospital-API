"""Poblar la base con datos de ejemplo en volumen suficiente para que los
reportes y modelos de análisis (clustering, clasificación) tengan sentido.
Uso: python seed.py
"""
import random
from datetime import date, datetime, timedelta

from app import create_app
from extensions import db
from models import (
    Especialidad, Consultorio, Medicamento,
    Paciente, Medico, Cita, Consulta,
    Diagnostico, EstudioClinico, Tratamiento,
    Hospitalizacion, Pago,
)

random.seed(42)
app = create_app()

NOMBRES = ["Marcos", "Sofía", "Diego", "Elena", "Carlos", "Ana", "Luis", "María",
           "Jorge", "Paola", "Ricardo", "Fernanda", "Iván", "Daniela", "Raúl",
           "Valeria", "Héctor", "Camila", "Óscar", "Renata"]
APELLIDOS = ["Ramírez", "Pérez", "Martínez", "Vargas", "Hernández", "Torres",
             "López", "González", "Flores", "Cruz", "Morales", "Reyes"]

DIAGNOSTICOS_CATALOGO = [
    ("Migraña tensional", "G44.2"),
    ("Infección de vías respiratorias", "J06.9"),
    ("Gastritis aguda", "K29.7"),
    ("Hipertensión arterial", "I10"),
    ("Diabetes mellitus tipo 2", "E11"),
    ("Lumbalgia", "M54.5"),
    ("Faringoamigdalitis", "J03.9"),
    ("Ansiedad generalizada", "F41.1"),
    ("Fractura de muñeca", "S62.0"),
    ("Dermatitis de contacto", "L23.9"),
]

TIPOS_ESTUDIO = ["Examen de sangre", "Examen de orina",
                  "Coproparasitoscópico (heces fecales)", "Radiografía",
                  "Electrocardiograma", "Ultrasonido"]

MOTIVOS_HOSPITALIZACION = ["Observación cardiológica", "Cirugía programada",
                            "Neumonía", "Postoperatorio", "Control de diabetes",
                            "Fractura mayor"]

HORAS_DISPONIBLES = ["08:00", "09:00", "09:30", "10:00", "10:30", "11:00",
                      "11:30", "12:00", "12:30", "16:00", "16:30", "17:00"]


def nombre_completo():
    return (random.choice(NOMBRES), random.choice(APELLIDOS), random.choice(APELLIDOS))


with app.app_context():
    db.drop_all()
    db.create_all()

    # --- Catálogos -----------------------------------------------------
    especialidades = [
        Especialidad(nombre="Medicina General", descripcion="Consulta general"),
        Especialidad(nombre="Pediatría", descripcion="Atención a menores"),
        Especialidad(nombre="Cardiología", descripcion="Enfermedades del corazón"),
        Especialidad(nombre="Traumatología", descripcion="Huesos y articulaciones"),
    ]
    db.session.add_all(especialidades)
    db.session.commit()

    consultorios = [
        Consultorio(numero="101", piso="1", especialidad_id=especialidades[0].id),
        Consultorio(numero="102", piso="1", especialidad_id=especialidades[1].id),
        Consultorio(numero="201", piso="2", especialidad_id=especialidades[2].id),
        Consultorio(numero="202", piso="2", especialidad_id=especialidades[3].id),
    ]
    db.session.add_all(consultorios)

    nombres_medicamentos = [
        ("Paracetamol 500mg", "Caja 20 tabletas", 45.0),
        ("Amoxicilina 500mg", "Caja 12 cápsulas", 90.0),
        ("Ibuprofeno 400mg", "Caja 30 tabletas", 60.0),
        ("Losartán 50mg", "Caja 30 tabletas", 110.0),
        ("Metformina 850mg", "Caja 30 tabletas", 95.0),
        ("Omeprazol 20mg", "Caja 14 cápsulas", 75.0),
        ("Loratadina 10mg", "Caja 10 tabletas", 55.0),
        ("Ácido acetilsalicílico 500mg", "Caja 20 tabletas", 40.0),
    ]
    medicamentos = []
    for i, (nombre, presentacion, precio) in enumerate(nombres_medicamentos):
        # Mezcla de vigencias: algunos ya caducados, varios por caducar pronto, el resto con vigencia larga
        if i < 2:
            caducidad = date.today() - timedelta(days=random.randint(1, 20))
        elif i < 4:
            caducidad = date.today() + timedelta(days=random.randint(5, 25))
        else:
            caducidad = date.today() + timedelta(days=random.randint(60, 500))
        medicamentos.append(Medicamento(
            nombre=nombre, presentacion=presentacion,
            stock=random.randint(20, 220), precio_unitario=precio,
            fecha_caducidad=caducidad,
        ))
    db.session.add_all(medicamentos)

    medicos = []
    for i in range(6):
        esp = especialidades[i % len(especialidades)]
        n, ap, am = nombre_completo()
        medicos.append(Medico(
            nombre=n, apellido_paterno=ap, apellido_materno=am,
            cedula_profesional=str(1000000 + i), especialidad_id=esp.id,
            telefono=f"722{1000000+i}", email=f"medico{i}@hospital.mx",
        ))
    db.session.add_all(medicos)

    pacientes = []
    for i in range(20):
        n, ap, am = nombre_completo()
        edad = random.randint(3, 85)
        nacimiento = date.today() - timedelta(days=edad * 365 + random.randint(0, 364))
        pacientes.append(Paciente(
            nombre=n, apellido_paterno=ap, apellido_materno=am,
            fecha_nacimiento=nacimiento, sexo=random.choice(["M", "F"]),
            telefono=f"722{2000000+i}", email=f"paciente{i}@example.com",
            direccion=random.choice(["Lerma", "Toluca", "Metepec", "Zinacantepec"]) + ", Edo. Méx.",
        ))
    db.session.add_all(pacientes)
    db.session.commit()

    # --- Citas (con estados, tipo de atención y patrón día/hora reales para el heatmap) ---
    estados_pool = (["atendida"] * 5 + ["confirmada"] * 2 + ["pendiente"] * 2 + ["cancelada"] * 2)
    tipos_atencion_pool = (["Consulta"] * 6 + ["Urgencia"] * 3 + ["Seguimiento"] * 2)
    # Lunes y martes en la mañana son los más saturados; fin de semana casi vacío (patrón intencional para el heatmap)
    dias_semana_pool = ([0] * 6 + [1] * 5 + [2] * 3 + [3] * 3 + [4] * 3 + [5] * 1)  # 0=lunes ... 6=domingo
    horas_pool = (["08:00"] * 4 + ["09:00"] * 4 + ["09:30"] * 3 + ["10:00"] * 3 +
                  ["10:30"] * 2 + ["11:00"] * 2 + ["11:30"] * 2 + ["12:00"] * 2 +
                  ["12:30"] * 1 + ["16:00"] * 1 + ["16:30"] * 1 + ["17:00"] * 1)

    citas = []
    for i in range(120):
        paciente = random.choice(pacientes)
        medico = random.choice(medicos)
        consultorio = next(c for c in consultorios if c.especialidad_id == medico.especialidad_id)

        semana_offset = random.randint(-8, 1)  # hasta 8 semanas atrás, 1 semana adelante
        dia_objetivo = random.choice(dias_semana_pool)
        base = date.today() + timedelta(weeks=semana_offset)
        fecha = base - timedelta(days=base.weekday()) + timedelta(days=dia_objetivo)

        estado = random.choice(estados_pool)
        if fecha > date.today():
            estado = random.choice(["confirmada", "pendiente", "cancelada"])

        cita = Cita(
            paciente_id=paciente.id, medico_id=medico.id, consultorio_id=consultorio.id,
            fecha=fecha, hora=random.choice(horas_pool),
            estado=estado, tipo_atencion=random.choice(tipos_atencion_pool),
            motivo=random.choice(["Dolor de cabeza", "Chequeo general", "Dolor en el pecho",
                                   "Fiebre", "Dolor de espalda", "Control de rutina",
                                   "Dolor abdominal", "Revisión de resultados"]),
        )
        citas.append(cita)
    db.session.add_all(citas)
    db.session.commit()

    # --- Consultas, diagnósticos, tratamientos, estudios (solo citas atendidas) ---
    for cita in citas:
        if cita.estado != "atendida":
            continue
        consulta = Consulta(
            cita_id=cita.id, paciente_id=cita.paciente_id, medico_id=cita.medico_id,
            fecha=datetime.combine(cita.fecha, datetime.min.time()),
            motivo_consulta=cita.motivo,
            notas="Evolución favorable, se indica tratamiento.",
            peso=round(random.uniform(15, 95), 1),
            talla=round(random.uniform(0.9, 1.9), 2),
            presion_arterial=f"{random.randint(100,140)}/{random.randint(60,90)}",
            temperatura=round(random.uniform(36.0, 38.5), 1),
        )
        db.session.add(consulta)
        db.session.commit()

        desc, cie10 = random.choice(DIAGNOSTICOS_CATALOGO)
        db.session.add(Diagnostico(consulta_id=consulta.id, descripcion=desc, codigo_cie10=cie10))

        if random.random() < 0.45:
            db.session.add(EstudioClinico(
                paciente_id=cita.paciente_id,
                tipo=random.choice(TIPOS_ESTUDIO),
                resultado="Resultado dentro de parámetros esperados" if random.random() < 0.7 else "Resultado con hallazgos, requiere seguimiento",
            ))

        for _ in range(random.randint(0, 2)):
            med = random.choice(medicamentos)
            db.session.add(Tratamiento(
                consulta_id=consulta.id, medicamento_id=med.id,
                dosis="1 tableta", frecuencia=random.choice(["Cada 8 horas", "Cada 12 horas", "Cada 24 horas"]),
                duracion_dias=random.choice([3, 5, 7, 10]),
                indicaciones="Tomar con alimentos",
            ))

        db.session.add(Pago(
            paciente_id=cita.paciente_id, concepto="consulta",
            monto=round(random.uniform(250, 600), 2),
            fecha=datetime.combine(cita.fecha, datetime.min.time()),
            metodo_pago=random.choice(["tarjeta", "efectivo", "transferencia"]),
        ))

    # --- Hospitalizaciones --------------------------------------------
    for _ in range(12):
        paciente = random.choice(pacientes)
        medico = random.choice(medicos)
        ingreso = datetime.now() - timedelta(days=random.randint(1, 45))
        con_alta = random.random() < 0.7
        alta = ingreso + timedelta(days=random.randint(1, 8)) if con_alta else None
        hosp = Hospitalizacion(
            paciente_id=paciente.id, medico_id=medico.id,
            fecha_ingreso=ingreso, fecha_alta=alta,
            habitacion=str(random.randint(101, 320)),
            motivo=random.choice(MOTIVOS_HOSPITALIZACION),
            estado="alta" if con_alta else "hospitalizado",
        )
        db.session.add(hosp)
        db.session.commit()
        if con_alta:
            db.session.add(Pago(
                paciente_id=paciente.id, concepto="hospitalizacion",
                monto=round(random.uniform(1500, 9000), 2),
                fecha=alta, metodo_pago=random.choice(["tarjeta", "efectivo", "transferencia"]),
            ))

    db.session.commit()
    print("Base de datos poblada: "
          f"{len(pacientes)} pacientes, {len(medicos)} médicos, {len(citas)} citas.")
