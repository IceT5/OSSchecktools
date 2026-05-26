Get-Process | Where-Object { $_.ProcessName -match 'scancode|extractcode|python' } | ForEach-Object {
    $memMB = [math]::Round($_.WorkingSet64/1MB, 1)
    $cpuS = [math]::Round($_.CPU, 1)
    '{0,6} | {1,-20} | CPU:{2,8}s | Mem:{3,8}MB | {4}' -f $_.Id, $_.ProcessName, $cpuS, $memMB, $_.StartTime
}
