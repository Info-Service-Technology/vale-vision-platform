variable "aws_region" { type = string default = "sa-east-1" }
variable "environment" { type = string default = "dev" }
variable "name_prefix" { type = string default = "vale-vision-dev" }

# Shared HDI platform inputs
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "ecs_cluster_arn" { type = string }
variable "ecs_cluster_name" { type = string }
variable "alb_https_listener_arn" { type = string }
variable "shared_alb_sg_id" { type = string }
variable "hosted_zone_id" { type = string }
variable "domain_name" { type = string }
variable "certificate_arn" { type = string default = null }

# App URLs
variable "backend_host" { type = string default = "api-valevision.dev.example.com" }
variable "frontend_host" { type = string default = "valevision.dev.example.com" }

# Compute
variable "backend_image_tag" { type = string default = "latest" }
variable "frontend_image_tag" { type = string default = "latest" }
variable "inference_image_tag" { type = string default = "latest" }
variable "backend_cpu" { type = number default = 512 }
variable "backend_memory" { type = number default = 1024 }
variable "frontend_cpu" { type = number default = 256 }
variable "frontend_memory" { type = number default = 512 }
variable "inference_cpu" { type = number default = 1024 }
variable "inference_memory" { type = number default = 2048 }
variable "backend_desired_count" { type = number default = 1 }
variable "frontend_desired_count" { type = number default = 1 }
variable "inference_desired_count" { type = number default = 1 }

# RDS strategy
variable "create_dedicated_rds" { type = bool default = false }
variable "db_name" { type = string default = "vale_vision" }
variable "db_username" { type = string default = "valevision_app" }
variable "db_password" { type = string default = null sensitive = true }
variable "existing_db_endpoint" { type = string default = null }
variable "existing_db_port" { type = number default = 3306 }
variable "existing_db_secret_arn" { type = string default = null }
variable "db_instance_class" { type = string default = "db.t4g.micro" }
variable "db_allocated_storage" { type = number default = 20 }
variable "db_engine_version" { type = string default = "8.0.36" }

# Frontend/build env
variable "frontend_api_base_url" { type = string default = "https://api-valevision.dev.example.com" }
