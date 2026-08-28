$clientid     = '<AICORE_CLIENT_ID>'
$clientsecret = '<AICORE_CLIENT_SECRET>'
$xsuaa = "https://ai-core-us.authentication.us10.hana.ondemand.com"
$depurl = "https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com/v2/inference/deployments/dd779af933dbd298"

Write-Host "Step 1: getting token..."
try {
  $tok = (Invoke-RestMethod -Method Post -Uri "$xsuaa/oauth/token" `
    -Body @{grant_type="client_credentials"; client_id=$clientid; client_secret=$clientsecret}).access_token
  Write-Host "Token OK, starts with:" $tok.Substring(0,15)
} catch {
  Write-Host "TOKEN FAILED:" $_.Exception.Message
  Write-Host "-> The clientsecret is probably wrong/truncated. Re-copy it from the BTP service key."
  exit
}

Write-Host "Step 2: calling /v2/predict..."
try {
  $r = Invoke-RestMethod -Method Post -Uri "$depurl/v2/predict" `
    -Headers @{Authorization="Bearer $tok"; "AI-Resource-Group"="myresourcegroup"} `
    -ContentType "application/json" `
    -Body '{"vendor_category":"PACK","vendor_country":"US","historical_ontime_rate":0.86,"avg_lead_time_days":6.9,"lead_time_variance":3.57,"po_count_last_quarter":14,"po_amount":26062.92,"concurrent_pos":5,"material_complexity":4,"expected_lead_time_days":8.8,"delivery_day_of_week":5,"is_quarter_end":1,"is_peak_season":1}'
  $r | ConvertTo-Json -Depth 5
} catch {
  Write-Host "PREDICT FAILED:" $_.Exception.Message
}