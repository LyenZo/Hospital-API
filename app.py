import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import db
from crud import register_crud
from analytics import reportes_bp
from models import (
    Especialidad, Consultorio, Medicamento,
    Paciente, Medico, Cita, Consulta,
    Diagnostico, EstudioClinico, Tratamiento,
    Hospitalizacion, Pago,
)


def create_app():
    app_instance = Flask(__name__)
    app_instance.config.from_object(Config)

    CORS(app_instance) 
    db.init_app(app_instance)

    entidades = [
        (Especialidad, "especialidades"),
        (Consultorio, "consultorios"),
        (Medicamento, "medicamentos"),
        (Paciente, "pacientes"),
        (Medico, "medicos"),
        (Cita, "citas"),
        (Consulta, "consultas"),
        (Diagnostico, "diagnosticos"),
        (EstudioClinico, "estudios-clinicos"),
        (Tratamiento, "tratamientos"),
        (Hospitalizacion, "hospitalizaciones"),
        (Pago, "pagos"),
    ]
    for modelo, nombre in entidades:
        register_crud(app_instance, modelo, nombre)

    app_instance.register_blueprint(reportes_bp)  

    @app_instance.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "servicio": "SIG-Hospital API"})

    @app_instance.route("/api/modulos", methods=["GET"])
    def modulos():

        return jsonify([nombre for _, nombre in entidades])

    with app_instance.app_context():
        db.create_all()

    return app_instance


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)