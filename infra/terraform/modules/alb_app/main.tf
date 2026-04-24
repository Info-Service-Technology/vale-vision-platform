data "aws_lb_listener" "shared" {
  arn = var.listener_arn
}

data "aws_lb" "shared" {
  arn = data.aws_lb_listener.shared.load_balancer_arn
}

resource "aws_lb_target_group" "backend" {
  name        = substr("${var.name_prefix}-be-tg", 0, 32)
  port        = var.backend_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = var.health_check_path_backend
    matcher             = "200-399"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
  }
}

resource "aws_lb_target_group" "frontend" {
  name        = substr("${var.name_prefix}-fe-tg", 0, 32)
  port        = var.frontend_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = var.health_check_path_frontend
    matcher             = "200-399"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
  }
}

resource "aws_lb_listener_rule" "frontend_host" {
  listener_arn = var.listener_arn
  priority     = var.frontend_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  condition {
    host_header { values = [var.frontend_host] }
  }
}

resource "aws_lb_listener_rule" "backend_host" {
  listener_arn = var.listener_arn
  priority     = var.backend_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    host_header { values = [var.backend_host] }
  }
}
