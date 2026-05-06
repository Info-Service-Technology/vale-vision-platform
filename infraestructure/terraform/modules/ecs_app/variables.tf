variable "name_prefix" {
  type = string
}

variable "region" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  type = string
}

variable "target_group_backend_arn" {
  type = string
}

variable "ecr_backend_url" {
  type = string
}

variable "ecr_inference_url" {
  type = string
}

variable "backend_image_tag" {
  type = string
}

variable "inference_image_tag" {
  type = string
}

variable "backend_cpu" {
  type = number
}

variable "backend_memory" {
  type = number
}

variable "inference_cpu" {
  type = number
}

variable "inference_memory" {
  type = number
}

variable "backend_desired_count" {
  type = number
}

variable "inference_desired_count" {
  type = number
}

variable "backend_container_port" {
  type = number
}

variable "inference_container_port" {
  type = number
}

variable "log_group_backend_name" {
  type = string
}

variable "log_group_inference_name" {
  type = string
}

variable "artifacts_bucket_name" {
  type = string
}

variable "sqs_queue_url" {
  type    = string
  default = null
}

variable "image_source_buckets" {
  type    = list(string)
  default = []
}

variable "db_host" {
  type    = string
  default = null
}

variable "db_port" {
  type    = number
  default = 3306
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_secret_arn" {
  type    = string
  default = null
}

variable "smtp_secret_arn" {
  type    = string
  default = null
}

variable "frontend_public_url" {
  type = string
}

variable "api_public_url" {
  type = string
}

variable "email_enabled" {
  type = bool
}

variable "email_from_name" {
  type = string
}

variable "email_from_address" {
  type = string
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
  type = bool
}

variable "smtp_host" {
  type = string
}

variable "smtp_port" {
  type = number
}

variable "smtp_username" {
  type = string
}

variable "smtp_use_starttls" {
  type = bool
}

variable "smtp_use_ssl" {
  type = bool
}

variable "smtp_timeout_seconds" {
  type = number
}

variable "inference_capacity_provider_name" {
  type        = string
  description = "Capacity provider EC2 GPU para o serviço de inferência"
  default     = null
}

variable "inference_gpu_desired_count" {
  type    = number
  default = 1
}
