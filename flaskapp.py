from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import sqlite3
import io

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # needed for flash messages

DB_PATH = "/home/ubuntu/flaskapp/users.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates the table if it doesn't exist.
    If you already created it, this does nothing (safe).
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          password TEXT NOT NULL,
          firstname TEXT,
          lastname TEXT,
          email TEXT,
          address TEXT,
          filename TEXT,
          filedata BLOB,
          wordcount INTEGER
        );
    """)
    conn.commit()
    conn.close()


def count_words(text: str) -> int:
    return len(text.split())


@app.route("/", methods=["GET"])
def home():
    # 4a Registration page
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    firstname = request.form.get("firstname", "").strip()
    lastname  = request.form.get("lastname", "").strip()
    email     = request.form.get("email", "").strip()
    address   = request.form.get("address", "").strip()

    if not all([username, password, firstname, lastname, email, address]):
        flash("All fields are required.")
        return redirect(url_for("home"))

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, password, firstname, lastname, email, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password, firstname, lastname, email, address))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        flash("That username already exists. Please choose another.")
        return redirect(url_for("home"))

    # Go directly to display page (step 4c) since details were collected here
    return redirect(url_for("profile", username=username))


@app.route("/details/<username>", methods=["GET", "POST"])
def details(username):
    if request.method == "GET":
        return render_template("details.html", username=username)

    firstname = request.form.get("firstname", "").strip()
    lastname = request.form.get("lastname", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()

    if not firstname or not lastname or not email or not address:
        flash("All fields are required.")
        return redirect(url_for("details", username=username))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET firstname=?, lastname=?, email=?, address=?
        WHERE username=?
    """, (firstname, lastname, email, address, username))
    conn.commit()
    conn.close()

    # 4c Redirect to display page
    return redirect(url_for("profile", username=username))


@app.route("/profile/<username>", methods=["GET"])
def profile(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    conn.close()

    if not user:
        flash("User not found.")
        return redirect(url_for("home"))

    # 4c Display accepted info + show word count + download button
    return render_template("profile.html", user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    # 4d Re-login page to retrieve user info
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    conn.close()

    if not user:
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return redirect(url_for("profile", username=username))


@app.route("/upload/<username>", methods=["POST"])
def upload(username):
    if "file" not in request.files:
        flash("No file part in request.")
        return redirect(url_for("profile", username=username))

    f = request.files["file"]
    if f.filename == "":
        flash("No file selected.")
        return redirect(url_for("profile", username=username))

    if f.filename.lower() != "limerick.txt":
        flash("Please upload the file named Limerick.txt.")
        return redirect(url_for("profile", username=username))

    data = f.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    wc = count_words(text)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET filename=?, filedata=?, wordcount=?
        WHERE username=?
    """, (f.filename, sqlite3.Binary(data), wc, username))
    conn.commit()
    conn.close()

    flash(f"Uploaded {f.filename}. Word count = {wc}.")
    return redirect(url_for("profile", username=username))


@app.route("/download/<username>", methods=["GET"])
def download(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, filedata FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row or row["filedata"] is None:
        flash("No stored file found. Upload Limerick.txt first.")
        return redirect(url_for("profile", username=username))

    filename = row["filename"] or "Limerick.txt"
    filedata = row["filedata"]

    return send_file(
        io.BytesIO(filedata),
        as_attachment=True,
        download_name=filename,
        mimetype="text/plain"
    )


# Ensure table exists even when run via Apache/mod_wsgi
init_db()

if __name__ == "__main__":
    # Optional local test
    app.run(host="0.0.0.0", port=5000, debug=True)
