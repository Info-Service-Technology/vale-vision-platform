variable "name_prefix" { type = string }
variable "region" { type = string }
variable "cluster_arn" { type = string }
variable "cluster_name" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "target_group_backend_arn" { type = string }
variable "target_group_frontend_arn" { type = string }
variable "ecr_backend_url" { type = string }
variable "ecr_frontend_url" { type = string }
variable "ecr_inference_url" { type = string }
variable "backend_image_tag" { type = string }
variable "frontend_image_tag" { type = string }
variable "inference_image_tag" { type = string }
variable "backend_cpu" { type = number }
variable "backend_memory" { type = number }
variable "frontend_cpu" { type = number }
variable "frontend_memory" { type = number }
variable "inference_cpu" { type = number }
variable "inference_memory" { type = number }
variable "backend_desired_count" { type = number }
variable "frontend_desired_count" { type = number }
variable "inference_desired_count" { type = number }
variable "backend_container_port" { type = number }
variable "frontend_container_port" { type = number }
variable "inference_container_port" { type = number }
variable "log_group_backend_name" { type = string }
variable "log_group_frontend_name" { type = string }
variable "log_group_inference_name" { type = string }
variable "artifacts_bucket_name" { type = string }
variable "db_host" { type = string default = null }
variable "db_port" { type = number default = 3306 }
variable "db_name" { type = string }
variable "db_secret_arn" { type = string default = null }
variable "frontend_api_base_url" { type = string }
