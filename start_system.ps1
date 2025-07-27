#!/usr/bin/env pwsh
# Multi-Agent System Startup Script
# Starts registry, agents, and GUI in the correct order

param(
    [switch]$NoGUI,
    [switch]$Help
)

if ($Help) {
    Write-Host "Multi-Agent System Startup Script"
    Write-Host ""
    Write-Host "Usage: .\start_system.ps1 [-NoGUI] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -NoGUI    Start only registry and agents (no GUI)"
    Write-Host "  -Help     Show this help message"
    Write-Host ""
    Write-Host "Services started:"
    Write-Host "  - Registry      http://localhost:9010"
    Write-Host "  - Math Agent    http://localhost:9011"
    Write-Host "  - Quote Agent   http://localhost:9012"
    Write-Host "  - Search Agent  http://localhost:9013"
    Write-Host "  - GUI           http://localhost:8000 (unless -NoGUI)"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services"
    exit 0
}

# Check if we're in the right directory
if (!(Test-Path "registry.py")) {
    Write-Error "Please run this script from the multiagent project directory"
    exit 1
}

# Check if virtual environment exists
if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Please ensure .venv exists"
    exit 1
}

$python = ".\.venv\Scripts\python.exe"

Write-Host "🚀 Starting Multi-Agent System..." -ForegroundColor Green
Write-Host ""

# Function to start a service in background
function Start-Service {
    param($Name, $Command, $Port)
    Write-Host "Starting $Name on port $Port..." -ForegroundColor Yellow
    $process = Start-Process -FilePath "pwsh" -ArgumentList "-Command", $Command -PassThru -WindowStyle Hidden
    Start-Sleep 2  # Give service time to start
    return $process
}

# Array to track all processes
$processes = @()

try {
    # Start Registry
    $registryCmd = "cd '$PWD'; & '$python' registry.py"
    $registryProcess = Start-Service "Registry" $registryCmd "9010"
    $processes += $registryProcess

    # Wait a bit for registry to fully start
    Start-Sleep 3

    # Start Math Agent
    $mathCmd = "cd '$PWD'; & '$python' -m agents.math_agent http://localhost:9010 9011 8021"
    $mathProcess = Start-Service "Math Agent" $mathCmd "9011"
    $processes += $mathProcess

    # Start Quote Agent
    $quoteCmd = "cd '$PWD'; & '$python' -m agents.quote_agent http://localhost:9010 9012 8022"
    $quoteProcess = Start-Service "Quote Agent" $quoteCmd "9012"
    $processes += $quoteProcess

    # Start Search Agent
    $searchCmd = "cd '$PWD'; & '$python' -m agents.search_agent http://localhost:9010 9013 8023"
    $searchProcess = Start-Service "Search Agent" $searchCmd "9013"
    $processes += $searchProcess

    # Wait for agents to register
    Start-Sleep 5

    # Start GUI (unless disabled)
    if (!$NoGUI) {
        $guiCmd = "cd '$PWD'; & '$python' gui.py"
        $guiProcess = Start-Service "GUI" $guiCmd "8000"
        $processes += $guiProcess
        Start-Sleep 2
    }

    Write-Host ""
    Write-Host "✅ All services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URLs:" -ForegroundColor Cyan
    Write-Host "  Registry:     http://localhost:9010" -ForegroundColor White
    Write-Host "  Math Agent:   http://localhost:9011" -ForegroundColor White
    Write-Host "  Quote Agent:  http://localhost:9012" -ForegroundColor White
    Write-Host "  Search Agent: http://localhost:9013" -ForegroundColor White
    if (!$NoGUI) {
        Write-Host "  GUI:          http://localhost:8000" -ForegroundColor White
    }
    Write-Host ""
    
    # Verify services are responding
    Write-Host "Verifying services..." -ForegroundColor Yellow
    
    $services = @(
        @{Name="Registry"; URL="http://localhost:9010"},
        @{Name="Math Agent"; URL="http://localhost:9011"},
        @{Name="Quote Agent"; URL="http://localhost:9012"},
        @{Name="Search Agent"; URL="http://localhost:9013"}
    )
    
    if (!$NoGUI) {
        $services += @{Name="GUI"; URL="http://localhost:8000"}
    }
    
    foreach ($service in $services) {
        try {
            $response = Invoke-WebRequest -Uri $service.URL -TimeoutSec 5 -UseBasicParsing
            Write-Host "  ✅ $($service.Name) is responding" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ $($service.Name) is not responding" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "🎉 System is ready! Press Ctrl+C to stop all services" -ForegroundColor Green
    Write-Host ""

    # Wait for Ctrl+C
    [Console]::TreatControlCAsInput = $true
    while ($true) {
        $key = [Console]::ReadKey($true)
        if (($key.Modifiers -band [ConsoleModifiers]::Control) -and ($key.Key -eq 'C')) {
            break
        }
        Start-Sleep 1
    }

} catch {
    Write-Error "Failed to start services: $_"
} finally {
    # Clean up processes
    Write-Host ""
    Write-Host "🛑 Stopping all services..." -ForegroundColor Yellow
    
    foreach ($process in $processes) {
        if ($process -and !$process.HasExited) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped process $($process.Id)" -ForegroundColor Gray
            } catch {
                # Process might have already exited
            }
        }
    }
    
    # Kill any remaining Python processes that might be related
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*multiagent*" -or 
        $_.CommandLine -like "*registry.py*" -or
        $_.CommandLine -like "*gui.py*" -or
        $_.CommandLine -like "*agents.*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ All services stopped" -ForegroundColor Green
}
