# DNS — one host per restaurant under the shared demo namespace (PRD-11 / SCRUM-52).
# `<slug>.demo.<domain_name>`, with /admin and /store served as PATHS on the same
# box (each restaurant is its own box, so paths are safe). Points at the box's
# Elastic IP. certbot issues a single-host Let's Encrypt cert via HTTP-01 — no
# wildcard needed, since each box serves exactly one hostname.
#
# At cutover to a customer's own domain, set var.fqdn to that domain.
data "aws_route53_zone" "main" {
  name         = "${var.domain_name}."
  private_zone = false
}

locals {
  fqdn = var.fqdn != "" ? var.fqdn : "${var.slug}.demo.${var.domain_name}"
}

resource "aws_route53_record" "app" {
  zone_id         = data.aws_route53_zone.main.zone_id
  name            = local.fqdn
  type            = "A"
  ttl             = 300
  allow_overwrite = true
  records         = [aws_eip.backend.public_ip]
}
