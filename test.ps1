$body = @{ email = "test@gmail.com"; password = "margurite" } | ConvertTo-Json
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/login" -Method Post -Body $body -ContentType "application/json"
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token" }

Write-Host "--- GENERATE REPORT (xlsx, strategique) ---"
$reportBody = @{ type = "Stratégique"; zones = "all"; format = "xlsx" } | ConvertTo-Json
$report = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/reports/generate" -Method Post -Body $reportBody -ContentType "application/json" -Headers $headers
$report | ConvertTo-Json
$reportId = $report.report_id

Write-Host "--- Pause 2 secondes pour laisser le job finir ---"
Start-Sleep -Seconds 2

Write-Host "--- LIST REPORTS ---"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/reports" -Headers $headers | ConvertTo-Json -Depth 5

Write-Host "--- DOWNLOAD REPORT (verification fichier) ---"
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/reports/$reportId/download" -Headers $headers -OutFile "rapport_test.xlsx"
Write-Host "Fichier telecharge : rapport_test.xlsx"

Write-Host "--- NOTIFICATIONS ---"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/notifications" -Headers $headers | ConvertTo-Json -Depth 5