variable "name" {
  type        = string
  description = "Container app name"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "container_image" {
  type        = string
  description = "Docker image to deploy"
}

variable "target_port" {
  type        = number
  description = "Port the container listens on"
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables for the container"
  default     = {}
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
}

variable "min_replicas" {
  type        = number
  description = "Minimum number of replicas"
  default     = 0
}

variable "max_replicas" {
  type        = number
  description = "Maximum number of replicas"
  default     = 1
}
