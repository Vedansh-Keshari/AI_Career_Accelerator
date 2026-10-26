<#
.SYNOPSIS
  Runs every automated Canvas Studio test on this machine and writes a report.
.DESCRIPTION
  Creates a private Python environment, installs what the apps need, then runs: environment smoke checks, the
  shared/web/desktop test suites, a real-browser end-to-end test, and a launcher start-up check.
  Results go to windows-test-report.md (plus JUnit XML) in the output folder. Exit code 0 = no failures.
.PARAMETER SkipInstall  Reuse the environment from a previous run.
.PARAMETER SkipBrowser  Skip the browser end-to-end test (no Chromium download).
.PARAMETER OutDir       Where the environment, logs and report go (default: .\windows-test-output next to this script).
#>
param(
  [switch]$SkipInstall,
  [switch]$SkipBrowser,
  [string]$OutDir = (Join-Path $PSScriptRoot "windows-test-output")
)
$ErrorActionPreference = "Continue"
$isWin = if (Test-Path variable:IsWindows) { $IsWindows } else { $true }   # Windows PowerShell 5.1 has no $IsWindows
$Shared = Split-Path -Parent $PSScriptRoot
$Root = Split-Path -Parent $Shared
$WebDir = Join-Path $Root "web"; $DeskDir = Join-Path $Root "desktop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Venv = Join-Path $OutDir "venv"
$Py = if ($isWin) { Join-Path $Venv "Scripts\python.exe" } else { Join-Path $Venv "bin/python" }
$Results = New-Object System.Collections.Generic.List[object]
$env:CANVAS_NO_KEYRING = "1"          # automated tests must not touch your real Credential Manager
$env:PYTHONIOENCODING = "utf-8"

function Add-Result($name, $status, $seconds, $detail) {
  $Results.Add([pscustomobject]@{ Step = $name; Status = $status; Seconds = [math]::Round($seconds, 1); Detail = $detail })
  $color = switch ($status) { "PASS" { "Green" } "FAIL" { "Red" } "SKIP" { "DarkGray" } default { "Yellow" } }
  Write-Host ("[{0}] {1} ({2:N1}s) {3}" -f $status, $name, $seconds, $detail) -ForegroundColor $color
}
function Run-Step($name, [scriptblock]$body, $log) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $body *> $log
  $code = $LASTEXITCODE
  $sw.Stop()
  $tail = (Get-Content $log -Tail 3 -ErrorAction SilentlyContinue) -join " | "
  if ($code -eq 0) { Add-Result $name "PASS" $sw.Elapsed.TotalSeconds "log: $log" }
  else { Add-Result $name "FAIL" $sw.Elapsed.TotalSeconds "exit $code - $tail (log: $log)" }
}

Write-Host "Canvas Studio test run  |  root: $Root  |  output: $OutDir`n"

# ---- 0. layout
if (-not (Test-Path (Join-Path (Join-Path $Shared "studio") "__init__.py"))) { Write-Host "Cannot find shared\studio - run this from the shared\windows-tests folder." -ForegroundColor Red; exit 2 }
$hasWeb = Test-Path (Join-Path $WebDir "app.py"); $hasDesk = Test-Path (Join-Path $DeskDir "app.py")
Add-Result "Folder layout (shared + web + desktop side by side)" $(if ($hasWeb -and $hasDesk) { "PASS" } else { "WARN" }) 0 "web: $hasWeb, desktop: $hasDesk"

# ---- 1. python + venv + install
$SysPy = $null
foreach ($cand in @("py", "python", "python3")) { if (Get-Command $cand -ErrorAction SilentlyContinue) { $SysPy = $cand; break } }
if (-not $SysPy) { Write-Host "Python 3.10+ was not found. Install it from python.org (tick 'Add Python to PATH')." -ForegroundColor Red; exit 2 }
if (-not $SkipInstall) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  if (-not (Test-Path $Py)) { if ($SysPy -eq "py") { & py -3 -m venv $Venv } else { & $SysPy -m venv $Venv } }
  $reqs = @(); foreach ($f in @((Join-Path $WebDir "requirements.txt"), (Join-Path $DeskDir "requirements.txt"))) { if (Test-Path $f) { $reqs += @("-r", $f) } }
  & $Py -m pip install -q --disable-pip-version-check @reqs pytest playwright 2>&1 | Tee-Object (Join-Path $OutDir "pip.log") | Out-Null
  $code = $LASTEXITCODE; $sw.Stop()
  Add-Result "Create environment and install libraries" $(if ($code -eq 0) { "PASS" } else { "FAIL" }) $sw.Elapsed.TotalSeconds "pip log: $(Join-Path $OutDir 'pip.log')"
  if ($code -ne 0) { Write-Host "Install failed; see pip.log." -ForegroundColor Red }
}
if (-not (Test-Path $Py)) { Write-Host "No environment at $Venv (run without -SkipInstall first)." -ForegroundColor Red; exit 2 }

# ---- 2. smoke checks
Run-Step "Environment and Windows smoke checks" { & $Py (Join-Path $PSScriptRoot "smoke_windows.py") --json (Join-Path $OutDir "smoke.json") } (Join-Path $OutDir "smoke.log")

