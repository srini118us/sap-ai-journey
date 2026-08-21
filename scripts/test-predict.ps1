# test-predict.ps1
# Smoke test for the deployed SAP AI Core supplier-prediction inference endpoint.
#
# Prerequisites:
#   - Serving deployment RUNNING in AI Core (from supplier-prediction-serve.yaml)
#   - AI Core service key from BTP cockpit (Instances -> AI Core -> Service Keys)
#   - Deployment URL from AI Launchpad -> ML Operations -> Deployments
#
# IMPORTANT: use SINGLE quotes for clientid and clientsecret in PowerShell.
#   Double quotes will silently mangle special characters ($, |, !) in
#   the XSUAA service-key values, producing 401 Unauthorized.

$clientid     = 'sb-<uuid>!b<num>|aicore!b<num>'   # from service key .clientid
$clientsecret = '<your-client-secret>'              # from service key .clientsecret
$xsuaa        = 'https://<subaccount>.authentication.<region>.hana.ondemand.com'  # from service key .url
$depurl       = 'https://api.ai.prod.<region>.aws.ml.hana.ondemand.com/v2/inference/deployments/<deploymentId>'
$rg           = 'myresourcegroup'                   # AI Core resource group

Write-Host "Step 1: getting OAuth token from XSUAA..."
try {
  $tok = (Invoke-RestMethod -Method Post -Uri "$xsuaa/oauth/token" `
    -Body @{grant_type='client_credentials'; client_id=$clientid; client_secret=$clientsecret}
  ).access_token
  Write-Host "Token OK, starts with:" $tok.Substring(0,15) "..."
} catch {
  Write-Host "TOKEN FAILED:" $_.Exception.Message
  Write-Host "-> Re-copy clientsecret from BTP service key (check for truncation)."
  exit 1
}

Write-Host "Step 2: calling /v2/predict (note: double /v2 is correct — AI Core gateway + FastAPI route)..."
try {
  $sample = @{
    vendor_category         = 'PACK'
    vendor_country          = 'US'
    historical_ontime_rate  = 0.86
    avg_lead_time_days      = 6.9
    lead_time_variance      = 3.57
    po_count_last_quarter   = 14
    po_amount               = 26062.92
    concurrent_pos          = 5
    material_complexity     = 4
    expected_lead_time_days = 8.8
    delivery_day_of_week    = 5
    is_quarter_end          = 1
    is_peak_season          = 1
  } | ConvertTo-Json -Compress

  $resp = Invoke-RestMethod -Method Post -Uri "$depurl/v2/predict" `
    -Headers @{Authorization="Bearer $tok"; 'AI-Resource-Group'=$rg} `
    -ContentType 'application/json' -Body $sample

  $resp | ConvertTo-Json -Depth 6
} catch {
  Write-Host "PREDICT FAILED:" $_.Exception.Message
  $r = $_.Exception.Response
  if ($r) {
    $reader = New-Object System.IO.StreamReader($r.GetResponseStream())
    Write-Host "Response body:" $reader.ReadToEnd()
  }
  exit 1
}
