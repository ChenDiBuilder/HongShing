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

output "fqdn" {
  description = "The single host this box serves"
  value       = local.fqdn
}

output "hosts" {
  description = "URLs served by the box (admin/store are paths on the one host)"
  value = {
    customer = "https://${local.fqdn}/"
    admin    = "https://${local.fqdn}/admin/"
    store    = "https://${local.fqdn}/store/"
  }
}
