# ── IAM role for the box ──
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backend" {
  name               = "hongshing-backend"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

# SSM (shell without SSH) + ECR pull for the backend image.
resource "aws_iam_role_policy_attachment" "backend_ssm" {
  role       = aws_iam_role.backend.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "backend_ecr" {
  role       = aws_iam_role.backend.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# SNS publish — OTP, reward-confirmation, and order-link SMS.
resource "aws_iam_role_policy" "backend_sns" {
  name = "sns-publish"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sns:Publish"]
      Resource = "*"
    }]
  })
}

resource "aws_iam_instance_profile" "backend" {
  name = "hongshing-backend"
  role = aws_iam_role.backend.name
}

# ── Security group ──
resource "aws_security_group" "backend" {
  name        = "hongshing-backend"
  description = "HongShing single-box: web + SSH"

  ingress {
    description = "SSH (restricted)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_ingress_cidr
  }
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── Instance ──
# Amazon Linux 2023 ARM64 (matches the t4g/arm64 build).
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023*-kernel-6.1-arm64"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t4g.micro"
  iam_instance_profile   = aws_iam_instance_profile.backend.name
  vpc_security_group_ids = [aws_security_group.backend.id]
  key_name               = var.ssh_key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e
    exec > /var/log/user-data.log 2>&1
    yum update -y
    yum install -y docker cronie unzip certbot
    systemctl enable --now docker
    systemctl enable --now crond
    usermod -aG docker ec2-user
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscliv2.zip
    unzip -q /tmp/awscliv2.zip -d /tmp && /tmp/aws/install
    mkdir -p /opt/hongshing/backups /opt/hongshing/www
    echo "user-data complete — run deploy.sh to bring up the app"
  EOF
  )

  # Backup=true selects this box into the Bridgeway fleet DLM snapshot policy.
  # Declared here so this stack doesn't strip the tag the ops stack adds.
  tags = { Name = "hongshing-backend", Backup = "true" }

  # Same data-durability guardrails as the portal: most_recent AMI would
  # otherwise make a routine apply REPLACE the box and wipe the Postgres volume,
  # TLS cert, and .env. Absorb AMI/user_data drift; hard-block any destroy.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [ami, user_data]
  }
}

resource "aws_eip" "backend" {
  instance = aws_instance.backend.id
}
