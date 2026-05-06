import json
import os
import time
from urllib.parse import unquote_plus

import boto3

from app.processor import process_image_from_s3


AWS_REGION = os.getenv("AWS_REGION", "sa-east-1")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
WAIT_TIME_SECONDS = int(os.getenv("WAIT_TIME_SECONDS", "20"))
VISIBILITY_TIMEOUT = int(os.getenv("VISIBILITY_TIMEOUT", "300"))

sqs = boto3.client("sqs", region_name=AWS_REGION)


def extract_s3_records(message_body: str):
    body = json.loads(message_body)

    # Formato simples/manual:
    # {"bucket":"...", "key":"..."}
    if "bucket" in body and "key" in body:
        return [
            {
                "s3": {
                    "bucket": {"name": body["bucket"]},
                    "object": {"key": body["key"]},
                }
            }
        ]

    # Evento direto do S3
    if "Records" in body:
        return body["Records"]

    # Caso venha encapsulado por SNS
    if "Message" in body:
        message = json.loads(body["Message"])
        return message.get("Records", [])

    return []


def handle_message(message):
    receipt_handle = message["ReceiptHandle"]
    records = extract_s3_records(message["Body"])

    if not records:
        raise ValueError(f"Mensagem SQS sem Records S3 reconhecíveis: {message['Body']}")

    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        print(f"[worker] Processando imagem: s3://{bucket}/{key}")

        process_image_from_s3(bucket=bucket, key=key)

    sqs.delete_message(
        QueueUrl=SQS_QUEUE_URL,
        ReceiptHandle=receipt_handle,
    )

    print("[worker] Mensagem processada e removida da fila.")


def main():
    if not SQS_QUEUE_URL:
        raise RuntimeError("Variável SQS_QUEUE_URL não configurada.")

    print("[worker] Iniciado. Aguardando mensagens SQS...")

    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=WAIT_TIME_SECONDS,
            VisibilityTimeout=VISIBILITY_TIMEOUT,
        )

        messages = response.get("Messages", [])
        

        if not messages:
            continue

        for message in messages:
            try:
                handle_message(message)
            except Exception as exc:
                print(f"[worker][erro] Falha ao processar mensagem: {exc}")
                # Não deleta a mensagem. Ela volta para fila após VisibilityTimeout.


if __name__ == "__main__":
    main()