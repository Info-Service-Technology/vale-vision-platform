aws_region  = "sa-east-1"
environment = "prd"
name_prefix = "sansx-vision-prd"

# Shared platform
vpc_id                        = "vpc-0822f063050b009b0"
private_subnet_ids            = ["subnet-0d906b6d7d3a10755", "subnet-07bbbcfff0a872b63"]
public_subnet_ids             = ["subnet-00c18bdff943e6739", "subnet-09a6b42e058d1f499"]
create_ecs_cluster            = true
enable_ecs_container_insights = true
alb_https_listener_arn        = "arn:aws:elasticloadbalancing:sa-east-1:913524918638:listener/app/hdi-dashboard-prod-alb/b00fe8f69b876f8c/a8532763e8c9d77e"
shared_alb_sg_id              = "sg-0c5064c1218639ab8"
primary_hosted_zone_id        = "Z0778600DOW4YCR27BKI"
secondary_hosted_zone_id      = null

# Domains
frontend_host = "sensxvisionplatform.com"
backend_host  = "api.sensxvisionplatform.com"
frontend_redirect_hosts = [
  "www.sensxvisionplatform.com"
]

frontend_dns_records = [
  { zone_id = "Z0778600DOW4YCR27BKI", name = "www.sensxvisionplatform.com" }
]

backend_dns_records = []

# DB strategy
create_dedicated_rds = true
db_name              = "vale_vision"
db_username          = "sansxvision_app"
db_engine_version    = "8.0.45"
# db_password: prefer passing by environment variable TF_VAR_db_password

# SMTP and transactional email
create_smtp_secret = true
# smtp_password: prefer passing by environment variable TF_VAR_smtp_password
smtp_username         = "mauroslucios@gmail.com"
email_from_address    = "mauroslucios@gmail.com"
email_reply_to        = "mauroslucios@gmail.com"
email_support_address = "mauroslucios@gmail.com"
frontend_public_url   = "https://sensxvisionplatform.com"
api_public_url        = "https://api.sensxvisionplatform.com"
image_source_buckets  = ["vale-vision-artifacts-dev", "vale-vision-raw-dev", "vale-vision-debug-dev"]
sqs_queue_url         = "https://sqs.sa-east-1.amazonaws.com/913524918638/sansx-vision-prd-inference-queue"

# ECS image tags
backend_image_tag           = "latest"
inference_image_tag         = "v5"
inference_desired_count     = 0
inference_gpu_desired_count = 1

# GitHub OIDC
enable_github_oidc = true
github_org         = "Info-Service-Technology"
github_repo        = "vale-vision-platform"
