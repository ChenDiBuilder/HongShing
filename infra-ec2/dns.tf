# ── DNS ──
# Subdomains in the EXISTING bridgewayinnovations.ca zone (looked up, not
# created). All point at the box's Elastic IP; nginx routes by host and certbot
# issues a single Let's Encrypt cert covering all three names.
data "aws_route53_zone" "main" {
  name         = "${var.domain_name}."
  private_zone = false
}

locals {
  host_customer = "${var.subdomain}.${var.domain_name}"       # signup landing
  host_admin    = "admin.${var.subdomain}.${var.domain_name}" # dashboard
  host_store    = "store.${var.subdomain}.${var.domain_name}" # storefront (future)
  all_hosts     = [local.host_customer, local.host_admin, local.host_store]
}

resource "aws_route53_record" "app" {
  for_each        = toset(local.all_hosts)
  zone_id         = data.aws_route53_zone.main.zone_id
  name            = each.value
  type            = "A"
  ttl             = 300
  allow_overwrite = true
  records         = [aws_eip.backend.public_ip]
}
