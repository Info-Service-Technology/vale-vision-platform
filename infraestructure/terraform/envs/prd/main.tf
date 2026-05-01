locals {
  backend_container_port   = 8000
  inference_container_port = 8080

  db_endpoint = var.create_dedicated_rds ? module.rds[0].endpoint : var.existing_db_endpoint
  db_port     = var.create_dedicated_rds ? module.rds[0].port : var.existing_db_port

  db_secret_arn    = var.create_dedicated_rds ? module.secrets.db_secret_arn : var.existing_db_secret_arn
  ecs_cluster_arn  = var.create_ecs_cluster ? module.ecs_cluster[0].cluster_arn : var.ecs_cluster_arn
  ecs_cluster_name = var.create_ecs_cluster ? module.ecs_cluster[0].cluster_name : var.ecs_cluster_name
}

module "ecr" {
  source      = "../../modules/ecr"
  name_prefix = var.name_prefix
}

module "artifacts" {
  source      = "../../modules/s3"
  name_prefix = var.name_prefix
}

module "logs" {
  source      = "../../modules/logs"
  name_prefix = var.name_prefix
}

module "ecs_cluster" {
  count                     = var.create_ecs_cluster ? 1 : 0
  source                    = "../../modules/ecs_cluster"
  name_prefix               = var.name_prefix
  enable_container_insights = var.enable_ecs_container_insights
}

module "security" {
  source           = "../../modules/security"
  name_prefix      = var.name_prefix
  vpc_id           = var.vpc_id
  shared_alb_sg_id = var.shared_alb_sg_id
}

module "secrets" {
  source                   = "../../modules/secrets"
  name_prefix              = var.name_prefix
  db_name                  = var.db_name
  db_username              = var.db_username
  db_password              = var.db_password
  existing_db_secret_arn   = var.existing_db_secret_arn
  create_db_secret         = var.create_dedicated_rds
  smtp_password            = var.smtp_password
  existing_smtp_secret_arn = var.existing_smtp_secret_arn
  create_smtp_secret       = var.create_smtp_secret
}

module "rds" {
  count              = var.create_dedicated_rds ? 1 : 0
  source             = "../../modules/rds"
  name_prefix        = var.name_prefix
  vpc_id             = var.vpc_id
  private_subnet_ids = var.private_subnet_ids
  security_group_id  = module.security.rds_sg_id
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
  db_instance_class  = var.db_instance_class
  allocated_storage  = var.db_allocated_storage
  engine_version     = var.db_engine_version
}

module "alb_app" {
  source                    = "../../modules/alb_app"
  name_prefix               = var.name_prefix
  vpc_id                    = var.vpc_id
  listener_arn              = var.alb_https_listener_arn
  backend_host              = var.backend_host
  frontend_host             = var.frontend_host
  frontend_redirect_hosts   = var.frontend_redirect_hosts
  backend_container_port    = local.backend_container_port
  health_check_path_backend = "/api/health"
}

module "ecs_app" {
  source                    = "../../modules/ecs_app"
  name_prefix               = var.name_prefix
  region                    = var.aws_region
  cluster_arn               = local.ecs_cluster_arn
  cluster_name              = local.ecs_cluster_name
  private_subnet_ids        = var.private_subnet_ids
  ecs_security_group_id     = module.security.ecs_sg_id
  target_group_backend_arn  = module.alb_app.backend_target_group_arn
  ecr_backend_url           = module.ecr.backend_repository_url
  ecr_inference_url         = module.ecr.inference_repository_url
  backend_image_tag         = var.backend_image_tag
  inference_image_tag       = var.inference_image_tag
  backend_cpu               = var.backend_cpu
  backend_memory            = var.backend_memory
  inference_cpu             = var.inference_cpu
  inference_memory          = var.inference_memory
  backend_desired_count     = var.backend_desired_count
  inference_desired_count   = var.inference_desired_count
  backend_container_port    = local.backend_container_port
  inference_container_port  = local.inference_container_port
  log_group_backend_name    = module.logs.backend_log_group_name
  log_group_inference_name  = module.logs.inference_log_group_name
  artifacts_bucket_name     = module.artifacts.bucket_name
  db_host                   = local.db_endpoint
  db_port                   = local.db_port
  db_name                   = var.db_name
  db_secret_arn             = local.db_secret_arn
  smtp_secret_arn           = module.secrets.smtp_secret_arn
  frontend_public_url       = var.frontend_public_url
  api_public_url            = var.api_public_url
  email_enabled             = var.email_enabled
  email_from_name           = var.email_from_name
  email_from_address        = var.email_from_address
  email_reply_to            = var.email_reply_to
  email_support_address     = var.email_support_address
  email_debug_return_tokens = var.email_debug_return_tokens
  smtp_host                 = var.smtp_host
  smtp_port                 = var.smtp_port
  smtp_username             = var.smtp_username
  smtp_use_starttls         = var.smtp_use_starttls
  smtp_use_ssl              = var.smtp_use_ssl
  smtp_timeout_seconds      = var.smtp_timeout_seconds
}

resource "aws_route53_record" "frontend" {
  for_each = {
    for record in [{ zone_id = var.primary_hosted_zone_id, name = var.frontend_host }] :
    "${record.zone_id}:${record.name}" => record
  }

  zone_id = each.value.zone_id
  name    = each.value.name
  type    = "A"
  allow_overwrite = true

  alias {
    name                   = module.alb_app.alb_dns_name
    zone_id                = module.alb_app.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "frontend_redirect" {
  for_each = {
    for record in var.frontend_dns_records : "${record.zone_id}:${record.name}" => record
  }

  zone_id = each.value.zone_id
  name    = each.value.name
  type    = "A"
  allow_overwrite = true

  alias {
    name                   = module.alb_app.alb_dns_name
    zone_id                = module.alb_app.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "backend" {
  for_each = {
    for record in concat(
      [{ zone_id = var.primary_hosted_zone_id, name = var.backend_host }],
      var.backend_dns_records
    ) : "${record.zone_id}:${record.name}" => record
  }

  zone_id = each.value.zone_id
  name    = each.value.name
  type    = "A"
  allow_overwrite = true

  alias {
    name                   = module.alb_app.alb_dns_name
    zone_id                = module.alb_app.alb_zone_id
    evaluate_target_health = true
  }
}

module "github_oidc" {
  count       = var.enable_github_oidc ? 1 : 0
  source      = "../../modules/github_oidc"
  role_name   = "${var.name_prefix}-github-actions-role"
  github_org  = var.github_org
  github_repo = var.github_repo
  ecr_repository_arns = [
    module.ecr.backend_repository_arn,
    module.ecr.inference_repository_arn,
  ]
  ecs_cluster_arns = [module.ecs_app.cluster_arn]
  ecs_service_arns = [
    module.ecs_app.backend_service_arn,
    module.ecs_app.inference_service_arn,
  ]
  allow_terraform_apply = true
}
