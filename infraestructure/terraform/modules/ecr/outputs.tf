output "backend_repository_url" { value = aws_ecr_repository.backend.repository_url }
output "inference_repository_url" { value = aws_ecr_repository.inference.repository_url }
output "backend_repository_arn" { value = aws_ecr_repository.backend.arn }
output "inference_repository_arn" { value = aws_ecr_repository.inference.arn }
