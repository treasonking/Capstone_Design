param(
    [string]$InputDir = "docs/images",
    [string]$OutputDir = "docs/images"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

function New-BitmapContext {
    param(
        [int]$Width,
        [int]$Height
    )

    $bitmap = New-Object System.Drawing.Bitmap $Width, $Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    return @{ Bitmap = $bitmap; Graphics = $graphics }
}

function Save-Bitmap {
    param(
        [hashtable]$Context,
        [string]$Path
    )

    $Context.Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $Context.Graphics.Dispose()
    $Context.Bitmap.Dispose()
}

function Get-WrappedLines {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [int]$MaxWidth
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return @("")
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $current = ""
    foreach ($word in ($Text -split "\s+")) {
        $candidate = if ($current) { "$current $word" } else { $word }
        $size = $Graphics.MeasureString($candidate, $Font)
        if ($size.Width -le $MaxWidth) {
            $current = $candidate
            continue
        }
        if ($current) {
            $lines.Add($current)
        }
        $current = $word
    }
    if ($current) {
        $lines.Add($current)
    }
    return $lines
}

function Draw-TextBlock {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush,
        [int]$X,
        [int]$Y,
        [int]$MaxWidth,
        [int]$LineHeight
    )

    $cursorY = $Y
    foreach ($line in (Get-WrappedLines -Graphics $Graphics -Text $Text -Font $Font -MaxWidth $MaxWidth)) {
        $Graphics.DrawString($line, $Font, $Brush, $X, $cursorY)
        $cursorY += $LineHeight
    }
    return $cursorY
}

function Draw-Badge {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [int]$X,
        [int]$Y,
        [System.Drawing.Color]$FillColor,
        [System.Drawing.Color]$TextColor
    )

    $paddingX = 16
    $paddingY = 8
    $textSize = $Graphics.MeasureString($Text, $Font)
    $rect = New-Object System.Drawing.RectangleF($X, $Y, ($textSize.Width + ($paddingX * 2)), ($textSize.Height + ($paddingY * 2)))
    $fill = New-Object System.Drawing.SolidBrush $FillColor
    $textBrush = New-Object System.Drawing.SolidBrush $TextColor
    $Graphics.FillRectangle($fill, $rect)
    $Graphics.DrawString($Text, $Font, $textBrush, ($X + $paddingX), ($Y + $paddingY))
    $fill.Dispose()
    $textBrush.Dispose()
}

