variable "name_prefix" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  default   = null
  sensitive = true
}

variable "existing_db_secret_arn" {
  type    = string
  default = null
}

variable "create_db_secret" {
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

variable "create_smtp_secret" {
  type    = bool
  default = false
}
