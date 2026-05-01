output "backend_service_name" { value = aws_ecs_service.backend.name }
output "inference_service_name" { value = aws_ecs_service.inference.name }
output "backend_service_arn" { value = aws_ecs_service.backend.id }
output "inference_service_arn" { value = aws_ecs_service.inference.id }
output "cluster_arn" { value = var.cluster_arn }
output "cluster_name" { value = var.cluster_name }