# ---- 3. test suites
Push-Location $Root
Run-Step "Shared engine tests (render, Canva flow, export, secrets, AI, golden images, Windows compatibility)" {
  & $Py -m pytest (Join-Path $Shared "tests") -q -p no:cacheprovider --junitxml (Join-Path $OutDir "junit-shared.xml") } (Join-Path $OutDir "tests-shared.log")
if ($hasWeb) { Run-Step "Website tests" { & $Py -m pytest (Join-Path $WebDir "tests") -q -p no:cacheprovider --junitxml (Join-Path $OutDir "junit-web.xml") } (Join-Path $OutDir "tests-web.log") }
else { Add-Result "Website tests" "SKIP" 0 "web folder not found" }
if ($hasDesk) { Run-Step "Desktop app tests" { & $Py -m pytest (Join-Path $DeskDir "tests") -q -p no:cacheprovider --junitxml (Join-Path $OutDir "junit-desktop.xml") } (Join-Path $OutDir "tests-desktop.log") }
else { Add-Result "Desktop app tests" "SKIP" 0 "desktop folder not found" }
Pop-Location

# ---- 4. browser end to end
if ($SkipBrowser -or -not $hasWeb) { Add-Result "Browser end-to-end test" "SKIP" 0 $(if ($hasWeb) { "-SkipBrowser" } else { "web folder not found" }) }
else {
  Run-Step "Install Chromium for the browser test" { & $Py -m playwright install chromium } (Join-Path $OutDir "playwright-install.log")
  $env:E2E_PYTHON = $Py; $env:E2E_APP = (Join-Path $WebDir "app.py"); $env:E2E_SHOTS = (Join-Path $OutDir "screenshots")
  Run-Step "Browser end-to-end test (editor, undo, brand kit, push, downloads)" { & $Py (Join-Path (Join-Path $Shared "tests") "e2e_browser.py") } (Join-Path $OutDir "e2e.log")
}

# ---- 5. launcher start-up check (the exact thing a user double-clicks)
if ($hasWeb) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $env:NO_BROWSER = "1"; $env:PORT = "5077"; $env:CANVA_STUDIO_HOME = (Join-Path $OutDir "launcher-home")
  $winHidden = if ($isWin) { @{ WindowStyle = "Hidden" } } else { @{} }
  $p = Start-Process -FilePath $Py -ArgumentList @((Join-Path $WebDir "app.py")) -PassThru @winHidden -RedirectStandardOutput (Join-Path $OutDir "launcher.out") -RedirectStandardError (Join-Path $OutDir "launcher.err")
  $ok = $false; $detail = ""
  for ($i = 0; $i -lt 40 -and -not $ok; $i++) {
    Start-Sleep -Milliseconds 500
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5077/api/bootstrap" -TimeoutSec 3; if ($r.StatusCode -eq 200 -and $r.Content -match "examples") { $ok = $true } } catch { }
  }
  if ($ok) { try { $h = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5077/" -TimeoutSec 3; $detail = "home page HTTP $($h.StatusCode), headers: X-Frame-Options=$($h.Headers['X-Frame-Options'])" } catch { $ok = $false; $detail = $_.Exception.Message } }
  try { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } } catch { }
  Remove-Item Env:\PORT, Env:\NO_BROWSER, Env:\CANVA_STUDIO_HOME -ErrorAction SilentlyContinue
  $sw.Stop()
  Add-Result "Website launcher starts and answers HTTP" $(if ($ok) { "PASS" } else { "FAIL" }) $sw.Elapsed.TotalSeconds $detail
}

# ---- 6. report
$pass = ($Results | Where-Object Status -eq "PASS").Count; $fail = ($Results | Where-Object Status -eq "FAIL").Count
$warn = ($Results | Where-Object Status -eq "WARN").Count; $skip = ($Results | Where-Object Status -eq "SKIP").Count
$osInfo = if ($isWin) { (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption } else { "non-Windows (script logic check only)" }
$report = @("# Canvas Studio automated test report", "", "- Run: $(Get-Date -Format 'yyyy-MM-dd HH:mm')", "- Machine: $env:COMPUTERNAME  |  OS: $osInfo  |  PowerShell $($PSVersionTable.PSVersion)",
  "- Python: $(& $Py --version 2>&1)", "- Result: **$pass passed, $fail failed, $warn warnings, $skip skipped**", "", "| Step | Status | Seconds | Detail |", "|---|---|---|---|")
foreach ($r in $Results) { $report += "| $($r.Step) | $($r.Status) | $($r.Seconds) | $($r.Detail -replace '\|', '/') |" }
$smokePath = Join-Path $OutDir "smoke.json"
if (Test-Path $smokePath) {
  $report += @("", "## Environment checks", "", "| Check | Status | Detail |", "|---|---|---|")
  foreach ($c in (Get-Content $smokePath -Raw | ConvertFrom-Json).results) { $report += "| $($c.check) | $($c.status) | $($c.detail -replace '\|', '/') |" }
}
$report += @("", "Next: do the manual checks in WINDOWS_TEST_DOCUMENT.md (window, downloads, real Canva sign-in) and record results there.")
$reportPath = Join-Path $OutDir "windows-test-report.md"
Set-Content -Path $reportPath -Value $report -Encoding UTF8
Write-Host "`n$pass passed, $fail failed, $warn warnings, $skip skipped.  Report: $reportPath" -ForegroundColor $(if ($fail) { "Red" } else { "Green" })
exit $(if ($fail) { 1 } else { 0 })
