# Beispiel-Terraform-Umgebung. Dient als Vorlage für `task terraform:bootstrap-env`.
# Nutzt den STACKIT-Provider exemplarisch.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    stackit = {
      source  = "stackitcloud/stackit"
      version = "~> 0.40"
    }
  }
  # Backend bewusst auskommentiert - pro Umgebung im backend.tf konfigurieren.
  # backend "s3" { ... }
}

provider "stackit" {
  default_region = var.region
}

variable "project_id" {
  description = "STACKIT Project ID"
  type        = string
}

variable "region" {
  type    = string
  default = "eu01"
}

# TODO: Ressourcen ergänzen.
output "project_id" {
  value = var.project_id
}
