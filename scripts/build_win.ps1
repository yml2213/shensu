param(
  [string]$Python = "python",
  [switch]$OneFile
)

Write-Host "Installing build dependencies..."
& $Python -m pip install --upgrade pip | Out-Null
& $Python -m pip install . pyinstaller | Out-Null

$name = "WechatTool"
$modeArgs = if ($OneFile) { "--onefile" } else { "--onedir" }

Write-Host "Building $name..."
pyinstaller main.py `
  --clean `
  --noconfirm `
  --windowed `
  $modeArgs `
  --name $name `
  --add-data "media;media" `
  --add-data "config.json;."

Write-Host "Done. Artifacts at dist/$name"

