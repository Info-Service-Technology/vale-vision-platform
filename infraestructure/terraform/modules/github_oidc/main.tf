data "aws_iam_openid_connect_provider" "github_existing" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  count = length(try(data.aws_iam_openid_connect_provider.github_existing.arn, "")) == 0 ? 1 : 0

  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]
}

locals {
  github_oidc_provider_arn = try(
    data.aws_iam_openid_connect_provider.github_existing.arn,
    aws_iam_openid_connect_provider.github[0].arn
  )
}

resource "aws_iam_role" "github_actions" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "github_actions" {
  name = "${var.role_name}-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "ECRAuth"
          Effect = "Allow"
          Action = [
            "ecr:GetAuthorizationToken"
          ]
          Resource = "*"
        }
      ],
      length(var.ecr_repository_arns) > 0 ? [
        {
          Sid    = "ECRPush"
          Effect = "Allow"
          Action = [
            "ecr:BatchCheckLayerAvailability",
            "ecr:CompleteLayerUpload",
            "ecr:UploadLayerPart",
            "ecr:InitiateLayerUpload",
            "ecr:PutImage",
            "ecr:BatchGetImage"
          ]
          Resource = var.ecr_repository_arns
        }
      ] : [],
      length(var.ecs_service_arns) > 0 ? [
        {
          Sid    = "ECSDeploy"
          Effect = "Allow"
          Action = [
            "ecs:UpdateService",
            "ecs:DescribeServices"
          ]
          Resource = var.ecs_service_arns
        }
      ] : [],
      length(var.ecs_cluster_arns) > 0 ? [
        {
          Sid    = "ECSDescribeCluster"
          Effect = "Allow"
          Action = [
            "ecs:DescribeClusters"
          ]
          Resource = var.ecs_cluster_arns
        }
      ] : [],
      var.allow_terraform_apply ? [
        {
          Sid    = "TerraformInfraReadWrite"
          Effect = "Allow"
          Action = [
            "acm:*",
            "application-autoscaling:*",
            "cloudwatch:*",
            "ec2:*",
            "ecs:*",
            "elasticloadbalancing:*",
            "ecr:*",
            "events:*",
            "iam:GetRole",
            "iam:PassRole",
            "iam:CreateRole",
            "iam:DeleteRole",
            "iam:AttachRolePolicy",
            "iam:DetachRolePolicy",
            "iam:PutRolePolicy",
            "iam:DeleteRolePolicy",
            "iam:TagRole",
            "iam:UntagRole",
            "iam:CreateOpenIDConnectProvider",
            "iam:GetOpenIDConnectProvider",
            "iam:DeleteOpenIDConnectProvider",
            "iam:CreatePolicy",
            "iam:DeletePolicy",
            "iam:GetPolicy",
            "iam:GetPolicyVersion",
            "iam:ListAttachedRolePolicies",
            "iam:ListRolePolicies",
            "iam:ListOpenIDConnectProviders",
            "logs:*",
            "rds:*",
            "route53:*",
            "s3:*",
            "secretsmanager:*"
          ]
          Resource = "*"
        }
      ] : []
    )
  })
}

resource "aws_iam_role_policy_attachment" "github_actions_attach" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions.arn
}
