variable "role_name" {
  type = string
}

variable "github_org" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "ecr_repository_arns" {
  type    = list(string)
  default = []
}

variable "ecs_cluster_arns" {
  type    = list(string)
  default = []
}

variable "ecs_service_arns" {
  type    = list(string)
  default = []
}

variable "allow_terraform_apply" {
  type    = bool
  default = false
}

variable "route53_hosted_zone_arns" {
  type    = list(string)
  default = []
}

variable "acm_certificate_arns" {
  type    = list(string)
  default = []
}

variable "secrets_arns" {
  type    = list(string)
  default = []
}

variable "s3_bucket_arns" {
  type    = list(string)
  default = []
}

variable "iam_role_arns" {
  type    = list(string)
  default = []
}

variable "rds_arns" {
  type    = list(string)
  default = []
}
