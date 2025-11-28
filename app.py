from flask import Flask, request, render_template_string, send_from_directory
import os
import mimetypes
import base64
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)

EMAIL_USER = os.environ.get("EMAIL_USER", "dashprintsllc@gmail.com")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

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

    # Build email content for SendGrid
    subject = f"New Quote Request from {name} – {company}".strip(" –")
    html_content = f"""
        <p>New quote request from <strong>Dash Prints Website</strong>:</p>
        <p><strong>Name:</strong> {name or ""}</p>
        <p><strong>Company:</strong> {company or ""}</p>
        <p><strong>Email:</strong> {email or ""}</p>
        <p><strong>Phone:</strong> {phone or ""}</p>
        <p><strong>Project Details:</strong><br>{(details or "").replace(chr(10), "<br>")}</p>
    """

    # Build SendGrid v3 API payload
    payload = {
        "personalizations": [
            {
                "to": [{"email": EMAIL_USER}],
                "subject": subject,
            }
        ],
        "from": {"email": EMAIL_USER},
        "content": [
            {
                "type": "text/html",
                "value": html_content,
            }
        ],
    }

    # Attach uploaded artwork if present and saved
    if saved_filepath and saved_filename:
        try:
            with open(saved_filepath, "rb") as f:
                file_data = f.read()
            encoded_file = base64.b64encode(file_data).decode()

            mime_type, _ = mimetypes.guess_type(saved_filename)
            if not mime_type:
                mime_type = "application/octet-stream"

            payload.setdefault("attachments", []).append(
                {
                    "content": encoded_file,
                    "filename": saved_filename,
                    "type": mime_type,
                    "disposition": "attachment",
                }
            )
        except Exception:
            # If anything goes wrong with the attachment, continue without it
            pass

    # Send email using SendGrid v3 API via HTTPS
    if not SENDGRID_API_KEY:
        print("Email error: SENDGRID_API_KEY is not set")
        return render_template_string(f"""
            <!DOCTYPE html>
            <html lang=\\"en\\">
            <head>
                <meta charset=\\"UTF-8\\">
                <title>Error – Dash Prints</title>
                <link rel=\\"stylesheet\\" href=\\"style.css\\">
            </head>
            <body>
                <main class=\\"legal-page\\">
                    <h1>Something went wrong</h1>
                    <p>Email service is not configured correctly. Please contact us directly at <a href=\\"mailto:{EMAIL_USER}\\">{EMAIL_USER}</a>.</p>
                    <p><a href=\\"/\\">← Back to Home</a></p>
                </main>
            </body>
            </html>
        """)

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,  # seconds
        )
        print(f"✅ DEBUG: SendGrid HTTP status: {response.status_code}")
        if response.status_code >= 400:
            print(f"SendGrid error body: {response.text}")

        # Thank-you page returned directly
        return render_template_string("""
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
                <meta charset=\"UTF-8\">
                <title>Thank You – Dash Prints</title>
                <link rel=\"stylesheet\" href=\"style.css\">
            </head>
            <body>
                <main class=\"legal-page\">
                    <h1>Thank you!</h1>
                    <p>Your quote request was successfully sent. We will contact you within one business day.</p>
                    <p><a href=\"/\">← Back to Home</a></p>
                </main>
            </body>
            </html>
        """)
    except Exception as e:
        print(f"Email error: {e}")
        return render_template_string(f"""
            <!DOCTYPE html>
            <html lang=\\"en\\">
            <head>
                <meta charset=\\"UTF-8\\">
                <title>Error – Dash Prints</title>
                <link rel=\\"stylesheet\\" href=\\"style.css\\">
            </head>
            <body>
                <main class=\\"legal-page\\">
                    <h1>Something went wrong</h1>
                    <p>We weren't able to send your request by email. Please try again in a few minutes or contact us directly at <a href=\\"mailto:{EMAIL_USER}\\">{EMAIL_USER}</a>.</p>
                    <p><a href=\\"/\\">← Back to Home</a></p>
                </main>
            </body>
            </html>
        """)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('images', 'Logo_transparent.png', mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
       


