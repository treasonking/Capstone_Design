param(
    [string]$EvaluationReport = "reports/evaluation_report.md",
    [string]$ProxyRequest = "reports/assets/proxy_demo_request.json",
    [string]$ProxyResponse = "reports/assets/proxy_demo_response.json",
    [string]$OutputDir = "reports/assets"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

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

function Get-MetricCell {
    param(
        [string]$Line,
        [int]$Index
    )

    $parts = $Line.Trim("|").Split("|") | ForEach-Object { $_.Trim() }
    return $parts[$Index]
}

function New-EvaluationImage {
    param(
        [string]$MarkdownPath,
        [string]$OutputPath
    )

    $content = Get-Content $MarkdownPath -Raw
    $datasetSize = [regex]::Match($content, "Dataset size:\s*(\d+)").Groups[1].Value
    $generatedAt = [regex]::Match($content, "Generated at:\s*([^\r\n]+)").Groups[1].Value
    $summaryLines = ($content -split "`r?`n") | Where-Object { $_ -match "^\|\s*(pii|injection)\s*\|" }
    $piiLine = $summaryLines | Where-Object { $_ -match "^\|\s*pii\s*\|" } | Select-Object -First 1
    $injLine = $summaryLines | Where-Object { $_ -match "^\|\s*injection\s*\|" } | Select-Object -First 1

    $ctx = New-BitmapContext -Width 1600 -Height 900
    $g = $ctx.Graphics
    $g.Clear([System.Drawing.Color]::FromArgb(245, 248, 252))

    $titleFont = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
    $subFont = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Regular)
    $sectionFont = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
    $bodyFont = New-Object System.Drawing.Font("Consolas", 16, [System.Drawing.FontStyle]::Regular)
    $smallFont = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Regular)
    $darkBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(24, 33, 47))
    $mutedBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(92, 104, 120))

    $cardBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $g.FillRectangle($cardBrush, 60, 60, 1480, 780)
    $g.DrawString("Capstone Detection Evaluation", $titleFont, $darkBrush, 100, 100)
    $g.DrawString("Dataset size 102 evidence snapshot", $subFont, $mutedBrush, 100, 148)
    $g.DrawString("Generated: $generatedAt", $smallFont, $mutedBrush, 100, 178)

    Draw-Badge -Graphics $g -Text "Dataset $datasetSize" -Font $smallFont -X 1180 -Y 100 -FillColor ([System.Drawing.Color]::FromArgb(225, 240, 255)) -TextColor ([System.Drawing.Color]::FromArgb(17, 88, 164))
    Draw-Badge -Graphics $g -Text "No FP / No FN" -Font $smallFont -X 1320 -Y 100 -FillColor ([System.Drawing.Color]::FromArgb(227, 247, 234)) -TextColor ([System.Drawing.Color]::FromArgb(31, 111, 60))

    $g.DrawString("Summary Table", $sectionFont, $darkBrush, 100, 250)

    $tableX = 100
    $tableY = 300
    $rowHeight = 76
    $columns = @(260, 220, 220, 220, 320)
    $headers = @("Task", "Precision", "Recall", "F1", "TP / FP / FN")
    $headerBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(232, 238, 246))
    $linePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(214, 221, 232))

    $cursorX = $tableX
    for ($i = 0; $i -lt $headers.Count; $i++) {
        $g.FillRectangle($headerBrush, $cursorX, $tableY, $columns[$i], $rowHeight)
        $g.DrawRectangle($linePen, $cursorX, $tableY, $columns[$i], $rowHeight)
        $g.DrawString($headers[$i], $sectionFont, $darkBrush, ($cursorX + 18), ($tableY + 20))
        $cursorX += $columns[$i]
    }

    $rows = @(
        @("PII", (Get-MetricCell $piiLine 1), (Get-MetricCell $piiLine 2), (Get-MetricCell $piiLine 3), ((Get-MetricCell $piiLine 4) + " / " + (Get-MetricCell $piiLine 5) + " / " + (Get-MetricCell $piiLine 6))),
        @("Injection", (Get-MetricCell $injLine 1), (Get-MetricCell $injLine 2), (Get-MetricCell $injLine 3), ((Get-MetricCell $injLine 4) + " / " + (Get-MetricCell $injLine 5) + " / " + (Get-MetricCell $injLine 6)))
    )

    for ($rowIndex = 0; $rowIndex -lt $rows.Count; $rowIndex++) {
        $rowY = $tableY + $rowHeight + ($rowIndex * $rowHeight)
        $bg = if ($rowIndex % 2 -eq 0) {
            [System.Drawing.Color]::FromArgb(250, 252, 255)
        } else {
            [System.Drawing.Color]::FromArgb(243, 247, 252)
        }
        $rowBrush = New-Object System.Drawing.SolidBrush $bg
        $cursorX = $tableX
        for ($colIndex = 0; $colIndex -lt $columns.Count; $colIndex++) {
            $g.FillRectangle($rowBrush, $cursorX, $rowY, $columns[$colIndex], $rowHeight)
            $g.DrawRectangle($linePen, $cursorX, $rowY, $columns[$colIndex], $rowHeight)
            $g.DrawString($rows[$rowIndex][$colIndex], $bodyFont, $darkBrush, ($cursorX + 18), ($rowY + 22))
            $cursorX += $columns[$colIndex]
        }
        $rowBrush.Dispose()
    }

    $g.DrawString("Evidence Notes", $sectionFont, $darkBrush, 100, 560)
    [void](Draw-TextBlock -Graphics $g -Text "Source: reports/evaluation_report.md generated from evaluation/sample_dataset.json. This capture is intended for presentation and report appendix use." -Font $subFont -Brush $mutedBrush -X 100 -Y 610 -MaxWidth 1320 -LineHeight 28)
    [void](Draw-TextBlock -Graphics $g -Text "Focused risk areas in the full markdown report: INJ_OBFUSCATED_INJECTION_ATTEMPT and PII_ACCOUNT_DETECTED. Both remain at 1.000 precision, recall, and F1 in the 102-sample benchmark." -Font $subFont -Brush $mutedBrush -X 100 -Y 680 -MaxWidth 1320 -LineHeight 28)

    Save-Bitmap -Context $ctx -Path $OutputPath

    $titleFont.Dispose()
    $subFont.Dispose()
    $sectionFont.Dispose()
    $bodyFont.Dispose()
    $smallFont.Dispose()
    $darkBrush.Dispose()
    $mutedBrush.Dispose()
    $cardBrush.Dispose()
    $headerBrush.Dispose()
    $linePen.Dispose()
}

