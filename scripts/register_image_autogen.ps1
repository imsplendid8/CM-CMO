# 구독(OAuth) 썸네일 자동 생성 — Windows 작업 스케줄러 등록
# 사용: 저장소 폴더에서 PowerShell로  .\scripts\register_image_autogen.ps1
#       시각 변경  .\scripts\register_image_autogen.ps1 -At 12:30 -Limit 8
#       해제      .\scripts\register_image_autogen.ps1 -Remove
# 매일 지정 시각에 대기 썸네일을 최대 Limit건 생성해 main에 올린다. 대기 항목이 없으면 바로 끝난다.
# PC가 꺼져 있었으면 다음에 켜졌을 때 한 번 실행한다(StartWhenAvailable). 로그: 저장소의 .image-autogen.log
param(
  [string]$At = "12:30",
  [int]$Limit = 8,
  [switch]$Remove
)
$ErrorActionPreference = "Stop"
$TaskName = "Modooflow 썸네일 자동 생성"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "해제했습니다: $TaskName"
  return
}

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "Python을 찾지 못했습니다. python.org에서 Python 3을 설치하세요." }
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) { throw "Node.js(npx)를 찾지 못했습니다. nodejs.org에서 LTS를 설치하세요." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git을 찾지 못했습니다. git-scm.com에서 설치하세요." }

$taskArgs = if ($py -like "*\py.exe") { "-3 scripts\local_image_autogen.py --limit $Limit" } else { "scripts\local_image_autogen.py --limit $Limit" }
$action   = New-ScheduledTaskAction -Execute $py -Argument $taskArgs -WorkingDirectory $Repo
$trigger  = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "등록했습니다: 매일 $At · 최대 $Limit 건 · 폴더 $Repo"
Write-Host "지금 한 번 시험하려면:  Start-ScheduledTask -TaskName '$TaskName'  (결과는 .image-autogen.log)"
