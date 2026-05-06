output "capacity_provider_name" {
  value = aws_ecs_capacity_provider.gpu.name
}

output "asg_name" {
  value = aws_autoscaling_group.ecs_gpu.name
}

output "launch_template_id" {
  value = aws_launch_template.ecs_gpu.id
}