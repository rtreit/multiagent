#!/usr/bin/env pwsh
# Multi-Agent System Startup Script - OpenAI Compatible
# Starts registry, agents with OpenAI API support, and new high-performance GUI

param(
    [switch]$NoGUI,
    [switch]$Help,
    [switch]$UseOldGUI
)

if ($Help) {
    Write-Host "Multi-Agent System Startup Script - OpenAI Compatible"
    Write-Host ""
    Write-Host "Usage: .\start_system.ps1 [-NoGUI] [-UseOldGUI] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -NoGUI      Start only registry and agents (no GUI)"
    Write-Host "  -UseOldGUI  Use the old A2A GUI instead of high-performance OpenAI GUI"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Services started:"
    Write-Host "  - Registry           http://localhost:9010"
    Write-Host "  - Math Agent A2A     http://localhost:9011 (OpenAI API: 10011)"
    Write-Host "  - Quote Agent A2A    http://localhost:9012 (OpenAI API: 10012)"
    Write-Host "  - Search Agent A2A   http://localhost:9013 (OpenAI API: 10013)"
    Write-Host "  - LLM Agent A2A      http://localhost:9014 (OpenAI API: 10014)"
    Write-Host "  - High-Performance GUI http://localhost:8080 (unless -NoGUI or -UseOldGUI)"
    Write-Host "  - Legacy GUI         http://localhost:8000 (only with -UseOldGUI)"
    Write-Host ""
    Write-Host "Performance: New OpenAI GUI delivers <1s response times vs 12+s with legacy A2A GUI"
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

Write-Host "🚀 Starting Multi-Agent System with OpenAI API Support..." -ForegroundColor Green
Write-Host "🎯 Performance Improvement: <1s response times vs 12+s with legacy GUI" -ForegroundColor Cyan
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
    Start-Sleep 5

    # Start Math Agent (A2A: 9011, MCP: 8021, OpenAI API: 10011)
    $mathCmd = "cd '$PWD'; & '$python' -m agents.math_agent http://localhost:9010 9011 8021"
    $mathProcess = Start-Service "Math Agent" $mathCmd "9011"
    $processes += $mathProcess

    # Start Quote Agent (A2A: 9012, MCP: 8022, OpenAI API: 10012)
    $quoteCmd = "cd '$PWD'; & '$python' -m agents.quote_agent http://localhost:9010 9012 8022"
    $quoteProcess = Start-Service "Quote Agent" $quoteCmd "9012"
    $processes += $quoteProcess

    # Start Search Agent (A2A: 9013, MCP: 8023, OpenAI API: 10013)
    $searchCmd = "cd '$PWD'; & '$python' -m agents.search_agent http://localhost:9010 9013 8023"
    $searchProcess = Start-Service "Search Agent" $searchCmd "9013"
    $processes += $searchProcess

    # Start LLM Agent (A2A: 9014, MCP: 8024, OpenAI API: 10014)
    $llmCmd = "cd '$PWD'; & '$python' -m agents.llm_agent http://localhost:9010 9014 8024"
    $llmProcess = Start-Service "LLM Agent" $llmCmd "9014"
    $processes += $llmProcess

    # Wait for agents to register and start their OpenAI APIs
    Start-Sleep 10

    # Start GUI (unless disabled)
    if (!$NoGUI) {
        if ($UseOldGUI) {
            Write-Host "⚠️  Starting legacy A2A GUI (slow performance)" -ForegroundColor Yellow
            $guiCmd = "cd '$PWD'; & '$python' gui_legacy.py"
            $guiProcess = Start-Service "Legacy GUI" $guiCmd "8000"
        } else {
            Write-Host "🚀 Starting high-performance OpenAI GUI" -ForegroundColor Green
            $guiCmd = "cd '$PWD'; & '$python' gui.py"
            $guiProcess = Start-Service "OpenAI GUI" $guiCmd "8080"
        }
        $processes += $guiProcess
        Start-Sleep 3
    }

    Write-Host ""
    Write-Host "✅ All services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URLs:" -ForegroundColor Cyan
    Write-Host "  Registry:        http://localhost:9010" -ForegroundColor White
    Write-Host ""
    Write-Host "A2A Endpoints (Legacy):" -ForegroundColor Yellow
    Write-Host "  Math Agent:      http://localhost:9011" -ForegroundColor White
    Write-Host "  Quote Agent:     http://localhost:9012" -ForegroundColor White
    Write-Host "  Search Agent:    http://localhost:9013" -ForegroundColor White
    Write-Host "  LLM Agent:       http://localhost:9014" -ForegroundColor White
    Write-Host ""
    Write-Host "OpenAI API Endpoints (High Performance):" -ForegroundColor Green
    Write-Host "  Math Agent:      http://localhost:10011/v1/chat/completions" -ForegroundColor White
    Write-Host "  Quote Agent:     http://localhost:10012/v1/chat/completions" -ForegroundColor White
    Write-Host "  Search Agent:    http://localhost:10013/v1/chat/completions" -ForegroundColor White
    Write-Host "  LLM Agent:       http://localhost:10014/v1/chat/completions" -ForegroundColor White
    Write-Host ""
    if (!$NoGUI) {
        if ($UseOldGUI) {
            Write-Host "  Legacy GUI:      http://localhost:8000 (12+s response times)" -ForegroundColor Yellow
        } else {
            Write-Host "  High-Perf GUI:   http://localhost:8080 (<1s response times)" -ForegroundColor Green
        }
    }
    Write-Host ""
    
    # Verify services are responding
    Write-Host "Verifying services..." -ForegroundColor Yellow
    
    $services = @(
        @{Name="Registry"; URL="http://localhost:9010"},
        @{Name="Math Agent OpenAI API"; URL="http://localhost:10011/health"},
        @{Name="Quote Agent OpenAI API"; URL="http://localhost:10012/health"},
        @{Name="Search Agent OpenAI API"; URL="http://localhost:10013/health"},
        @{Name="LLM Agent OpenAI API"; URL="http://localhost:10014/health"}
    )
    
    if (!$NoGUI) {
        if ($UseOldGUI) {
            $services += @{Name="Legacy GUI"; URL="http://localhost:8000"}
        } else {
            $services += @{Name="High-Performance GUI"; URL="http://localhost:8080"}
        }
    }
    
    foreach ($service in $services) {
        try {
            $response = Invoke-WebRequest -Uri $service.URL -TimeoutSec 10 -UseBasicParsing
            Write-Host "  ✅ $($service.Name) is responding" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ $($service.Name) is not responding: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "🎉 System is ready! Press Ctrl+C to stop all services" -ForegroundColor Green
    Write-Host ""
    Write-Host "Performance Notes:" -ForegroundColor Cyan
    Write-Host "  - OpenAI API endpoints eliminate A2A protocol overhead" -ForegroundColor White
    Write-Host "  - High-Performance GUI: <1s response times vs 12+s with legacy GUI" -ForegroundColor White
    Write-Host "  - Use OpenAI GUI for best performance (default)" -ForegroundColor White
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
        $_.CommandLine -like "*gui*.py*" -or
        $_.CommandLine -like "*agents.*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ All services stopped" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Tip: Use -UseOldGUI flag if you need legacy A2A GUI for testing" -ForegroundColor Cyan
}
