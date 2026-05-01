resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.name_prefix}-backend"
  retention_in_days = 30
}
resource "aws_cloudwatch_log_group" "inference" {
  name              = "/ecs/${var.name_prefix}-inference"
  retention_in_days = 30
}
