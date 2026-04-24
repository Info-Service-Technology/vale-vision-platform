resource "aws_ecr_repository" "backend" {
  name                 = "${var.name_prefix}/backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.name_prefix}/frontend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_repository" "inference" {
  name                 = "${var.name_prefix}/inference"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}
