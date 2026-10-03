from flask import Flask, render_template, request, session, redirect, url_for, send_file
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

from openpyxl import Workbook
import io


app = Flask(__name__)


# =========================================================
# CONFIGURACIÓN DE SESIÓN
# =========================================================

app.secret_key = "rentec_clave_segura"

# La sesión permanecerá activa durante 7 días
app.permanent_session_lifetime = timedelta(days=7)


# =========================================================
# CONFIGURACIÓN MYSQL
# =========================================================

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "rentec"

mysql = MySQL(app)


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/")
def inicio():

    return render_template(
        "index.html",
        nombre=session.get("nombre"),
        rol=session.get("rol")
    )


# =========================================================
# CATÁLOGO
# =========================================================

@app.route("/computadores")
def computadores():

    return render_template("computadores.html")


@app.route("/tecladosmaus")
def tecladosmaus():

    return render_template("tecladosmaus.html")


@app.route("/televisores")
def televisores():

    return render_template("televisores.html")


@app.route("/torresdepc")
def torresdepc():

    return render_template("torresdepc.html")


# =========================================================
# NOSOTROS
# =========================================================

@app.route("/nosotros")
def nosotros():

    return render_template("quienesomos.html")


@app.route("/mision")
def mision():

    return render_template("misionyvision.html")


# =========================================================
# LOGIN Y REGISTRO
# =========================================================

@app.route("/login-registro")
def login_registro():

    return render_template("Login-Registro.html")


# =========================================================
# REGISTRO
# =========================================================

