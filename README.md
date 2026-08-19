# Sistema Integral de Gestión y Análisis Hospitalario (SIG-Hospital) - Backend (API)

## Información del Proyecto
* **Institución:** Universidad Tecnológica del Valle de Toluca (UTVT)
* **Equipo de Desarrollo:**
  * Marcos Jesús Ugalde Zarza
* **Fecha de Entrega:** 18 de agosto de 2026

---

## Descripción General
El presente repositorio contiene el código fuente correspondiente al backend del sistema SIG-Hospital. Este componente provee la lógica de negocio, la gestión de almacenamiento de información y el procesamiento analítico requerido por la institución médica para la toma de decisiones. 

El desarrollo se fundamenta en el framework Flask (Python) y expone una arquitectura de Interfaz de Programación de Aplicaciones (API) RESTful. Adicionalmente, integra módulos de extracción de conocimiento y análisis de datos.

## Tecnologías Implementadas
* **Lenguaje:** Python 3.11+
* **Framework Web:** Flask
* **ORM y Base de Datos:** Flask-SQLAlchemy (SQLite)
* **Análisis de Datos:** Pandas y NumPy
* **Visualización Interna:** Matplotlib
* **Machine Learning:** Scikit-learn
* **Servidor de Producción:** Gunicorn
* **Seguridad:** Flask-CORS

## Módulos del Sistema
La API gestiona la información de 8 módulos obligatorios estructurados mediante operaciones CRUD:
1. Pacientes
2. Médicos (incluyendo especialidades)
3. Citas
4. Consultas
5. Diagnósticos
6. Tratamientos (control de medicamentos)
7. Hospitalización
8. Reportes y Análisis (estadísticas y modelos predictivos)

## Instrucciones de Instalación y Ejecución Local

1. Clonar el repositorio.
2. Crear y activar un entorno virtual de Python:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En sistemas Unix/MacOS
   venv\Scripts\activate     # En sistemas Windows
   python app.py
   python seed.py
   python app.py
