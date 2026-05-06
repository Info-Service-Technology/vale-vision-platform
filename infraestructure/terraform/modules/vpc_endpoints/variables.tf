variable "name_prefix" {
  type        = string
  description = "Prefix to use for VPC endpoint security group names"
}

variable "vpc_id" {
  type        = string
  description = "ID of the VPC where the endpoints will be created"
}
variable "private_subnet_ids" {
  type        = list(string)
  description = "List of private subnet IDs where the endpoints will be created"
}

variable "ecs_security_group_id" {
  type = string
  description = "ID of the security group used by ECS tasks/instances to allow access to VPC endpoints"
}