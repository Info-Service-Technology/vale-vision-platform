output "backend_repository_url" { value = module.ecr.backend_repository_url }
output "frontend_repository_url" { value = module.ecr.frontend_repository_url }
output "inference_repository_url" { value = module.ecr.inference_repository_url }
output "artifacts_bucket_name" { value = module.artifacts.bucket_name }
output "backend_target_group_arn" { value = module.alb_app.backend_target_group_arn }
output "frontend_target_group_arn" { value = module.alb_app.frontend_target_group_arn }
output "db_endpoint" { value = local.db_endpoint }
