terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "CHANGE-ME-tfstate"
    key          = "vale-vision/dev/terraform.tfstate"
    region       = "sa-east-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "vale-vision"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
