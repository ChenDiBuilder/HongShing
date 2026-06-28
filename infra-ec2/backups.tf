# ── Off-box DB backups ──
# Versioned, private S3 bucket for nightly pg_dump uploads (backup.sh). The
# recovery path if the EBS volume / instance is lost.
resource "aws_s3_bucket" "db_backups" {
  bucket = "${var.slug}-db-backups-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "db_backups" {
  bucket                  = aws_s3_bucket.db_backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "db_backups" {
  bucket = aws_s3_bucket.db_backups.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "db_backups" {
  bucket = aws_s3_bucket.db_backups.id
  rule {
    id     = "expire-old-backups"
    status = "Enabled"
    filter {}
    expiration { days = 90 }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

# Instance role may upload backups (PutObject only — least privilege).
resource "aws_iam_role_policy" "backend_backup_s3" {
  name = "db-backup-s3"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.db_backups.arn}/*"
    }]
  })
}
