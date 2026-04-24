output "backend_service_name" { value = aws_ecs_service.backend.name }
output "frontend_service_name" { value = aws_ecs_service.frontend.name }
output "inference_service_name" { value = aws_ecs_service.inference.name }
