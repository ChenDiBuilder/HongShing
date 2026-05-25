# Shared Vela VPC — HongShing deploys into Vela's infrastructure
data "aws_vpc" "vela" {
  filter {
    name   = "tag:Name"
    values = ["vela-vpc"]
  }
}

data "aws_subnets" "vela_public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.vela.id]
  }
  filter {
    name   = "tag:Name"
    values = ["vela-public-*"]
  }
}

data "aws_security_group" "vela_ecs" {
  filter {
    name   = "group-name"
    values = ["vela-ecs-*"]
  }
  vpc_id = data.aws_vpc.vela.id
}

data "aws_lb" "vela" {
  name = "vela-alb"
}

data "aws_lb_listener" "vela_https" {
  load_balancer_arn = data.aws_lb.vela.arn
  port              = 443
}

data "aws_lb_listener" "vela_http" {
  load_balancer_arn = data.aws_lb.vela.arn
  port              = 80
}
