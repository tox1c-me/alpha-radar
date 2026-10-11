param(
    [int]$Index = 1,
    [int]$Offset = 60
)

$ErrorActionPreference = 'Stop'

$dataPath = Join-Path $PSScriptRoot 'events.json'
$events = Get-Content -Path $dataPath -Encoding UTF8 -Raw | ConvertFrom-Json
$e = $events[$Index - 1]

$sep = '----------------------------------------'
$msg = $e.body + "`r`n`r`n" + $sep + "`r`n距发布还有约 $Offset 分钟。"

Add-Type -AssemblyName System.Windows.Forms

$form = New-Object System.Windows.Forms.Form
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.WindowState = [System.Windows.Forms.FormWindowState]::Minimized

[void][System.Windows.Forms.MessageBox]::Show(
    $form,
    $msg,
    $e.title,
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Warning
)

$form.Dispose()
