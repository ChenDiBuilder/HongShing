locals {
  demo_path = "/product-demo/hongshing"
}

# Frontend S3 bucket
resource "aws_s3_bucket" "frontend" {
  bucket = "${var.app_name}-frontend-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Assets S3 bucket
resource "aws_s3_bucket" "assets" {
  bucket = "${var.app_name}-assets-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront OAC for S3
resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.app_name}-frontend-oac-${var.environment}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_iam_policy_document" "cloudfront_oac" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.main.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.cloudfront_oac.json
}

# CloudFront Function — strips /product-demo/hongshing prefix from API paths before forwarding to ALB
resource "aws_cloudfront_function" "strip_api_prefix" {
  name    = "${var.app_name}-strip-demo-path-${var.environment}"
  runtime = "cloudfront-js-2.0"
  code    = file("${path.module}/cloudfront_function.js")
  publish = true
}

# CloudFront Function — append index.html to directory paths for S3
resource "aws_cloudfront_function" "directory_index" {
  name    = "${var.app_name}-directory-index-${var.environment}"
  runtime = "cloudfront-js-2.0"
  code    = file("${path.module}/cloudfront_directory_index.js")
  publish = true
}

# CloudFront distribution (default *.cloudfront.net cert — no custom domain needed)
resource "aws_cloudfront_distribution" "main" {
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "S3-${var.app_name}-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  origin {
    domain_name = data.aws_lb.vela.dns_name
    origin_id   = "ALB-${var.app_name}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  # SPA static files at /product-demo/hongshing/*
  default_cache_behavior {
    target_origin_id       = "S3-${var.app_name}-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.directory_index.arn
    }
  }

  # API proxy at /product-demo/hongshing/api/*
  ordered_cache_behavior {
    path_pattern           = "${local.demo_path}/api/*"
    target_origin_id       = "ALB-${var.app_name}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["Origin", "Authorization", "Content-Type", "Host"]
      cookies {
        forward = "all"
      }
    }

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.strip_api_prefix.arn
    }
  }

  # SPA fallback: 403/404 → /product-demo/hongshing/index.html
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "${local.demo_path}/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "${local.demo_path}/index.html"
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  price_class = "PriceClass_100"
}
