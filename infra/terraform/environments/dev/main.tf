terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstatepaymentfraud"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

locals {
  tags = {
    Environment = var.environment
    Project     = "payment-fraud-detection"
    Owner       = "hemant"
    ManagedBy   = "terraform"
  }
}

module "resource_group" {
  source   = "../../modules/resource-group"
  name     = "payment-fraud-${var.environment}-rg"
  location = var.location
  tags     = local.tags
}

module "fraud_scorer" {
  source              = "../../modules/container-app"
  name                = "fraud-scorer-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  container_image     = var.fraud_scorer_image
  target_port         = 8001
  tags                = local.tags
  min_replicas        = 1

  environment_variables = {}
}


module "transaction_api" {
  source              = "../../modules/container-app"
  name                = "transaction-api-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  container_image     = var.transaction_api_image
  target_port         = 8000
  tags                = local.tags

  environment_variables = {
    API_KEY          = var.api_key
    FRAUD_SCORER_URL = module.fraud_scorer.url
  }
}