@app.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "POST":

        # -------------------------------------------------
        # DATOS DEL FORMULARIO
        # -------------------------------------------------

        nombre = request.form["nombre"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        usuario = request.form["usuario"]
        password = request.form["password"]

        # -------------------------------------------------
        # ENCRIPTAR CONTRASEÑA
        # -------------------------------------------------

        password_hash = generate_password_hash(password)

        cursor = mysql.connection.cursor()


        # -------------------------------------------------
        # COMPROBAR USUARIO
        # -------------------------------------------------

        cursor.execute(
            "SELECT id FROM usuarios WHERE usuario = %s",
            (usuario,)
        )

        existe = cursor.fetchone()

        if existe:

            cursor.close()

            return """
            <script>
                alert("El nombre de usuario ya existe");
                window.location.href="/registro";
            </script>
            """


        # -------------------------------------------------
        # COMPROBAR CORREO
        # -------------------------------------------------

        cursor.execute(
            "SELECT id FROM usuarios WHERE correo = %s",
            (correo,)
        )

        correo_existe = cursor.fetchone()

        if correo_existe:

            cursor.close()

            return """
            <script>
                alert("El correo electrónico ya está registrado");
                window.location.href="/registro";
            </script>
            """


        # -------------------------------------------------
        # INSERTAR USUARIO
        # -------------------------------------------------
        #
        # ID DE ROLES:
        #
        # 1 = Administrador
        # 2 = Cliente
        #
        # Los usuarios que se registren normalmente
        # serán clientes.
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO usuarios
            (
                nombre_completo,
                correo,
                telefono,
                usuario,
                contrasena,
                id_rol
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            nombre,
            correo,
            telefono,
            usuario,
            password_hash,
            2
        ))

        mysql.connection.commit()

        cursor.close()

        return render_template("registro_exitoso.html")


    return render_template("Registro.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]


        # -------------------------------------------------
        # BUSCAR USUARIO
        # -------------------------------------------------

        cursor = mysql.connection.cursor()

        # Obtenemos el nombre del rol mediante JOIN
        cursor.execute("""
            SELECT
                usuarios.id,
                usuarios.nombre_completo,
                usuarios.contrasena,
                roles.rol
            FROM usuarios
            INNER JOIN roles
                ON usuarios.id_rol = roles.id_rol
            WHERE usuarios.usuario = %s
        """, (usuario,))

        usuario_db = cursor.fetchone()

        cursor.close()


        # -------------------------------------------------
        # USUARIO NO EXISTE
        # -------------------------------------------------

        if usuario_db is None:

            return """
            <script>
                alert("El usuario no existe");
                window.location.href="/login";
            </script>
            """


        # -------------------------------------------------
        # OBTENER DATOS
        # -------------------------------------------------

        id_usuario = usuario_db[0]
        nombre = usuario_db[1]
        password_hash = usuario_db[2]
        rol = usuario_db[3]


        # -------------------------------------------------
        # COMPROBAR CONTRASEÑA
        # -------------------------------------------------

        if not check_password_hash(password_hash, password):

            return """
            <script>
                alert("Contraseña incorrecta");
                window.location.href="/login";
            </script>
            """


        # -------------------------------------------------
        # CREAR SESIÓN
        # -------------------------------------------------

        session.permanent = True

        session["id_usuario"] = id_usuario
        session["nombre"] = nombre
        session["rol"] = rol


        # -------------------------------------------------
        # MOSTRAR MENSAJE
        # -------------------------------------------------

        return redirect(url_for("inicio_exitoso"))


    return render_template("Login.html")


# =========================================================
# MENSAJE DE LOGIN EXITOSO
# =========================================================

@app.route("/inicio_exitoso")
def inicio_exitoso():

    # Si no hay sesión, no puede entrar
    if "id_usuario" not in session:

        return redirect(url_for("login"))


    return render_template(
        "login_exitoso.html"
    )


# =========================================================
# INICIO DEL USUARIO
# =========================================================

@app.route("/inicio_usuario")
def inicio_usuario():

    # Verificar que haya iniciado sesión
    if "id_usuario" not in session:

        return redirect(url_for("login"))


    return render_template(
        "inicio_usuario.html",
        nombre=session["nombre"],
        rol=session.get("rol")
    )


# =========================================================
# PANEL DE ADMINISTRADOR
# =========================================================

@app.route("/administrador")
def administrador():

    # Verificar sesión
    if "id_usuario" not in session:

        return redirect(url_for("login"))


    # Verificar administrador
    if session.get("rol") != "Administrador":

        return redirect(url_for("inicio_usuario"))


    return render_template(
        "administrador.html",
        nombre=session["nombre"]
    )


# =========================================================
# GESTIÓN DE USUARIOS
# =========================================================

@app.route("/administrador/usuarios", methods=["GET", "POST"])
def gestionar_usuarios():

    # Verificar sesión
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    # Solo administrador
    if session.get("rol") != "Administrador":
        return redirect(url_for("inicio_usuario"))

    cursor = mysql.connection.cursor()

    # =====================================================
    # MODIFICAR USUARIO
    # =====================================================

    if request.method == "POST":

        id_usuario = request.form["id_usuario"]
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        usuario = request.form["usuario"]
        id_rol = request.form["id_rol"]

        cursor.execute("""
            UPDATE usuarios
            SET
                nombre_completo = %s,
                correo = %s,
                telefono = %s,
                usuario = %s,
                id_rol = %s
            WHERE id = %s
        """, (
            nombre,
            correo,
            telefono,
            usuario,
            id_rol,
            id_usuario
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("gestionar_usuarios"))

    # =====================================================
    # OBTENER USUARIOS
    # =====================================================

    cursor.execute("""
        SELECT
            usuarios.id,
            usuarios.nombre_completo,
            usuarios.correo,
            usuarios.telefono,
            usuarios.usuario,
            usuarios.id_rol,
            roles.rol
        FROM usuarios
        INNER JOIN roles
            ON usuarios.id_rol = roles.id_rol
        ORDER BY usuarios.id
    """)

    usuarios_db = cursor.fetchall()

    # =====================================================
    # OBTENER ROLES
    # =====================================================

    cursor.execute("""
        SELECT
            id_rol,
            rol
        FROM roles
        ORDER BY id_rol
    """)

    roles_db = cursor.fetchall()

    # =====================================================
    # USUARIO A EDITAR
    # =====================================================

    id_editar = request.args.get("editar")
    usuario_editar = None

    if id_editar:

        cursor.execute("""
            SELECT
                usuarios.id,
                usuarios.nombre_completo,
                usuarios.correo,
                usuarios.telefono,
                usuarios.usuario,
                usuarios.id_rol,
                roles.rol
            FROM usuarios
            INNER JOIN roles
                ON usuarios.id_rol = roles.id_rol
            WHERE usuarios.id = %s
        """, (id_editar,))

        usuario_editar = cursor.fetchone()

    cursor.close()

    # =====================================================
    # MOSTRAR PÁGINA
    # =====================================================

    return render_template(
        "gestionar_usuarios.html",
        usuarios=usuarios_db,
        roles=roles_db,
        usuario_editar=usuario_editar
    )


# =========================================================
# CREAR USUARIO
# =========================================================

@app.route(
    "/administrador/usuarios/crear",
    methods=["GET", "POST"]
)
def crear_usuario():

    # Verificar sesión
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    # Solo administrador
    if session.get("rol") != "Administrador":
        return redirect(url_for("inicio_usuario"))

    # Crear usuario
    if request.method == "POST":

        nombre = request.form["nombre"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        usuario = request.form["usuario"]
        password = request.form["password"]
        id_rol = request.form["id_rol"]

        password_hash = generate_password_hash(password)

        cursor = mysql.connection.cursor()

        # Comprobar usuario
        cursor.execute(
            "SELECT id FROM usuarios WHERE usuario = %s",
            (usuario,)
        )

        if cursor.fetchone():

            cursor.close()

            return """
            <script>
                alert("El nombre de usuario ya existe");
                window.location.href="/administrador/usuarios/crear";
            </script>
            """

        # Comprobar correo
        cursor.execute(
            "SELECT id FROM usuarios WHERE correo = %s",
            (correo,)
        )

        if cursor.fetchone():

            cursor.close()

            return """
            <script>
                alert("El correo electrónico ya está registrado");
                window.location.href="/administrador/usuarios/crear";
            </script>
            """

        # Insertar usuario
        cursor.execute("""
            INSERT INTO usuarios
            (
                nombre_completo,
                correo,
                telefono,
                usuario,
                contrasena,
                id_rol
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            nombre,
            correo,
            telefono,
            usuario,
            password_hash,
            id_rol
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("gestionar_usuarios"))

    # Obtener roles
    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id_rol,
            rol
        FROM roles
        ORDER BY id_rol
    """)

    roles_db = cursor.fetchall()

    cursor.close()

    return render_template(
        "crear_usuario.html",
        roles=roles_db
    )

@app.route("/administrador/usuarios/eliminar/<int:id_usuario>")
def eliminar_usuario(id_usuario):

    # Verificar sesión
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    # Solo administrador
    if session.get("rol") != "Administrador":
        return redirect(url_for("inicio_usuario"))

    # No permitir eliminarse a sí mismo
    if id_usuario == session["id_usuario"]:

        return """
        <script>
            alert("No puedes eliminar tu propio usuario administrador");
            window.location.href="/administrador/usuarios";
        </script>
        """

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM usuarios WHERE id = %s",
        (id_usuario,)
    )

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for("gestionar_usuarios"))

@app.route("/usuarios")
def usuarios():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            usuarios.id,
            usuarios.nombre_completo,
            usuarios.correo,
            usuarios.telefono,
            usuarios.usuario,
            usuarios.id_rol,
            roles.rol
        FROM usuarios
        INNER JOIN roles
            ON usuarios.id_rol = roles.id_rol
        ORDER BY usuarios.id
    """)

    datos = cursor.fetchall()

    cursor.close()

    return {
        "mensaje": "Conexión exitosa",
        "cantidad": len(datos),
        "usuarios": datos
    }

# =========================================================
# REPORTE DE USUARIOS Y ROLES
# =========================================================

@app.route("/reporte")
def reporte():

    # Verificar que haya iniciado sesión
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    # Solo administrador
    if session.get("rol") != "Administrador":
        return redirect(url_for("inicio_usuario"))

    # Obtener filtro
    rol_filtro = request.args.get("rol")

    cursor = mysql.connection.cursor()

    # =====================================================
    # CONSULTA MULTITABLA CON INNER JOIN
    # =====================================================

    if rol_filtro:

        cursor.execute("""
            SELECT
                usuarios.id,
                usuarios.nombre_completo,
                usuarios.correo,
                usuarios.telefono,
                usuarios.usuario,
                roles.rol
            FROM usuarios
            INNER JOIN roles
                ON usuarios.id_rol = roles.id_rol
            WHERE roles.rol = %s
            ORDER BY usuarios.id DESC
        """, (rol_filtro,))

    else:

        cursor.execute("""
            SELECT
                usuarios.id,
                usuarios.nombre_completo,
                usuarios.correo,
                usuarios.telefono,
                usuarios.usuario,
                roles.rol
            FROM usuarios
            INNER JOIN roles
                ON usuarios.id_rol = roles.id_rol
            ORDER BY usuarios.id DESC
        """)

    usuarios = cursor.fetchall()

    cursor.close()

    return render_template(
        "reporte.html",
        usuarios=usuarios,
        rol_filtro=rol_filtro
    )


# =========================================================
# EXPORTAR REPORTE A EXCEL
# =========================================================

@app.route("/reporte_excel")
def reporte_excel():

    # Verificar sesión
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    # Solo administrador
    if session.get("rol") != "Administrador":
        return redirect(url_for("inicio_usuario"))

    # Obtener filtro
    rol_filtro = request.args.get("rol")

    cursor = mysql.connection.cursor()

    # =====================================================
    # CONSULTA MULTITABLA
    # =====================================================

    if rol_filtro:

        cursor.execute("""
            SELECT
                usuarios.id,
                usuarios.nombre_completo,
                usuarios.correo,
                usuarios.telefono,
                usuarios.usuario,
                roles.rol
            FROM usuarios
            INNER JOIN roles
                ON usuarios.id_rol = roles.id_rol
            WHERE roles.rol = %s
            ORDER BY usuarios.id DESC
        """, (rol_filtro,))

    else:

        cursor.execute("""
            SELECT
                usuarios.id,
                usuarios.nombre_completo,
                usuarios.correo,
                usuarios.telefono,
                usuarios.usuario,
                roles.rol
            FROM usuarios
            INNER JOIN roles
                ON usuarios.id_rol = roles.id_rol
            ORDER BY usuarios.id DESC
        """)

    datos = cursor.fetchall()

    cursor.close()

    # =====================================================
    # CREAR ARCHIVO EXCEL
    # =====================================================

    libro = Workbook()

    hoja = libro.active

    hoja.title = "Reporte Rentec"

    # Encabezados
    hoja.append([
        "ID",
        "Nombre completo",
        "Correo",
        "Teléfono",
        "Usuario",
        "Rol"
    ])

    # Datos
    for fila in datos:

        hoja.append([
            fila[0],
            fila[1],
            fila[2],
            fila[3],
            fila[4],
            fila[5]
        ])

    # =====================================================
    # GUARDAR EN MEMORIA
    # =====================================================

    archivo = io.BytesIO()

    libro.save(archivo)

    archivo.seek(0)

    # Descargar Excel
    return send_file(
        archivo,
        download_name="reporte_rentec.xlsx",
        as_attachment=True
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("inicio"))

if __name__ == "__main__":

    print("======================================")
    print("       RENTEC - FLASK INICIADO")
    print("======================================")
    print("Servidor: http://127.0.0.1:5000")
    print("======================================")

    app.run(debug=True)

