data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.name_prefix}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "execution_policy" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secret_access" {
  name = "${var.name_prefix}-secret-access"
  role = aws_iam_role.task_execution.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = ["secretsmanager:GetSecretValue"],
        Resource = compact([var.db_secret_arn])
      }
    ]
  })
}

resource "aws_iam_role" "task_role" {
  name               = "${var.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role_policy" "task_access" {
  name = "${var.name_prefix}-task-access"
  role = aws_iam_role.task_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        Resource = [
          "arn:aws:s3:::${var.artifacts_bucket_name}",
          "arn:aws:s3:::${var.artifacts_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = ["secretsmanager:GetSecretValue"],
        Resource = compact([var.db_secret_arn])
      }
    ]
  })
}

locals {
  backend_container = [{
    name      = "backend"
    image     = "${var.ecr_backend_url}:${var.backend_image_tag}"
    essential = true
    portMappings = [{ containerPort = var.backend_container_port, hostPort = var.backend_container_port, protocol = "tcp" }]
    environment = [
      { name = "APP_NAME", value = "vale-vision-backend" },
      { name = "DB_HOST", value = coalesce(var.db_host, "") },
      { name = "DB_PORT", value = tostring(var.db_port) },
      { name = "DB_NAME", value = var.db_name },
      { name = "ARTIFACTS_BUCKET", value = var.artifacts_bucket_name }
    ]
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = var.log_group_backend_name,
        awslogs-region        = var.region,
        awslogs-stream-prefix = "ecs"
      }
    }
  }]

  frontend_container = [{
    name      = "frontend"
    image     = "${var.ecr_frontend_url}:${var.frontend_image_tag}"
    essential = true
    portMappings = [{ containerPort = var.frontend_container_port, hostPort = var.frontend_container_port, protocol = "tcp" }]
    environment = [
      { name = "VITE_API_BASE_URL", value = var.frontend_api_base_url }
    ]
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = var.log_group_frontend_name,
        awslogs-region        = var.region,
        awslogs-stream-prefix = "ecs"
      }
    }
  }]

  inference_container = [{
    name      = "inference"
    image     = "${var.ecr_inference_url}:${var.inference_image_tag}"
    essential = true
    portMappings = [{ containerPort = var.inference_container_port, hostPort = var.inference_container_port, protocol = "tcp" }]
    environment = [
      { name = "ARTIFACTS_BUCKET", value = var.artifacts_bucket_name }
    ]
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = var.log_group_inference_name,
        awslogs-region        = var.region,
        awslogs-stream-prefix = "ecs"
      }
    }
  }]
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name_prefix}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.backend_cpu)
  memory                   = tostring(var.backend_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn
  container_definitions    = jsonencode(local.backend_container)
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.name_prefix}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.frontend_cpu)
  memory                   = tostring(var.frontend_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn
  container_definitions    = jsonencode(local.frontend_container)
}

resource "aws_ecs_task_definition" "inference" {
  family                   = "${var.name_prefix}-inference"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.inference_cpu)
  memory                   = tostring(var.inference_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn
  container_definitions    = jsonencode(local.inference_container)
}

resource "aws_ecs_service" "backend" {
  name            = "${var.name_prefix}-backend"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_backend_arn
    container_name   = "backend"
    container_port   = var.backend_container_port
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60
  enable_execute_command             = true
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.name_prefix}-frontend"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_frontend_arn
    container_name   = "frontend"
    container_port   = var.frontend_container_port
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60
  enable_execute_command             = true
}

resource "aws_ecs_service" "inference" {
  name            = "${var.name_prefix}-inference"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.inference.arn
  desired_count   = var.inference_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  enable_execute_command             = true
}
