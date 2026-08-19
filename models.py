from datetime import datetime, date
from extensions import db


class SerializableMixin:
    """Convierte cualquier modelo a dict automáticamente a partir de sus columnas.
    Esto es lo que permite que el CRUD genérico funcione igual para las 12 entidades
    sin tener que escribir un serializador por cada una."""

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            result[column.name] = value
        return result


# ---------------------------------------------------------------------------
# Catálogos de apoyo
# ---------------------------------------------------------------------------

class Especialidad(db.Model, SerializableMixin):
    __tablename__ = "especialidades"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255))

    medicos = db.relationship("Medico", backref="especialidad", lazy=True)
    consultorios = db.relationship("Consultorio", backref="especialidad", lazy=True)


class Consultorio(db.Model, SerializableMixin):
    __tablename__ = "consultorios"
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), nullable=False)
    piso = db.Column(db.String(20))
    especialidad_id = db.Column(db.Integer, db.ForeignKey("especialidades.id"))

    citas = db.relationship("Cita", backref="consultorio", lazy=True)


class Medicamento(db.Model, SerializableMixin):
    __tablename__ = "medicamentos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    presentacion = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)
    precio_unitario = db.Column(db.Float, default=0.0)
    fecha_caducidad = db.Column(db.Date)

    tratamientos = db.relationship("Tratamiento", backref="medicamento", lazy=True)


# ---------------------------------------------------------------------------
# Módulo 1: Pacientes
# ---------------------------------------------------------------------------

class Paciente(db.Model, SerializableMixin):
    __tablename__ = "pacientes"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    fecha_nacimiento = db.Column(db.Date)
    sexo = db.Column(db.String(20))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(150))
    direccion = db.Column(db.String(255))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    citas = db.relationship("Cita", backref="paciente", lazy=True)
    consultas = db.relationship("Consulta", backref="paciente", lazy=True)
    estudios_clinicos = db.relationship("EstudioClinico", backref="paciente", lazy=True)
    hospitalizaciones = db.relationship("Hospitalizacion", backref="paciente", lazy=True)
    pagos = db.relationship("Pago", backref="paciente", lazy=True)


# ---------------------------------------------------------------------------
# Módulo 2: Médicos
# ---------------------------------------------------------------------------

class Medico(db.Model, SerializableMixin):
    __tablename__ = "medicos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    cedula_profesional = db.Column(db.String(50))
    especialidad_id = db.Column(db.Integer, db.ForeignKey("especialidades.id"))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(150))

    citas = db.relationship("Cita", backref="medico", lazy=True)
    consultas = db.relationship("Consulta", backref="medico", lazy=True)
    hospitalizaciones = db.relationship("Hospitalizacion", backref="medico", lazy=True)


# ---------------------------------------------------------------------------
# Módulo 3: Citas
# ---------------------------------------------------------------------------

class Cita(db.Model, SerializableMixin):
    __tablename__ = "citas"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=False)
    consultorio_id = db.Column(db.Integer, db.ForeignKey("consultorios.id"))
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(30), default="pendiente")  # pendiente, confirmada, cancelada, atendida
    tipo_atencion = db.Column(db.String(30), default="Consulta")  # Consulta, Urgencia, Seguimiento
    motivo = db.Column(db.String(255))

    consulta = db.relationship("Consulta", backref="cita", uselist=False, lazy=True)


# ---------------------------------------------------------------------------
# Módulo 4: Consultas
# ---------------------------------------------------------------------------

class Consulta(db.Model, SerializableMixin):
    __tablename__ = "consultas"
    id = db.Column(db.Integer, primary_key=True)
    cita_id = db.Column(db.Integer, db.ForeignKey("citas.id"))
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    motivo_consulta = db.Column(db.String(255))
    notas = db.Column(db.Text)
    peso = db.Column(db.Float)
    talla = db.Column(db.Float)
    presion_arterial = db.Column(db.String(20))
    temperatura = db.Column(db.Float)

    diagnosticos = db.relationship("Diagnostico", backref="consulta", lazy=True)
    tratamientos = db.relationship("Tratamiento", backref="consulta", lazy=True)


# ---------------------------------------------------------------------------
# Módulo 5: Diagnósticos
# ---------------------------------------------------------------------------

class Diagnostico(db.Model, SerializableMixin):
    __tablename__ = "diagnosticos"
    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey("consultas.id"), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    codigo_cie10 = db.Column(db.String(20))
    fecha = db.Column(db.Date, default=date.today)


class EstudioClinico(db.Model, SerializableMixin):
    __tablename__ = "estudios_clinicos"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    resultado = db.Column(db.Text)
    fecha = db.Column(db.Date, default=date.today)


# ---------------------------------------------------------------------------
# Módulo 6: Tratamientos
# ---------------------------------------------------------------------------

class Tratamiento(db.Model, SerializableMixin):
    __tablename__ = "tratamientos"
    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey("consultas.id"), nullable=False)
    medicamento_id = db.Column(db.Integer, db.ForeignKey("medicamentos.id"), nullable=False)
    dosis = db.Column(db.String(100))
    frecuencia = db.Column(db.String(100))
    duracion_dias = db.Column(db.Integer)
    indicaciones = db.Column(db.String(255))


# ---------------------------------------------------------------------------
# Módulo 7: Hospitalización
# ---------------------------------------------------------------------------

class Hospitalizacion(db.Model, SerializableMixin):
    __tablename__ = "hospitalizaciones"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=False)
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_alta = db.Column(db.DateTime)
    habitacion = db.Column(db.String(20))
    motivo = db.Column(db.String(255))
    estado = db.Column(db.String(30), default="hospitalizado")  # hospitalizado, alta


# ---------------------------------------------------------------------------
# Módulo 8 (soporte): Pagos — insumo para el módulo de Reportes y análisis
# ---------------------------------------------------------------------------

class Pago(db.Model, SerializableMixin):
    __tablename__ = "pagos"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    concepto = db.Column(db.String(100))  # consulta, hospitalizacion, estudio, etc.
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_pago = db.Column(db.String(50))
