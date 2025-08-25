from flask import Flask, request, jsonify, render_template_string
import os, mimetypes
import magic  # 來自 python-magic，讀檔頭判斷
from datetime import datetime

app = Flask(__name__)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

INDEX_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>MIME Upload Tester</title></head>
<body>
  <h1>MIME Upload Tester</h1>
  <form action="/upload" method="post" enctype="multipart/form-data">
    <p><input type="file" name="file" required></p>
    <p><button type="submit">Upload</button></p>
  </form>
  <p>用這個表單在不同瀏覽器/作業系統上傳（DOCX/PDF等），伺服器會回傳實際收到的標頭與判斷。</p>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400

    # 伺服器端存檔（可對照 python-magic）
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    save_path = os.path.join(UPLOAD_DIR, f"{ts}-{f.filename}")
    f.save(save_path)

    # 1) 瀏覽器在 multipart 中傳的 Content-Type（表單欄位層級）
    browser_sent = getattr(f, "content_type", None)

    # 2) Flask/werkzeug 對檔案型態的看法
    flask_mimetype = getattr(f, "mimetype", None)

    # 3) 伺服器用副檔名猜（不可靠，但可對照）
    ext_guess, _ = mimetypes.guess_type(f.filename)

    # 4) 直接讀檔頭（magic number）
    try:
        magic_type = magic.from_file(save_path, mime=True)
    except Exception as e:
        magic_type = f"magic error: {e}"

    # 5) HTTP Request 層級的標頭（多數情況為 multipart/form-data; boundary=...）
    req_content_type = request.headers.get("Content-Type")

    # 只回最關鍵的 header，避免太長
    headers_subset = {k: v for k, v in request.headers.items() if k.lower() in {
        "content-type", "user-agent", "origin", "referer"
    }}

    result = {
        "filename": f.filename,
        "http_request_content_type": req_content_type,
        "form_field_content_type_from_browser": browser_sent,
        "flask_detected_mimetype": flask_mimetype,
        "mimetypes_guess_from_extension": ext_guess,
        "python_magic_from_file": magic_type,
        "request_headers_subset": headers_subset,
        "saved_to": save_path,
    }

    # 也印到容器日誌，方便 `docker compose logs -f`
    print("\n=== Upload Received ===")
    for k, v in result.items():
        print(f"{k}: {v}")
    print("=======================\n", flush=True)

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
