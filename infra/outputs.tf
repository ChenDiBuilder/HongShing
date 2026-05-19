output "vpc_id" {
  value = aws_vpc.main.id
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_customer_web_url" {
  value = aws_ecr_repository.customer_web.repository_url
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.main.id
}

output "demo_url" {
  value = "https://${aws_cloudfront_distribution.main.domain_name}/product-demo/hongshing/"
}

output "rds_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "s3_frontend_bucket" {
  value = aws_s3_bucket.frontend.id
}

output "s3_assets_bucket" {
  value = aws_s3_bucket.assets.id
}

output "sns_topic_arn" {
  value = aws_sns_topic.sms.arn
}
