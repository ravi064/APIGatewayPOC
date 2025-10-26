# Keycloak Client Secret Rotation Script (PowerShell)
# This script helps rotate client secrets in Keycloak

param(
    [string]$KeycloakUrl = "http://localhost:8180",
    [string]$Realm = "api-gateway-poc",
    [string]$AdminUser = "admin",
    [string]$AdminPassword = "admin"
)

# Configuration
$ErrorActionPreference = "Stop"

Write-Host "=== Keycloak Client Secret Rotation Tool ===" -ForegroundColor Green
Write-Host ""

# Function to generate a secure random secret
function Generate-Secret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    return [Convert]::ToBase64String($bytes) -replace '[+/=]',''| Select-Object -First 32
}

# Function to get admin token
function Get-AdminToken {
    Write-Host "Getting admin access token..." -ForegroundColor Yellow
    
    $body = @{
    username = $AdminUser
     password = $AdminPassword
        grant_type = "password"
        client_id = "admin-cli"
  }
    
    try {
        $response = Invoke-RestMethod -Uri "$KeycloakUrl/realms/master/protocol/openid-connect/token" `
            -Method Post `
            -Body $body `
    -ContentType "application/x-www-form-urlencoded"
        
        return $response.access_token
    }
    catch {
   Write-Host "Failed to get admin token. Check credentials." -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}

# Function to get client UUID
function Get-ClientUUID {
    param(
        [string]$ClientId,
        [string]$Token
    )
    
    $headers = @{
        Authorization = "Bearer $Token"
    }
    
    try {
        $clients = Invoke-RestMethod -Uri "$KeycloakUrl/admin/realms/$Realm/clients" `
            -Method Get `
  -Headers $headers
        
    $client = $clients | Where-Object { $_.clientId -eq $ClientId }
        
        if (-not $client) {
  Write-Host "Client '$ClientId' not found" -ForegroundColor Red
        exit 1
        }
        
        return $client.id
    }
    catch {
        Write-Host "Failed to get client UUID" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
      exit 1
    }
}

# Function to update client secret
function Update-ClientSecret {
    param(
        [string]$ClientId,
        [string]$NewSecret,
        [string]$Token
    )
    
    Write-Host "Updating secret for client: $ClientId" -ForegroundColor Yellow
    
    $uuid = Get-ClientUUID -ClientId $ClientId -Token $Token
    
    $headers = @{
        Authorization = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    
 $body = @{
        type = "secret"
        value = $NewSecret
  } | ConvertTo-Json
  
    try {
        Invoke-RestMethod -Uri "$KeycloakUrl/admin/realms/$Realm/clients/$uuid/client-secret" `
            -Method Post `
            -Headers $headers `
       -Body $body | Out-Null
   
    Write-Host "COMPLETE: Secret updated for $ClientId" -ForegroundColor Green
    }
    catch {
Write-Host "Failed to update secret" -ForegroundColor Red
Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}

# Function to display menu
function Show-Menu {
    Write-Host ""
    Write-Host "Select an option:"
    Write-Host "1) Rotate api-gateway secret"
    Write-Host "2) Rotate customer-service secret"
    Write-Host "3) Rotate product-service secret"
    Write-Host "4) Rotate ALL confidential client secrets"
 Write-Host "5) Generate secure secret (display only)"
    Write-Host "6) Exit"
    Write-Host ""
}

# Function to rotate specific client
function Rotate-Client {
    param([string]$ClientId)
    
    $token = Get-AdminToken
    $newSecret = Generate-Secret
    
    Update-ClientSecret -ClientId $ClientId -NewSecret $newSecret -Token $token
    
    Write-Host ""
    Write-Host "=== New Secret ===" -ForegroundColor Green
    Write-Host "Client: $ClientId" -ForegroundColor Yellow
    Write-Host "Secret: $newSecret" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Save this secret! Update your environment variables:" -ForegroundColor Yellow
    Write-Host ""
    
    switch ($ClientId) {
 "api-gateway" {
     Write-Host "API_GATEWAY_CLIENT_SECRET=$newSecret"
        }
    "customer-service" {
     Write-Host "CUSTOMER_SERVICE_CLIENT_SECRET=$newSecret"
        }
    "product-service" {
       Write-Host "PRODUCT_SERVICE_CLIENT_SECRET=$newSecret"
        }
    }
    
    Write-Host ""
}

# Function to rotate all clients
function Rotate-AllClients {
    Write-Host "Rotating ALL confidential client secrets..." -ForegroundColor Yellow
    Write-Host ""
    
    $token = Get-AdminToken
    
    # api-gateway
    $gatewaySecret = Generate-Secret
    Update-ClientSecret -ClientId "api-gateway" -NewSecret $gatewaySecret -Token $token
    
    # customer-service
    $customerSecret = Generate-Secret
    Update-ClientSecret -ClientId "customer-service" -NewSecret $customerSecret -Token $token
    
    # product-service
    $productSecret = Generate-Secret
 Update-ClientSecret -ClientId "product-service" -NewSecret $productSecret -Token $token
    
    Write-Host ""
    Write-Host "=== All Secrets Rotated ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Copy these to your .env file:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "API_GATEWAY_CLIENT_SECRET=$gatewaySecret"
    Write-Host "CUSTOMER_SERVICE_CLIENT_SECRET=$customerSecret"
    Write-Host "PRODUCT_SERVICE_CLIENT_SECRET=$productSecret"
    Write-Host ""
    Write-Host "IMPORTANT: Restart all services after updating environment variables!" -ForegroundColor Red
    Write-Host ""
}

# Main menu loop
while ($true) {
    Show-Menu
    $choice = Read-Host "Enter choice [1-6]"
    
    switch ($choice) {
        "1" { Rotate-Client -ClientId "api-gateway" }
        "2" { Rotate-Client -ClientId "customer-service" }
        "3" { Rotate-Client -ClientId "product-service" }
  "4" { Rotate-AllClients }
        "5" {
       $secret = Generate-Secret
            Write-Host ""
   Write-Host "Generated secure secret:" -ForegroundColor Green
            Write-Host $secret
         Write-Host ""
     }
     "6" {
         Write-Host "Exiting..."
            exit 0
        }
        default {
 Write-Host "Invalid option. Please try again." -ForegroundColor Red
   }
    }
}
