output "backend_target_group_arn" { value = aws_lb_target_group.backend.arn }
output "frontend_target_group_arn" { value = aws_lb_target_group.frontend.arn }
output "alb_dns_name" { value = data.aws_lb.shared.dns_name }
