locals {
  backend_container_port   = 8000
  frontend_container_port  = 5174
  inference_container_port = 8080

  db_endpoint = var.create_dedicated_rds ? module.rds[0].endpoint : var.existing_db_endpoint
  db_port     = var.create_dedicated_rds ? module.rds[0].port : var.existing_db_port

  db_secret_arn = var.create_dedicated_rds ? module.secrets.db_secret_arn : var.existing_db_secret_arn
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

module "security" {
  source           = "../../modules/security"
  name_prefix      = var.name_prefix
  vpc_id           = var.vpc_id
  shared_alb_sg_id = var.shared_alb_sg_id
}

module "secrets" {
  source                = "../../modules/secrets"
  name_prefix           = var.name_prefix
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = var.db_password
  existing_db_secret_arn = var.existing_db_secret_arn
  create_db_secret      = var.create_dedicated_rds
}

module "rds" {
  count               = var.create_dedicated_rds ? 1 : 0
  source              = "../../modules/rds"
  name_prefix         = var.name_prefix
  vpc_id              = var.vpc_id
  private_subnet_ids  = var.private_subnet_ids
  security_group_id   = module.security.rds_sg_id
  db_name             = var.db_name
  db_username         = var.db_username
  db_password         = var.db_password
  db_instance_class   = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  engine_version      = var.db_engine_version
}

module "alb_app" {
  source                    = "../../modules/alb_app"
  name_prefix               = var.name_prefix
  vpc_id                    = var.vpc_id
  listener_arn              = var.alb_https_listener_arn
  backend_host              = var.backend_host
  frontend_host             = var.frontend_host
  backend_container_port    = local.backend_container_port
  frontend_container_port   = local.frontend_container_port
  health_check_path_backend = "/health"
  health_check_path_frontend = "/"
}

module "ecs_app" {
  source                   = "../../modules/ecs_app"
  name_prefix              = var.name_prefix
  region                   = var.aws_region
  cluster_arn              = var.ecs_cluster_arn
  cluster_name             = var.ecs_cluster_name
  private_subnet_ids       = var.private_subnet_ids
  ecs_security_group_id    = module.security.ecs_sg_id
  target_group_backend_arn = module.alb_app.backend_target_group_arn
  target_group_frontend_arn = module.alb_app.frontend_target_group_arn
  ecr_backend_url          = module.ecr.backend_repository_url
  ecr_frontend_url         = module.ecr.frontend_repository_url
  ecr_inference_url        = module.ecr.inference_repository_url
  backend_image_tag        = var.backend_image_tag
  frontend_image_tag       = var.frontend_image_tag
  inference_image_tag      = var.inference_image_tag
  backend_cpu              = var.backend_cpu
  backend_memory           = var.backend_memory
  frontend_cpu             = var.frontend_cpu
  frontend_memory          = var.frontend_memory
  inference_cpu            = var.inference_cpu
  inference_memory         = var.inference_memory
  backend_desired_count    = var.backend_desired_count
  frontend_desired_count   = var.frontend_desired_count
  inference_desired_count  = var.inference_desired_count
  backend_container_port   = local.backend_container_port
  frontend_container_port  = local.frontend_container_port
  inference_container_port = local.inference_container_port
  log_group_backend_name   = module.logs.backend_log_group_name
  log_group_frontend_name  = module.logs.frontend_log_group_name
  log_group_inference_name = module.logs.inference_log_group_name
  artifacts_bucket_name    = module.artifacts.bucket_name
  db_host                  = local.db_endpoint
  db_port                  = local.db_port
  db_name                  = var.db_name
  db_secret_arn            = local.db_secret_arn
  frontend_api_base_url    = var.frontend_api_base_url
}

resource "aws_route53_record" "frontend" {
  zone_id = var.hosted_zone_id
  name    = var.frontend_host
  type    = "CNAME"
  ttl     = 60
  records = [module.alb_app.alb_dns_name]
}

resource "aws_route53_record" "backend" {
  zone_id = var.hosted_zone_id
  name    = var.backend_host
  type    = "CNAME"
  ttl     = 60
  records = [module.alb_app.alb_dns_name]
}
