from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
import os
import face_recognition
from flask import send_from_directory


app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 4306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'tebusco'

mysql = MySQL(app)


def cargar_imagenes_registradas():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT ruta_imagen FROM personas_desaparecidas")
    registros = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]
    cursor.close()
    registros_dict = [dict(zip(column_names, registro)) for registro in registros]
    rutas_imagenes = [registro['ruta_imagen'] for registro in registros_dict]
    return rutas_imagenes

def analizar_imagen(imagen_analizar, rutas_registradas):
    imagen_analizar_encodings = face_recognition.face_encodings(face_recognition.load_image_file(imagen_analizar))

    for ruta_registrada in rutas_registradas:
        imagen_registrada_encodings = face_recognition.face_encodings(face_recognition.load_image_file(ruta_registrada))

        # Comparar las codificaciones faciales
        resultados = face_recognition.compare_faces(imagen_registrada_encodings, imagen_analizar_encodings[0])

        # Si hay una coincidencia, devuelve True
        if True in resultados:
            return True

    # Si no hay coincidencias
    return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analizar', methods=['POST'])
def analizar():
    if request.method == 'POST':
        imagen_analizar = request.files['archivo']
        rutas_registradas = cargar_imagenes_registradas()
        ruta_imagen = None

        for ruta_registrada in rutas_registradas:
            imagen_registrada_encodings = face_recognition.face_encodings(face_recognition.load_image_file(ruta_registrada))
            imagen_analizar_encodings = face_recognition.face_encodings(face_recognition.load_image_file(imagen_analizar))

            resultados = face_recognition.compare_faces(imagen_registrada_encodings, imagen_analizar_encodings[0])

            if True in resultados:
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT * FROM personas_desaparecidas WHERE ruta_imagen = %s", (ruta_registrada,))
                column_names = [column[0] for column in cursor.description]
                datos_registrados = dict(zip(column_names, cursor.fetchone()))
                cursor.close()

                mensaje_resultado = f"¡Coincidencia encontrada! Datos asociados a la imagen:\n" \
                                    f"Nombre: {datos_registrados['nombre']}\n" \
                                    f"Apellido: {datos_registrados['apellido']}\n" \
                                    f"Fecha de Desaparición: {datos_registrados['fecha_desaparicion']}\n" \
                                    f"Estado: {datos_registrados['estado']}\n" \
                                    f"Teléfono de Contacto: {datos_registrados['telefono_contacto']}"
                ruta_imagen = datos_registrados['ruta_imagen']
                mensaje_resultado += f"\nImagen: <img src='{url_for('display_image', filename=ruta_imagen)}' alt='Imagen Registrada'>"

                return render_template('analizar.html', mensaje_resultado=mensaje_resultado)
                return render_template('analizar.html', mensaje_resultado=datos_registrados)

        mensaje_resultado = "No se encontraron coincidencias."
        return render_template('analizar.html', mensaje_resultado=mensaje_resultado)

    return redirect(url_for('index'))


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        imagen = request.files['archivo']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        fecha_desaparicion = request.form['fecha_desaparicion']
        estado = request.form['estado']
        telefono_contacto = request.form['telefono_contacto']

        directorio_uploads = 'static/uploads/'
        if not os.path.exists(directorio_uploads):
            os.makedirs(directorio_uploads)

        ruta_imagen = os.path.join(directorio_uploads, imagen.filename)
        imagen.save(ruta_imagen)

        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO personas_desaparecidas (ruta_imagen, nombre, apellido, fecha_desaparicion, estado, telefono_contacto)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (ruta_imagen, nombre, apellido, fecha_desaparicion, estado, telefono_contacto))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('index'))

    return render_template('registrar.html')

@app.route('/visualizar')
def visualizar_registros():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM personas_desaparecidas")
    column_names = [column[0] for column in cursor.description]
    registros = [dict(zip(column_names, row)) for row in cursor.fetchall()]
    cursor.close()

    return render_template('visualizar.html', registros=registros)


@app.route('/<filename>')
def display_image(filename):
    return send_from_directory('/', filename)


if __name__ == '__main__':
    app.run(debug=True)
