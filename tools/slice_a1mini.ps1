# 用 Bambu Studio 命令行切片，输出可以直接在 Bambu Studio 打开 / 发送打印的 .3mf
# 默认：A1 mini 0.4 喷嘴 + 0.20mm Standard @BBL A1M + Bambu PLA Basic @BBL A1M
# 用法：pwsh tools/slice_a1mini.ps1 -Stl path/to/model.stl [-Out model_a1mini.3mf] [-Process "0.28mm Extra Draft @BBL A1M"]
#       多个模型排在同一盘：-Stl a.stl,b.stl -Out plate_a1mini.3mf（自动排布）
param(
    [Parameter(Mandatory)][string[]]$Stl,
    [string]$Out,
    [string]$Printer = "Bambu Lab A1 mini 0.4 nozzle",
    [string]$Process = "0.20mm Standard @BBL A1M",
    [string]$Filament = "Bambu PLA Basic @BBL A1M"
)
$ErrorActionPreference = "Stop"
$exe = "C:\Program Files\Bambu Studio\bambu-studio.exe"
$work = Join-Path $env:TEMP "bbl_slice"
New-Item -ItemType Directory -Force $work | Out-Null
Remove-Item "$work\*" -Recurse -Force -ErrorAction SilentlyContinue

# 命令行不展开预设继承，先展开成完整 JSON
$flatten = Join-Path $PSScriptRoot "flatten_preset.py"
python $flatten machine $Printer "$work\machine.json" | Out-Null
python $flatten process $Process "$work\process.json" | Out-Null
python $flatten filament $Filament "$work\filament.json" | Out-Null

$stlPaths = @($Stl | ForEach-Object { (Resolve-Path $_).Path })
if (-not $Out) {
    if ($stlPaths.Count -gt 1) { throw "多个模型时请用 -Out 指定输出文件" }
    $Out = Join-Path (Split-Path $stlPaths[0]) ([IO.Path]::GetFileNameWithoutExtension($stlPaths[0]) + "_a1mini.3mf")
}
$models = @()
for ($i = 0; $i -lt $stlPaths.Count; $i++) {
    Copy-Item $stlPaths[$i] "$work\model$i.stl"
    $models += "$work\model$i.stl"
}
$a = @("--slice", "0", "--arrange", "1",
       "--load-settings", "`"$work\machine.json;$work\process.json`"",
       "--load-filaments", "`"$work\filament.json`"",
       "--outputdir", $work, "--export-3mf", "sliced.3mf") + $models
$p = Start-Process -FilePath $exe -ArgumentList $a -Wait -PassThru -NoNewWindow
$r = Get-Content "$work\result.json" -Raw | ConvertFrom-Json
if ($r.return_code -ne 0) { throw "切片失败：$($r.error_string)" }
Copy-Item "$work\sliced.3mf" $Out -Force
$t = [TimeSpan]::FromSeconds($r.sliced_plates[0].total_predication)
"{0}: {1:hh}h{1:mm}m, {2:N0}g, layer {3:N2}mm, infill {4}%" -f (Split-Path $Out -Leaf), $t,
    $r.sliced_plates[0].filaments[0].total_used_g, $r.layer_height, $r.sparse_infill_density
