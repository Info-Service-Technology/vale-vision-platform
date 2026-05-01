variable "aws_region" {
  type    = string
  default = "sa-east-1"
}

variable "environment" {
  type    = string
  default = "prd"
}

variable "name_prefix" {
  type    = string
  default = "sansx-vision-prd"
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "ecs_cluster_arn" {
  type    = string
  default = null
}

variable "ecs_cluster_name" {
  type    = string
  default = null
}

variable "create_ecs_cluster" {
  type    = bool
  default = false
}

variable "enable_ecs_container_insights" {
  type    = bool
  default = true
}

variable "alb_https_listener_arn" {
  type = string
}

variable "shared_alb_sg_id" {
  type = string
}

variable "primary_hosted_zone_id" {
  type = string
}

variable "secondary_hosted_zone_id" {
  type    = string
  default = null
}

variable "domain_name" {
  type    = string
  default = "sensxvisionplatform.com"
}

variable "certificate_arn" {
  type    = string
  default = null
}

variable "backend_host" {
  type    = string
  default = "api.sensxvisionplatform.com"
}

variable "frontend_host" {
  type    = string
  default = "sensxvisionplatform.com"
}

variable "frontend_redirect_hosts" {
  type = list(string)
  default = [
    "www.sensxvisionplatform.com",
    "sensxvisionplatform.com.br",
    "www.sensxvisionplatform.com.br"
  ]
}

variable "frontend_dns_records" {
  type = list(object({
    zone_id = string
    name    = string
  }))
  default = []
}

variable "backend_dns_records" {
  type = list(object({
    zone_id = string
    name    = string
  }))
  default = []
}

variable "backend_image_tag" {
  type    = string
  default = "latest"
}

variable "inference_image_tag" {
  type    = string
  default = "latest"
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "inference_cpu" {
  type    = number
  default = 1024
}

variable "inference_memory" {
  type    = number
  default = 2048
}

variable "backend_desired_count" {
  type    = number
  default = 1
}

variable "inference_desired_count" {
  type    = number
  default = 1
}

variable "create_dedicated_rds" {
  type    = bool
  default = false
}

variable "db_name" {
  type    = string
  default = "vale_vision"
}

variable "db_username" {
  type    = string
  default = "valevision_app"
}

variable "db_password" {
  type      = string
  default   = null
  sensitive = true
}

variable "existing_db_endpoint" {
  type    = string
  default = null
}

variable "existing_db_port" {
  type    = number
  default = 3306
}

variable "existing_db_secret_arn" {
  type    = string
  default = null
}

variable "create_smtp_secret" {
  type    = bool
  default = false
}

variable "smtp_password" {
  type      = string
  default   = null
  sensitive = true
}

variable "existing_smtp_secret_arn" {
  type    = string
  default = null
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_engine_version" {
  type    = string
  default = "8.0.36"
}

variable "frontend_public_url" {
  type    = string
  default = "https://sensxvisionplatform.com"
}

variable "api_public_url" {
  type    = string
  default = "https://api.sensxvisionplatform.com"
}

variable "email_enabled" {
  type    = bool
  default = true
}

variable "email_from_name" {
  type    = string
  default = "SensX Vision Platform"
}

variable "email_from_address" {
  type    = string
  default = "no-reply@sensxvisionplatform.com"
}

variable "email_reply_to" {
  type    = string
  default = null
}

variable "email_support_address" {
  type    = string
  default = null
}

variable "email_debug_return_tokens" {
  type    = bool
  default = false
}

variable "smtp_host" {
  type    = string
  default = "smtp.gmail.com"
}

variable "smtp_port" {
  type    = number
  default = 587
}

variable "smtp_username" {
  type    = string
  default = ""
}

variable "smtp_use_starttls" {
  type    = bool
  default = true
}

variable "smtp_use_ssl" {
  type    = bool
  default = false
}

variable "smtp_timeout_seconds" {
  type    = number
  default = 30
}

variable "github_org" {
  type    = string
  default = ""
}

variable "github_repo" {
  type    = string
  default = ""
}

variable "enable_github_oidc" {
  type    = bool
  default = false
}
