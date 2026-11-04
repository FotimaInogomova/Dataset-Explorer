$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$appPath = Join-Path $projectRoot 'app.py'

function Test-Streamlit($port) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/_stcore/health" -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content.Trim() -eq 'ok'
    } catch {
        return $false
    }
}

try {
    if (-not (Test-Path $pythonPath)) { throw "Project Python environment was not found: $pythonPath" }
    if (-not (Test-Path $appPath)) { throw "Dataset Explorer app.py was not found: $appPath" }

    $port = $null
    for ($candidate = 8501; $candidate -le 8510; $candidate++) {
        if (Test-Streamlit $candidate) {
            $port = $candidate
            break
        }
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $candidate)
            $listener.Start()
            $port = $candidate
            break
        } catch {
        } finally {
            if ($listener) { $listener.Stop() }
        }
    }
    if ($null -eq $port) { throw 'No available local port was found between 8501 and 8510.' }

    if (-not (Test-Streamlit $port)) {
        $quotedAppPath = '"' + $appPath + '"'
        $arguments = @('-m', 'streamlit', 'run', $quotedAppPath, '--server.headless', 'true', '--server.address', '127.0.0.1', '--server.port', "$port", '--browser.gatherUsageStats', 'false')
        Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden | Out-Null

        $ready = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 500
            if (Test-Streamlit $port) { $ready = $true; break }
        }
        if (-not $ready) { throw "Streamlit did not respond on local port $port." }
    }

    Start-Process "http://127.0.0.1:$port/"
} catch {
    $dialog = New-Object -ComObject WScript.Shell
    $null = $dialog.Popup("Dataset Explorer could not start.`r`n$($_.Exception.Message)", 0, 'Dataset Explorer', 16)
    exit 1
}
