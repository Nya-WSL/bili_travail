$check = Test-Path "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -PathType Container # 检查 Edge WebView2 注册表路径
$installerUrl = "https://go.microsoft.com/fwlink/p/?LinkId=2124703" # 在线安装程序链接
$installer = "MicrosoftEdgeWebview2Setup.exe"

if ($check) {
    Write-Output "Edge WebView2 runtime 已安装"
}
else {
    Write-Output "未检测到 Edge WebView2 runtime，尝试使用winget安装..."
    # 通过 winget 安装 WebView2
    winget install Microsoft.EdgeWebview2Runtime --accept-source-agreements --accept-package-agreements >$null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Edge WebView2 runtime 安装成功"
    }
    else {
        Write-Output "winget安装失败，尝试使用在线安装程序安装..."
        Invoke-WebRequest -Uri $installerUrl -OutFile $installer
        & ".\$installer"
    }
}