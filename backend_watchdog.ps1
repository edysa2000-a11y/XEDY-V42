# ==============================================================================
# XEDY BACKEND KEEP-ALIVE WATCHDOG
# Periodically monitors port 8000. Restarts the server instantly if down.
# ==============================================================================

$port = 8000
$healthUrl = "http://127.0.0.1:$port/api/v1/health"
$sleepIntervalSeconds = 30
$projectDir = "c:\Antigravity\Project\XEDY Mission Control"

Write-Host "=========================================================="
Write-Host "   XEDY Mission Control Watchdog Daemon Started           "
Write-Host "   Monitoring Port: $port | Interval: $sleepIntervalSeconds seconds"
Write-Host "=========================================================="

# Main Loop
while ($true) {
    try {
        # Perform HTTP check with a tight timeout (5s)
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "OPERATIONAL") {
            # Server is healthy
            Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | [HEALTHY] Backend is running operational." -ForegroundColor Green
        } else {
            Throw "Server returned non-operational state: $($response.status)"
        }
    } catch {
        # Server is dead or not responding
        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | [CRITICAL] Backend server is DOWN or unresponsive! Initiating auto-recovery..." -ForegroundColor Red
        
        # Kill any dangling/frozen processes on port 8000 first
        $portProcess = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
        if ($portProcess) {
            foreach ($pidVal in $portProcess) {
                Write-Host "Killing zombie process PID: $pidVal" -ForegroundColor Yellow
                Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue
            }
            # Allow OS sockets to free up
            Start-Sleep -Seconds 2
        }

        # Spawn backend in background
        Write-Host "Spawning clean backend server instance via run_backend.bat..." -ForegroundColor Cyan
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c run_backend.bat" -WorkingDirectory $projectDir -WindowStyle Minimized
        
        # Wait 15 seconds to let server load fully before next check
        Start-Sleep -Seconds 15
    }

    Start-Sleep -Seconds $sleepIntervalSeconds
}
