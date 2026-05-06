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
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = compact([var.db_secret_arn, var.smtp_secret_arn])
      }
    ]
  })
}

resource "aws_iam_role" "task_role" {
  name               = "${var.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

locals {
  readable_bucket_names = distinct(concat([var.artifacts_bucket_name], var.image_source_buckets))
  readable_bucket_arns  = [for bucket in local.readable_bucket_names : "arn:aws:s3:::${bucket}"]
  readable_object_arns  = [for bucket in local.readable_bucket_names : "arn:aws:s3:::${bucket}/*"]

  backend_container = [{
    name         = "backend"
    image        = "${var.ecr_backend_url}:${var.backend_image_tag}"
    essential    = true
    portMappings = [{ containerPort = var.backend_container_port, hostPort = var.backend_container_port, protocol = "tcp" }]
    environment = [
      { name = "APP_NAME", value = "vale-vision-backend" },
      { name = "MYSQL_HOST", value = coalesce(var.db_host, "") },
      { name = "MYSQL_PORT", value = tostring(var.db_port) },
      { name = "MYSQL_DB", value = var.db_name },
      { name = "MYSQL_USER", value = var.db_username },
      { name = "ARTIFACTS_BUCKET", value = var.artifacts_bucket_name },
      { name = "FRONTEND_PUBLIC_URL", value = var.frontend_public_url },
      { name = "API_PUBLIC_URL", value = var.api_public_url },
      { name = "EMAIL_ENABLED", value = tostring(var.email_enabled) },
      { name = "EMAIL_FROM_NAME", value = var.email_from_name },
      { name = "EMAIL_FROM_ADDRESS", value = var.email_from_address },
      { name = "EMAIL_REPLY_TO", value = coalesce(var.email_reply_to, "") },
      { name = "EMAIL_SUPPORT_ADDRESS", value = coalesce(var.email_support_address, "") },
      { name = "EMAIL_DEBUG_RETURN_TOKENS", value = tostring(var.email_debug_return_tokens) },
      { name = "SMTP_HOST", value = var.smtp_host },
      { name = "SMTP_PORT", value = tostring(var.smtp_port) },
      { name = "SMTP_USERNAME", value = var.smtp_username },
      { name = "SMTP_USE_STARTTLS", value = tostring(var.smtp_use_starttls) },
      { name = "SMTP_USE_SSL", value = tostring(var.smtp_use_ssl) },
      { name = "SMTP_TIMEOUT_SECONDS", value = tostring(var.smtp_timeout_seconds) }
    ]
    secrets = concat(
      var.db_secret_arn != null ? [{
        name      = "MYSQL_PASSWORD"
        valueFrom = "${var.db_secret_arn}:password::"
      }] : [],
      var.smtp_secret_arn != null ? [{
        name      = "SMTP_PASSWORD"
        valueFrom = var.smtp_secret_arn
      }] : []
    )
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = var.log_group_backend_name,
        awslogs-region        = var.region,
        awslogs-stream-prefix = "ecs"
      }
    }
  }]

  inference_container = [{
    name         = "inference"
    image        = "${var.ecr_inference_url}:${var.inference_image_tag}"
    essential    = true
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

  inference_gpu_container = [{
    name         = "inference"
    image        = "${var.ecr_inference_url}:${var.inference_image_tag}"
    essential    = true
    portMappings = [{ containerPort = var.inference_container_port, hostPort = var.inference_container_port, protocol = "tcp" }]

    environment = [
      { name = "AWS_REGION", value = var.region },
      { name = "SQS_QUEUE_URL", value = var.sqs_queue_url },
      { name = "DB_HOST", value = coalesce(var.db_host, "") },
      { name = "DB_PORT", value = tostring(var.db_port) },
      { name = "DB_USER", value = var.db_username },
      { name = "DB_NAME", value = var.db_name },
      { name = "S3_BUCKET", value = "vale-vision-artifacts-dev" },
      { name = "S3_PREFIX_RAW", value = "raw/" },
      { name = "S3_PREFIX_PROCESSED", value = "processed/" },
      { name = "S3_PREFIX_RESOLVED", value = "resolved/" },
      { name = "TENANT", value = "vale" },
      { name = "CAMERA_NAME", value = "cam01" },
      { name = "CONFIDENCE_THRESHOLD", value = "0.4" },
      { name = "FILL_ALERT_THRESHOLD", value = "75" },
      { name = "CONTAMINATION_ALERT_THRESHOLD", value = "5" }
    ]

    resourceRequirements = [
      {
        type  = "GPU"
        value = "1"
      }
    ]

    secrets = var.db_secret_arn != null ? [{
      name      = "DB_PASSWORD"
      valueFrom = "${var.db_secret_arn}:password::"
    }] : []

    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = var.log_group_inference_name,
        awslogs-region        = var.region,
        awslogs-stream-prefix = "ecs-gpu"
      }
    }
  }]
}

resource "aws_iam_role_policy" "task_access" {
  name = "${var.name_prefix}-task-access"
  role = aws_iam_role.task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = local.readable_bucket_arns
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = local.readable_object_arns
      },
      {
        Effect = "Allow"
        Action = ["s3:PutObject"]
        Resource = [
          "arn:aws:s3:::${var.artifacts_bucket_name}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = compact([var.db_secret_arn, var.smtp_secret_arn])
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
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

resource "aws_ecs_task_definition" "inference_gpu" {
  family                   = "${var.name_prefix}-inference-gpu"
  network_mode             = "awsvpc"
  requires_compatibilities = ["EC2"]
  cpu                      = tostring(var.inference_cpu)
  memory                   = tostring(var.inference_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn
  container_definitions    = jsonencode(local.inference_gpu_container)
}

resource "aws_ecs_service" "backend" {
  name            = "${var.name_prefix}-backend"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
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

resource "aws_ecs_service" "inference" {
  name            = "${var.name_prefix}-inference"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.inference.arn
  desired_count   = var.inference_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  enable_execute_command             = true
}

resource "aws_ecs_service" "inference_gpu" {
  name            = "${var.name_prefix}-inference-gpu"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.inference_gpu.arn
  desired_count = var.inference_gpu_desired_count

  capacity_provider_strategy {
    capacity_provider = var.inference_capacity_provider_name
    weight            = 1
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  enable_execute_command             = true
}