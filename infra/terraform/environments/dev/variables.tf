variable "location" {
  type    = string
  default = "centralus"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "transaction_api_image" {
  type        = string
  description = "Transaction API Docker image"
}

variable "fraud_scorer_image" {
  type        = string
  description = "Fraud Scorer Docker image"
}

variable "api_key" {
  type        = string
  sensitive   = true
  description = "API key for transaction service"
}

variable "fraud_scorer_url" {
  type        = string
  description = "Internal URL of fraud scorer service"
}
