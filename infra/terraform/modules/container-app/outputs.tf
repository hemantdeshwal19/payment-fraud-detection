output "url" {
  value = "https://${azurerm_container_app.this.ingress[0].fqdn}"
}

output "name" {
  value = azurerm_container_app.this.name
}
