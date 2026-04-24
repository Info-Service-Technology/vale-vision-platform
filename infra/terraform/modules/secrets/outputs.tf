output "db_secret_arn" {
  value = var.create_db_secret ? aws_secretsmanager_secret.db[0].arn : var.existing_db_secret_arn
}
