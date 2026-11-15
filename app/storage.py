"""Image uploads: stored in AWS S3 when S3_BUCKET is set, otherwise on local disk."""
import os
import uuid

from flask import current_app, url_for
from werkzeug.utils import secure_filename

ALLOWED = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def save_image(file):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError("Only PNG, JPG and WEBP images are allowed.")

    ext = file.filename.rsplit(".", 1)[1].lower()
    key = f"menu/{uuid.uuid4().hex}.{ext}"
    bucket = current_app.config["S3_BUCKET"]

    if bucket:
        import boto3  # credentials come from the EC2 IAM role, never from code
        region = current_app.config["AWS_REGION"]
        s3 = boto3.client("s3", region_name=region)
        s3.upload_fileobj(file, bucket, key, ExtraArgs={"ContentType": file.mimetype})
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

    folder = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(folder, exist_ok=True)
    name = secure_filename(key.replace("/", "_"))
    file.save(os.path.join(folder, name))
    return url_for("static", filename=f"uploads/{name}")
