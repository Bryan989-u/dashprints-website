from flask import Flask, request, render_template_string, send_from_directory
import smtplib
from email.message import EmailMessage
import os
import mimetypes
from werkzeug.utils import secure_filename

app = Flask(__name__)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.environ.get("EMAIL_USER", "dashprintsllc@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

# Maximum upload size: 10 MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Only allow safe artwork file types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Where uploaded files will be stored
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    # Serve the main website page
    return send_from_directory(".", "index.html")



@app.route("/style.css")
def styles():
    # Serve the main stylesheet
    return send_from_directory(".", "style.css")


# Serve image assets from the images folder
@app.route("/images/<path:filename>")
def images(filename):
    # Serve image assets from the images folder
    return send_from_directory("images", filename)

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get("name")
    company = request.form.get("company")
    email = request.form.get("email")
    phone = request.form.get("phone")
    details = request.form.get("project_details")

    # Handle optional file upload securely
    uploaded_file = request.files.get("artwork_file")
    saved_filepath = None
    saved_filename = None

    if uploaded_file and uploaded_file.filename:
        # Check extension against allow‑list
        if not allowed_file(uploaded_file.filename):
            return render_template_string("""
                <!DOCTYPE html>
                <html lang=\"en\">
                <head>
                    <meta charset=\"UTF-8\">
                    <title>File Type Not Allowed – Dash Prints</title>
                    <link rel=\"stylesheet\" href=\"style.css\">\n                </head>
                <body>
                    <main class=\"legal-page\">\n                        <h1>File type not allowed</h1>\n                        <p>For security reasons, we only accept artwork in PNG, JPG, or JPEG formats.</p>\n                        <p>Please go back and upload a supported file type.</p>\n                        <p><a href=\"/\">← Back to Home</a></p>\n                    </main>\n                </body>\n                </html>
            """)

        # Use a safe filename and save to uploads directory
        safe_name = secure_filename(uploaded_file.filename)
        saved_filename = safe_name
        saved_filepath = os.path.join(UPLOADS_DIR, safe_name)
        uploaded_file.save(saved_filepath)

    # Build email
    msg = EmailMessage()
    msg["Subject"] = f"TEST – New Quote Request from {name} – {company}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    body = f"""
New quote request from Dash Prints Website:

Name: {name}
Company: {company}
Email: {email}
Phone: {phone}

Project Details:
{details}
"""
    msg.set_content(body)

    # Attach uploaded artwork if present and saved
    if saved_filepath and saved_filename:
        try:
            with open(saved_filepath, "rb") as f:
                file_data = f.read()
            maintype, subtype = "application", "octet-stream"
            mime_type, _ = mimetypes.guess_type(saved_filename)
            if mime_type:
                maintype, subtype = mime_type.split("/", 1)
            msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=saved_filename)
        except Exception:
            # If anything goes wrong with the attachment, continue without it
            pass

    # Send email using Gmail SMTP
    try:
        print("📡 DEBUG: Connecting to Gmail SMTP...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            print("🔐 DEBUG: TLS started, logging in...")
            server.login(EMAIL_USER, EMAIL_PASS)
            print(f"✅ DEBUG: Logged in as {EMAIL_USER}, preparing to send email...")
            print("📤 DEBUG: Attempting to send owner email...")
            server.send_message(msg)

        # Thank-you page returned directly
        return render_template_string("""
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
                <meta charset=\"UTF-8\">\n                <title>Thank You – Dash Prints</title>
                <link rel=\"stylesheet\" href=\"style.css\">\n            </head>
            <body>
                <main class=\"legal-page\">\n                    <h1>Thank you!</h1>\n                    <p>Your quote request was successfully sent. We will contact you within one business day.</p>\n                    <p><a href=\"/\">← Back to Home</a></p>\n                </main>\n            </body>\n            </html>
        """)
    except Exception as e:
        return f"An error occurred while sending your request: {e}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
       


