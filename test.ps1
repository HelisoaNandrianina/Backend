$body = @{ email = "test@gmail.com"; password = "margurite" } | ConvertTo-Json
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/login" -Method Post -Body $body -ContentType "application/json"
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token" }
Write-Host "--- GENERATE ANALYSIS ---"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/decision/generate-analysis" -Method Post -Headers $headers | ConvertTo-Json
Write-Host "--- RANKING ---"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/decision/ranking" -Headers $headers | ConvertTo-Json
Write-Host "--- RECOMMENDATIONS ---"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/decision/recommendations" -Headers $headers | ConvertTo-Json
Write-Host "--- NOTIFICATIONS ---"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/notifications" -Headers $headers | ConvertTo-Json