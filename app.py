from flask import Flask, render_template, request, redirect, session, send_file, make_response, url_for
import sqlite3
from io import BytesIO
from PIL import Image
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret"

# ------------------ DATABASE INIT ------------------
def init_db():
    with sqlite3.connect("phishing.db") as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS admin (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL
                    )''')

        c.execute('''CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        campaign_id INTEGER,
                        opened INTEGER DEFAULT 0,
                        clicked INTEGER DEFAULT 0,
                        submitted INTEGER DEFAULT 0,
                        password TEXT,
                        timestamp TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                         group_name TEXT NOT NULL
                     )
                    ''')
        c.execute('''CREATE TABLE IF NOT EXISTS email_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        message TEXT NOT NULL
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS campaigns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        message TEXT,
                        landing_page TEXT,
                        group_name TEXT,
                        launch_date TEXT
                    )''')


        # Insert default admin
        c.execute("SELECT * FROM admin WHERE username='admin'")
        if not c.fetchone():
            c.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin123'))

        conn.commit()

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return redirect("/admin/login")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with sqlite3.connect("phishing.db") as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
            admin = c.fetchone()

        if admin:
            session["admin"] = True
            return redirect("/admin/dashboard")

        return "Invalid credentials"
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/admin/login")

    with sqlite3.connect("phishing.db") as conn:
        c = conn.cursor()

        c.execute("SELECT id, name FROM campaigns")
        campaigns = c.fetchall()

        c.execute("SELECT COUNT(*) FROM campaigns")
        total_campaigns = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events")
        total_targets = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events WHERE clicked=1")
        total_clicked = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events WHERE submitted=1")
        total_submitted = c.fetchone()[0]

    return render_template(
        "admin_dashboard.html",
        campaigns=campaigns,
        total_campaigns=total_campaigns,
        total_targets=total_targets,
        total_clicked=total_clicked,
        total_submitted=total_submitted
    )


@app.route('/admin/create-campaign', methods=['GET', 'POST'])
def create_campaign():

    if not session.get("admin"):
        return redirect("/admin/login")

    if request.method == 'POST':

        name = request.form['name']
        message = request.form['message']
        landing_page = request.form['landing_page']
        group_name = request.form['group_name']

        targets = [
            email.strip()
            for email in request.form['targets'].split(',')
            if email.strip()
        ]

        with sqlite3.connect("phishing.db") as conn:
            c = conn.cursor()

            # Insert campaign
            c.execute("""
                INSERT INTO campaigns
                (name, message, landing_page, group_name, launch_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                name,
                message,
                landing_page,
                group_name,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            campaign_id = c.lastrowid

            # Insert targets into events table
            for email in targets:
                c.execute("""
                    INSERT INTO events
                    (email, campaign_id)
                    VALUES (?, ?)
                """, (email, campaign_id))

            conn.commit()

        return redirect(f"/admin/campaign/{campaign_id}/links")

    return render_template('create_campaign.html')

@app.route("/admin/campaign/<int:campaign_id>/links")
def campaign_links(campaign_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    with sqlite3.connect("phishing.db") as conn:
        c = conn.cursor()
        c.execute("SELECT email FROM events WHERE campaign_id=?", (campaign_id,))
        targets = c.fetchall()

    links = [
        {
            "email": email[0],
            "link": f"http://127.0.0.1:5000/fake-login?email={email[0]}&campaign_id={campaign_id}"
        }
        for email in targets
    ]

    return render_template("campaign_links.html", campaign_id=campaign_id, links=links)


@app.route("/admin/campaign/<int:campaign_id>/preview/<email>")
def preview_campaign(campaign_id, email):
    if not session.get("admin"):
        return redirect("/admin/login")

    with sqlite3.connect("phishing.db") as conn:
        c = conn.cursor()
        c.execute("SELECT name, message FROM campaigns WHERE id=?", (campaign_id,))
        campaign = c.fetchone()
        
    if campaign:
        name, message = campaign
        return render_template("preview_email.html", email=email, campaign_id=campaign_id, subject=name, message=message)
    return "Campaign not found", 404


@app.route("/fake-login", methods=["GET", "POST"])
def fake_login():
    email = request.args.get("email")
    campaign_id = request.args.get("campaign_id")

    if request.method == "POST":
        entered_email = request.form["email"]
        password = request.form["password"]

        with sqlite3.connect("phishing.db") as conn:
            c = conn.cursor()
            c.execute("""
            UPDATE events
            SET
                submitted = 1,
                password = ?,
                timestamp = ?
            WHERE email = ? AND campaign_id = ?
            """, (password,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                email,
                campaign_id
            ))
            conn.commit()

        with open("captured_credentials.txt", "a") as f:
            f.write(f"{datetime.now()} | Target: {email} | Entered: {entered_email}/{password}\n")

        return redirect("/awareness")

    # Mark as clicked ONLY when victim visits phishing page
    if request.method == "GET":

        if email and campaign_id:

            with sqlite3.connect("phishing.db") as conn:
                c = conn.cursor()

                c.execute("""
                    UPDATE events
                    SET 
                          opened = 1,
                          clicked = 1
                    WHERE email = ? AND campaign_id = ?
                """, (email, campaign_id))

                conn.commit()

    return render_template(
    "fake_login.html",
    email=email
)


@app.route("/track/open")
def track_open():
    email = request.args.get("email")
    campaign_id = request.args.get("campaign_id")

    if email and campaign_id:
        with sqlite3.connect("phishing.db") as conn:
            c = conn.cursor()
            c.execute("UPDATE events SET opened = 1 WHERE email = ? AND campaign_id = ?", (email, campaign_id))
            conn.commit()

    img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    byte_io = BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return send_file(byte_io, mimetype='image/png')


@app.route("/awareness")
def awareness():
    return render_template("awareness.html")


@app.route("/admin/campaign/<int:campaign_id>/results")
def campaign_results(campaign_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    with sqlite3.connect("phishing.db") as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM campaigns WHERE id=?", (campaign_id,))
        campaign = c.fetchone()

        c.execute("""
        SELECT
            email,
            password,
            CASE WHEN opened=1 OR clicked=1 OR submitted=1 THEN 1 ELSE 0 END,
            clicked,
            submitted,
            timestamp
        FROM events
        WHERE campaign_id=?
    """, (campaign_id,))
        results = c.fetchall()

        submitted_count = sum(
        1 for row in results
        if row[4]
    )

    return render_template("campaign_results.html",
                           campaign_id=campaign_id,
                           campaign_name=campaign[0],
                           results=results,
                           submitted_count=submitted_count)


@app.route("/admin/campaign/<int:campaign_id>/export")
def export_csv(campaign_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    with sqlite3.connect("phishing.db") as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM campaigns WHERE id=?", (campaign_id,))
        campaign = c.fetchone()

        c.execute("SELECT email, password, opened, clicked, submitted, timestamp FROM events WHERE campaign_id=?", (campaign_id,))
        results = c.fetchall()

    output = [[
    "Email",
    "Password",
    "Opened",
    "Clicked",
    "Submitted",
    "Timestamp"
]]
    output.extend(results)

    csv_data = '\n'.join([','.join(map(str, row)) for row in output])
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename={campaign[0]}_results.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin/login")

@app.route('/admin/users-groups', methods=['GET', 'POST'])
def users_groups():
    if not session.get("admin"):
        return redirect("/admin/login")
    
    import sqlite3
    from flask import request, render_template

    conn = sqlite3.connect('phishing.db')
    c = conn.cursor()

    # Form submission
    if request.method == 'POST':
        email = request.form['email'].strip()
        group = request.form['group'].strip()
        c.execute("INSERT INTO users (email, group_name) VALUES (?, ?)", (email, group))
        conn.commit()

    # Fetch users
    c.execute("SELECT email, group_name FROM users")
    users = c.fetchall()
    conn.close()

    return render_template('users_groups.html', users=users)

@app.route("/admin/email-templates", methods=["GET", "POST"])
def email_templates():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = sqlite3.connect("phishing.db")
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["template_name"]
        subject = request.form["subject"]
        message = request.form["message"]
        add_link = request.form.get("add_link")

        if add_link:
            message += '\n\n <a href="/fake-login">View Policy Document</a>'

        cursor.execute("INSERT INTO email_templates (name, subject, message) VALUES (?, ?, ?)", (name, subject, message))
        conn.commit()

    # ✅ Fetch all templates to display them
    cursor.execute("SELECT id, name, subject, message FROM email_templates")
    templates = cursor.fetchall()
    conn.close()

    # ✅ Return the page with templates passed
    return render_template("email_templates.html", templates=templates)
@app.route("/admin/email-templates/view/<int:template_id>")
def view_email_template(template_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = sqlite3.connect("phishing.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, subject, message FROM email_templates WHERE id = ?", (template_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        name, subject, message = result
        return render_template("preview_email.html", subject=subject, sender=name, message=message)
    else:
        return "Template not found", 404


@app.route("/admin/email-templates/delete/<int:template_id>")
def delete_email_template(template_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = sqlite3.connect("phishing.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_templates WHERE id=?", (template_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("email_templates"))
@app.route('/admin/results')
def results():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = sqlite3.connect("phishing.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, message, group_name, launch_date FROM campaigns")
    campaigns = cursor.fetchall()
    conn.close()
    return render_template("results.html", campaigns=campaigns)

# ------------------ MAIN ------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)