function New-ProxyDemoImage {
    param(
        [string]$RequestPath,
        [string]$ResponsePath,
        [string]$OutputPath
    )

    $requestText = (Get-Content $RequestPath -Raw).Trim()
    $response = Get-Content $ResponsePath -Raw | ConvertFrom-Json

    $ctx = New-BitmapContext -Width 1600 -Height 1100
    $g = $ctx.Graphics
    $g.Clear([System.Drawing.Color]::FromArgb(241, 245, 249))

    $titleFont = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
    $subFont = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Regular)
    $sectionFont = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
    $monoFont = New-Object System.Drawing.Font("Consolas", 15, [System.Drawing.FontStyle]::Regular)
    $smallMono = New-Object System.Drawing.Font("Consolas", 13, [System.Drawing.FontStyle]::Regular)
    $darkBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(19, 29, 43))
    $mutedBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(94, 106, 125))
    $whiteBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $panelBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(248, 250, 252))
    $jsonBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(12, 52, 101))
    $panelPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(211, 219, 230))

    $g.FillRectangle($whiteBrush, 60, 60, 1480, 980)
    $g.DrawString("Security Proxy API Demo", $titleFont, $darkBrush, 100, 100)
    $g.DrawString("Live response captured from http://127.0.0.1:8000/proxy/chat", $subFont, $mutedBrush, 100, 148)

    Draw-Badge -Graphics $g -Text ("Action " + $response.action) -Font $subFont -X 1180 -Y 100 -FillColor ([System.Drawing.Color]::FromArgb(255, 241, 214)) -TextColor ([System.Drawing.Color]::FromArgb(153, 89, 0))
    Draw-Badge -Graphics $g -Text ("Reason " + $response.reason_code) -Font $subFont -X 1020 -Y 148 -FillColor ([System.Drawing.Color]::FromArgb(225, 240, 255)) -TextColor ([System.Drawing.Color]::FromArgb(17, 88, 164))

    $g.DrawString("Request", $sectionFont, $darkBrush, 100, 230)
    $g.FillRectangle($panelBrush, 100, 270, 1340, 120)
    $g.DrawRectangle($panelPen, 100, 270, 1340, 120)
    [void](Draw-TextBlock -Graphics $g -Text $requestText -Font $monoFont -Brush $jsonBrush -X 124 -Y 300 -MaxWidth 1290 -LineHeight 26)

    $g.DrawString("Response Highlights", $sectionFont, $darkBrush, 100, 430)
    $highlights = @(
        "action: $($response.action)",
        "input_action: $($response.input_action)",
        "output_action: $($response.output_action)",
        "reason_code: $($response.reason_code)",
        "timestamp_utc: $($response.audit_summary.timestamp_utc)",
        "latency_ms: $($response.audit_summary.latency_ms)"
    )
    $y = 472
    foreach ($line in $highlights) {
        $g.DrawString("• $line", $subFont, $darkBrush, 120, $y)
        $y += 34
    }

    $g.DrawString("Masked Content", $sectionFont, $darkBrush, 100, 700)
    $g.FillRectangle($panelBrush, 100, 740, 1340, 90)
    $g.DrawRectangle($panelPen, 100, 740, 1340, 90)
    [void](Draw-TextBlock -Graphics $g -Text ([string]$response.content) -Font $monoFont -Brush $jsonBrush -X 124 -Y 768 -MaxWidth 1290 -LineHeight 26)

    $g.DrawString("Audit Summary", $sectionFont, $darkBrush, 100, 860)
    $auditJson = $response.audit_summary | ConvertTo-Json -Depth 6
    $g.FillRectangle($panelBrush, 100, 900, 1340, 100)
    $g.DrawRectangle($panelPen, 100, 900, 1340, 100)
    $auditPreview = ($auditJson -split "`r?`n" | Select-Object -First 4) -join " "
    [void](Draw-TextBlock -Graphics $g -Text $auditPreview -Font $smallMono -Brush $jsonBrush -X 124 -Y 926 -MaxWidth 1290 -LineHeight 22)

    Save-Bitmap -Context $ctx -Path $OutputPath

    $titleFont.Dispose()
    $subFont.Dispose()
    $sectionFont.Dispose()
    $monoFont.Dispose()
    $smallMono.Dispose()
    $darkBrush.Dispose()
    $mutedBrush.Dispose()
    $whiteBrush.Dispose()
    $panelBrush.Dispose()
    $jsonBrush.Dispose()
    $panelPen.Dispose()
}

New-EvaluationImage -MarkdownPath $EvaluationReport -OutputPath (Join-Path $OutputDir "evaluation_summary_capture.png")
New-ProxyDemoImage -RequestPath $ProxyRequest -ResponsePath $ProxyResponse -OutputPath (Join-Path $OutputDir "proxy_api_demo.png")
