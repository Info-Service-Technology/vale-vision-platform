import os
import uuid
import json
from datetime import datetime
from io import BytesIO
from PIL import Image

import boto3
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

uploads_bp = Blueprint("uploads", __name__)

AWS_REGION = os.getenv("AWS_REGION", "sa-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "sansx-vision-prd")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

s3_client = boto3.client("s3", region_name=AWS_REGION)
sqs_client = boto3.client("sqs", region_name=AWS_REGION)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@uploads_bp.route("/api/events/upload-image", methods=["POST"])
def upload_image():
    try:
        file = request.files.get("file")

        if not file:
            return jsonify({"error": "Arquivo não enviado"}), 400

        if not file.filename:
            return jsonify({"error": "Nome de arquivo inválido"}), 400

        if not allowed_file(file.filename):
            return jsonify({
                "error": "Formato inválido. Use JPG, JPEG, PNG ou WEBP."
            }), 400

        tenant = request.form.get("tenant", "vale")
        camera = request.form.get("camera", "cam01")
        grupo = request.form.get("grupo", "desconhecido")

        now = datetime.utcnow()

        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")

        original_filename = secure_filename(file.filename)

        unique_filename = (
            f"{uuid.uuid4().hex}_{original_filename}"
        )

        s3_key = (
            f"raw/"
            f"tenant={tenant}/"
            f"camera={camera}/"
            f"year={year}/"
            f"month={month}/"
            f"day={day}/"
            f"{unique_filename}"
        )

        compressed_file = compress_image(file)

        s3_client.upload_fileobj(
            Fileobj=compressed_file,
            Bucket=S3_BUCKET,
            Key=s3_key,
            ExtraArgs={
                "ContentType": "image/jpeg"
            }
        )

        sqs_payload = {
            "bucket": S3_BUCKET,
            "key": s3_key,
            "tenant": tenant,
            "camera": camera,
            "grupo": grupo,
            "uploaded_at": now.isoformat()
        }

        sqs_response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(sqs_payload)
        )

        return jsonify({
            "status": "queued",
            "bucket": S3_BUCKET,
            "s3_key": s3_key,
            "message_id": sqs_response.get("MessageId")
        }), 202

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
    
def compress_image(file_storage, quality=75, max_size=(1600, 1600)):
    image = Image.open(file_storage)

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image.thumbnail(max_size)

    output = BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=quality,
        optimize=True
    )

    output.seek(0)

    return output
