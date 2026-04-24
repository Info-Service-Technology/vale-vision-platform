# Vale Vision Terraform

This stack provisions the Vale Vision application layer while allowing reuse of shared HDI platform resources.

## Modes
- Shared platform mode: reuse existing VPC, ECS cluster, ALB HTTPS listener, ACM/Route53.
- Dedicated DB mode: create a dedicated RDS MySQL instance for Vale Vision.

## Structure
- envs/dev: example environment wiring modules together
- modules/ecr: ECR repositories for backend/frontend/inference
- modules/s3: S3 bucket for artifacts
- modules/logs: CloudWatch log groups
- modules/secrets: Secrets Manager secrets
- modules/security: security groups for ECS, ALB and RDS
- modules/alb_app: target groups and listener rules on a shared ALB
- modules/ecs_app: task definitions, IAM roles and services
- modules/rds: optional dedicated RDS MySQL
