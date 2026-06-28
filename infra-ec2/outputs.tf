output "ec2_public_ip" {
  description = "Elastic IP of the box (point DNS / SSH here)"
  value       = aws_eip.backend.public_ip
}

output "ec2_instance_id" {
  description = "Instance id (deploy.sh / start-stop schedule use this)"
  value       = aws_instance.backend.id
}

output "ecr_repository_url" {
  description = "ECR repo URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "backup_bucket" {
  description = "Off-box DB backup bucket"
  value       = aws_s3_bucket.db_backups.id
}

output "hosts" {
  description = "Hostnames served by the box"
  value = {
    customer = local.host_customer
    admin    = local.host_admin
    store    = local.host_store
  }
}
