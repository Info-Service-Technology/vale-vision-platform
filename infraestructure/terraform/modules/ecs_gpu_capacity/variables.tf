variable "project_name" {}
variable "cluster_name" {}
variable "vpc_id" {}
variable "subnet_ids" {
  type = list(string)
}
variable "security_group_ids" {
  type = list(string)
}
variable "instance_type" {
  default = "g4dn.xlarge"
}
variable "ami_id" {}
variable "min_size" {
  default = 0
}
variable "max_size" {
  default = 1
}
variable "desired_capacity" {
  default = 1
}