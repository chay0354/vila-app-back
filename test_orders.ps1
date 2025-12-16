$base = "http://127.0.0.1:4000"
$id = "ORD-" + [guid]::NewGuid().ToString()

Write-Host "=== Creating Order ==="
$body = @{
  id = $id
  guest_name = "Test Guest"
  unit_number = "101"
  arrival_date = "2025-03-01"
  departure_date = "2025-03-03"
  status = "חדש"
  guests_count = 2
  paid_amount = 0
  total_amount = 1500
  payment_method = "מזומן"
} | ConvertTo-Json -Depth 10

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$utf8 = New-Object System.Text.UTF8Encoding $false
$bodyBytes = $utf8.GetBytes($body)

try {
  $created = Invoke-RestMethod -Method Post -Uri "$base/orders" -Body $body -ContentType "application/json; charset=utf-8"
  Write-Host "Created successfully"
  Write-Host ($created | ConvertTo-Json -Depth 10)
} catch {
  Write-Host "Error creating: $($_.Exception.Message)"
  if ($_.ErrorDetails.Message) {
    Write-Host "Details: $($_.ErrorDetails.Message)"
  }
  exit
}

Write-Host ""
Write-Host "=== Getting All Orders ==="
try {
  $all = Invoke-RestMethod -Method Get -Uri "$base/orders"
  Write-Host "Found $($all.Count) orders"
  $found = $all | Where-Object { $_.id -eq $id }
  if ($found) {
    Write-Host "Found our order"
    Write-Host ($found | ConvertTo-Json -Depth 10)
  } else {
    Write-Host "Order not found in list"
  }
} catch {
  Write-Host "Error getting orders: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "=== Updating Order ==="
$patch = @{
  status = "שולם"
  paid_amount = 1500
} | ConvertTo-Json -Depth 10

try {
  $updated = Invoke-RestMethod -Method Patch -Uri "$base/orders/$id" -Body $patch -ContentType "application/json; charset=utf-8"
  Write-Host "Updated successfully"
  Write-Host ($updated | ConvertTo-Json -Depth 10)
} catch {
  Write-Host "Error updating: $($_.Exception.Message)"
  if ($_.ErrorDetails.Message) {
    Write-Host "Details: $($_.ErrorDetails.Message)"
  }
}

Write-Host ""
Write-Host "=== Deleting Order ==="
try {
  Invoke-RestMethod -Method Delete -Uri "$base/orders/$id"
  Write-Host "Deleted order $id"
} catch {
  Write-Host "Error deleting: $($_.Exception.Message)"
  if ($_.ErrorDetails.Message) {
    Write-Host "Details: $($_.ErrorDetails.Message)"
  }
}

Write-Host ""
Write-Host "=== Verifying Deletion ==="
try {
  $all = Invoke-RestMethod -Method Get -Uri "$base/orders"
  $found = $all | Where-Object { $_.id -eq $id }
  if ($found) {
    Write-Host "ERROR: Order still exists!"
  } else {
    Write-Host "SUCCESS: Order deleted from DB"
  }
} catch {
  Write-Host "Error verifying: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "=== Test Complete ==="