function New-ScenarioImage {
    param(
        [string]$Slug,
        [string]$Title,
        [string]$Expectation
    )

    $requestPath = Join-Path $InputDir "$Slug.request.json"
    $responsePath = Join-Path $InputDir "$Slug.response.json"
    $outputPath = Join-Path $OutputDir "$Slug.png"

    $requestText = (Get-Content $requestPath -Raw).Trim()
    $response = Get-Content $responsePath -Raw | ConvertFrom-Json

    $ctx = New-BitmapContext -Width 1600 -Height 1080
    $g = $ctx.Graphics
    $g.Clear([System.Drawing.Color]::FromArgb(242, 246, 251))

    $titleFont = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
    $subFont = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Regular)
    $sectionFont = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
    $monoFont = New-Object System.Drawing.Font("Consolas", 15, [System.Drawing.FontStyle]::Regular)
    $smallMono = New-Object System.Drawing.Font("Consolas", 12, [System.Drawing.FontStyle]::Regular)
    $darkBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(21, 31, 46))
    $mutedBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(96, 107, 124))
    $panelBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $codeBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(15, 55, 108))
    $borderPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(212, 221, 231))

    $g.FillRectangle($panelBrush, 60, 60, 1480, 960)
    $g.DrawString($Title, $titleFont, $darkBrush, 100, 100)
    $g.DrawString("Live proxy response captured from http://127.0.0.1:8000/proxy/chat", $subFont, $mutedBrush, 100, 148)
    Draw-Badge -Graphics $g -Text ("Expected " + $Expectation) -Font $subFont -X 1060 -Y 102 -FillColor ([System.Drawing.Color]::FromArgb(230, 239, 255)) -TextColor ([System.Drawing.Color]::FromArgb(18, 92, 166))
    Draw-Badge -Graphics $g -Text ("Actual " + $response.action) -Font $subFont -X 1265 -Y 102 -FillColor ([System.Drawing.Color]::FromArgb(255, 240, 214)) -TextColor ([System.Drawing.Color]::FromArgb(155, 90, 0))

    $g.DrawString("Request", $sectionFont, $darkBrush, 100, 220)
    $g.FillRectangle($panelBrush, 100, 260, 1340, 110)
    $g.DrawRectangle($borderPen, 100, 260, 1340, 110)
    [void](Draw-TextBlock -Graphics $g -Text $requestText -Font $monoFont -Brush $codeBrush -X 124 -Y 292 -MaxWidth 1290 -LineHeight 25)

    $g.DrawString("Response Highlights", $sectionFont, $darkBrush, 100, 410)
    $highlights = @(
        "action: $($response.action)",
        "reason_code: $($response.reason_code)",
        "input_action: $($response.input_action)",
        "output_action: $($response.output_action)",
        "timestamp_utc: $($response.audit_summary.timestamp_utc)",
        "latency_ms: $($response.audit_summary.latency_ms)"
    )
    $cursorY = 452
    foreach ($line in $highlights) {
        $g.DrawString("• $line", $subFont, $darkBrush, 120, $cursorY)
        $cursorY += 34
    }

    $g.DrawString("Reasons", $sectionFont, $darkBrush, 860, 410)
    $reasons = ($response.reasons -join ", ")
    [void](Draw-TextBlock -Graphics $g -Text $reasons -Font $subFont -Brush $darkBrush -X 880 -Y 452 -MaxWidth 560 -LineHeight 30)

    $g.DrawString("Content", $sectionFont, $darkBrush, 100, 700)
    $g.FillRectangle($panelBrush, 100, 740, 1340, 100)
    $g.DrawRectangle($borderPen, 100, 740, 1340, 100)
    [void](Draw-TextBlock -Graphics $g -Text ([string]$response.content) -Font $monoFont -Brush $codeBrush -X 124 -Y 772 -MaxWidth 1290 -LineHeight 25)

    $g.DrawString("Audit Preview", $sectionFont, $darkBrush, 100, 880)
    $g.FillRectangle($panelBrush, 100, 920, 1340, 70)
    $g.DrawRectangle($borderPen, 100, 920, 1340, 70)
    $auditPreview = ($response.audit_summary | ConvertTo-Json -Depth 4 -Compress)
    [void](Draw-TextBlock -Graphics $g -Text $auditPreview -Font $smallMono -Brush $codeBrush -X 124 -Y 944 -MaxWidth 1290 -LineHeight 18)

    Save-Bitmap -Context $ctx -Path $outputPath

    $titleFont.Dispose()
    $subFont.Dispose()
    $sectionFont.Dispose()
    $monoFont.Dispose()
    $smallMono.Dispose()
    $darkBrush.Dispose()
    $mutedBrush.Dispose()
    $panelBrush.Dispose()
    $codeBrush.Dispose()
    $borderPen.Dispose()
}

New-ScenarioImage -Slug "demo_proxy_block_direct_override" -Title "Security Proxy Demo - Direct Override Block" -Expectation "BLOCK"
New-ScenarioImage -Slug "demo_proxy_mask_phone" -Title "Security Proxy Demo - Phone Masking" -Expectation "MASK"
New-ScenarioImage -Slug "demo_proxy_boundary_allow" -Title "Security Proxy Demo - Boundary Safe Allow" -Expectation "ALLOW"
New-ScenarioImage -Slug "demo_proxy_multi_step_warn" -Title "Security Proxy Demo - Multi-Step Warning" -Expectation "WARN"
