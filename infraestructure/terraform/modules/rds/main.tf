resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "this" {
  identifier              = "${var.name_prefix}-mysql"
  engine                  = "mysql"
  engine_version          = var.engine_version
  instance_class          = var.db_instance_class
  allocated_storage       = var.allocated_storage
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [var.security_group_id]
  storage_encrypted       = true
  skip_final_snapshot     = true
  backup_retention_period = 7
  deletion_protection     = false
  publicly_accessible     = false

  lifecycle {
    ignore_changes = [password]
  }
}