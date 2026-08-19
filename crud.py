from datetime import datetime, date, time as time_cls

from flask import Blueprint, request, jsonify
from extensions import db


def _convertir_valor(valor, tipo_python):
    if valor in (None, ""):
        return None
    if not isinstance(valor, str):
        return valor

    if tipo_python is datetime:
        texto = valor.replace("Z", "")
        try:
            return datetime.fromisoformat(texto)
        except ValueError:
            return datetime.strptime(texto, "%Y-%m-%dT%H:%M")
    if tipo_python is date:
        return date.fromisoformat(valor[:10])
    if tipo_python is time_cls:
        return time_cls.fromisoformat(valor)
    return valor


def register_crud(app, model, name):

    bp = Blueprint(name, __name__, url_prefix=f"/api/{name}")
    columnas_validas = {c.name for c in model.__table__.columns if c.name != "id"}
    tipos_columna = {
        c.name: c.type.python_type
        for c in model.__table__.columns
        if c.name in columnas_validas and hasattr(c.type, "python_type")
        and c.type.python_type in (date, datetime, time_cls)
    }

    def _preparar_campos(data):
        campos = {}
        for k, v in data.items():
            if k not in columnas_validas:
                continue
            if v == "":
                v = None
            elif k in tipos_columna:
                v = _convertir_valor(v, tipos_columna[k])
            campos[k] = v
        return campos

    @bp.route("", methods=["GET"])
    def listar():
        try:
            registros = model.query.all()
            return jsonify([r.to_dict() for r in registros])
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @bp.route("/<int:id>", methods=["GET"])
    def obtener(id):
        try:
            registro = model.query.get(id)
            if registro is None:
                return jsonify({"error": f"{name} con id {id} no encontrado"}), 404
            return jsonify(registro.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @bp.route("", methods=["POST"])
    def crear():
        data = request.get_json(silent=True) or {}
        try:
            campos = _preparar_campos(data)
            registro = model(**campos)
            db.session.add(registro)
            db.session.commit()
            return jsonify(registro.to_dict()), 201
        except (ValueError, TypeError) as e:
            db.session.rollback()
            return jsonify({"error": f"Dato inválido: {e}"}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400

    @bp.route("/<int:id>", methods=["PUT"])
    def actualizar(id):
        registro = model.query.get(id)
        if registro is None:
            return jsonify({"error": f"{name} con id {id} no encontrado"}), 404
        data = request.get_json(silent=True) or {}
        try:
            campos = _preparar_campos(data)
            for k, v in campos.items():
                setattr(registro, k, v)
            db.session.commit()
            return jsonify(registro.to_dict())
        except (ValueError, TypeError) as e:
            db.session.rollback()
            return jsonify({"error": f"Dato inválido: {e}"}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400

    @bp.route("/_schema", methods=["GET"])
    def esquema():
        campos = []
        for c in model.__table__.columns:
            if c.name == "id":
                continue
            campos.append({
                "nombre": c.name,
                "tipo": str(c.type),
                "requerido": not c.nullable,
                "es_llave_foranea": bool(c.foreign_keys),
            })
        return jsonify({"entidad": name, "campos": campos})

    @bp.route("/<int:id>", methods=["DELETE"])
    def eliminar(id):
        registro = model.query.get(id)
        if registro is None:
            return jsonify({"error": f"{name} con id {id} no encontrado"}), 404
        db.session.delete(registro)
        db.session.commit()
        return jsonify({"mensaje": f"{name} {id} eliminado"}), 200

    app.register_blueprint(bp)