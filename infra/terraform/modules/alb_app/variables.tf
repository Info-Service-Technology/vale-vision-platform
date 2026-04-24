variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "listener_arn" { type = string }
variable "backend_host" { type = string }
variable "frontend_host" { type = string }
variable "backend_container_port" { type = number }
variable "frontend_container_port" { type = number }
variable "health_check_path_backend" { type = string default = "/health" }
variable "health_check_path_frontend" { type = string default = "/" }
variable "frontend_priority" { type = number default = 210 }
variable "backend_priority" { type = number default = 220 }
