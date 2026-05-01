resource "aws_secretsmanager_secret" "db" {
  count = var.create_db_secret ? 1 : 0
  name  = "${var.name_prefix}/db"
}

resource "aws_secretsmanager_secret_version" "db" {
  count     = var.create_db_secret ? 1 : 0
  secret_id = aws_secretsmanager_secret.db[0].id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    dbname   = var.db_name
  })
}

resource "aws_secretsmanager_secret" "smtp" {
  count = var.create_smtp_secret ? 1 : 0
  name  = "${var.name_prefix}/smtp-password"
}

resource "aws_secretsmanager_secret_version" "smtp" {
  count         = var.create_smtp_secret ? 1 : 0
  secret_id     = aws_secretsmanager_secret.smtp[0].id
  secret_string = var.smtp_password
}
