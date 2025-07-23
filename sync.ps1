# PATRIOT Sync Tool - PowerShell скрипт для синхронизации между компьютерами
# ============================================================================

param(
    [string]$Action = "check",
    [string]$Message = "",
    [switch]$Force = $false
)

$Script:ComputerName = $env:COMPUTERNAME
$Script:ProjectName = "PATRIOT Trading System"

function Write-Banner {
    param([string]$Title)
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Yellow
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
}

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $color = switch ($Status) {
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        default { "White" }
    }
    
    $icon = switch ($Status) {
        "SUCCESS" { "✅" }
        "WARNING" { "⚠️ " }
        "ERROR" { "❌" }
        default { "ℹ️ " }
    }
    
    Write-Host "$icon $Message" -ForegroundColor $color
}

function Test-GitRepository {
    try {
        $gitStatus = git status 2>$null
        return $true
    }
    catch {
        return $false
    }
}

function Get-GitStatus {
    if (-not (Test-GitRepository)) {
        Write-Status "Not a git repository" "ERROR"
        return $null
    }
    
    try {
        # Получаем информацию о коммитах
        $localCommit = (git rev-parse HEAD 2>$null).Substring(0, 8)
        $localMessage = git log -1 --pretty=format:"%s" 2>$null
        
        # Обновляем remote информацию
        git fetch origin 2>$null | Out-Null
        $remoteCommit = (git rev-parse origin/main 2>$null).Substring(0, 8)
        $remoteMessage = git log -1 --pretty=format:"%s" origin/main 2>$null
        
        # Проверяем статус файлов
        $statusOutput = git status --porcelain 2>$null
        $uncommittedFiles = if ($statusOutput) { ($statusOutput | Measure-Object).Count } else { 0 }
        
        # Проверяем ahead/behind
        $revList = git rev-list --left-right --count origin/main...HEAD 2>$null
        if ($revList) {
            $behind, $ahead = $revList.Split("`t")
        } else {
            $behind, $ahead = 0, 0
        }
        
        return @{
            LocalCommit = $localCommit
            LocalMessage = $localMessage
            RemoteCommit = $remoteCommit
            RemoteMessage = $remoteMessage
            UncommittedFiles = [int]$uncommittedFiles
            Behind = [int]$behind
            Ahead = [int]$ahead
            InSync = ($localCommit -eq $remoteCommit)
        }
    }
    catch {
        Write-Status "Error getting git status: $($_.Exception.Message)" "ERROR"
        return $null
    }
}

function Show-StatusReport {
    Write-Banner "$Script:ProjectName - Sync Status"
    
    Write-Host "💻 Computer: $Script:ComputerName" -ForegroundColor Cyan
    Write-Host "📅 Check time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "📂 Directory: $(Get-Location)" -ForegroundColor Cyan
    Write-Host ""
    
    $status = Get-GitStatus
    if (-not $status) {
        return $false
    }
    
    Write-Host "🏠 Local commit:  $($status.LocalCommit) - $($status.LocalMessage)" -ForegroundColor White
    Write-Host "☁️  Remote commit: $($status.RemoteCommit) - $($status.RemoteMessage)" -ForegroundColor White
    Write-Host ""
    
    # Анализ статуса
    if ($status.InSync) {
        Write-Status "UP TO DATE - Local version matches GitHub" "SUCCESS"
    } else {
        Write-Status "OUT OF SYNC - Synchronization required" "WARNING"
        
        if ($status.Behind -gt 0) {
            Write-Status "You are $($status.Behind) commit(s) behind remote" "WARNING"
            Write-Host "💡 Run: .\sync.ps1 pull" -ForegroundColor Yellow
        }
        
        if ($status.Ahead -gt 0) {
            Write-Status "You have $($status.Ahead) local commit(s) not pushed" "WARNING"
            Write-Host "💡 Run: .\sync.ps1 push" -ForegroundColor Yellow
        }
    }
    
    if ($status.UncommittedFiles -gt 0) {
        Write-Status "You have $($status.UncommittedFiles) uncommitted file(s)" "WARNING"
        Write-Host "💡 Run: .\sync.ps1 commit -Message \"Your commit message\"" -ForegroundColor Yellow
    }
    
    # Показываем последние коммиты
    Write-Host ""
    Write-Host "📜 Recent commits:" -ForegroundColor Cyan
    $recentCommits = git log -5 --pretty=format:"%h|%an|%ar|%s" origin/main 2>$null
    if ($recentCommits) {
        foreach ($commitLine in $recentCommits) {
            $hash, $author, $time, $message = $commitLine.Split('|', 4)
            $icon = if ($hash.StartsWith($status.LocalCommit.Substring(0, 7))) { "🟢" } else { "🔴" }
            Write-Host "   $icon $hash by $author ($time)" -ForegroundColor Gray
            Write-Host "      $message" -ForegroundColor DarkGray
        }
    }
    
    return $status
}

function Sync-Pull {
    Write-Banner "Pulling Latest Changes"
    
    try {
        Write-Status "Fetching remote changes..."
        git fetch origin
        
        Write-Status "Pulling from origin/main..."
        $pullResult = git pull origin main 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Successfully pulled latest changes" "SUCCESS"
            return $true
        } else {
            Write-Status "Pull failed: $pullResult" "ERROR"
            return $false
        }
    }
    catch {
        Write-Status "Error during pull: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Sync-Commit {
    param([string]$CommitMessage)
    
    if (-not $CommitMessage) {
        $CommitMessage = "[$Script:ComputerName] Auto-commit $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    } else {
        $CommitMessage = "[$Script:ComputerName] $CommitMessage"
    }
    
    Write-Banner "Committing Changes"
    
    try {
        Write-Status "Adding all changes..."
        git add .
        
        Write-Status "Committing with message: $CommitMessage"
        git commit -m $CommitMessage
        
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Successfully committed changes" "SUCCESS"
            return $true
        } else {
            Write-Status "Nothing to commit or commit failed" "WARNING"
            return $false
        }
    }
    catch {
        Write-Status "Error during commit: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Sync-Push {
    Write-Banner "Pushing to GitHub"
    
    try {
        Write-Status "Pushing to origin/main..."
        $pushResult = git push origin main 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Successfully pushed to GitHub" "SUCCESS"
            return $true
        } else {
            Write-Status "Push failed: $pushResult" "ERROR"
            return $false
        }
    }
    catch {
        Write-Status "Error during push: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Sync-Full {
    param([string]$CommitMessage)
    
    Write-Banner "Full Synchronization"
    
    $status = Get-GitStatus
    if (-not $status) {
        return $false
    }
    
    $success = $true
    
    # 1. Pull если есть изменения на remote
    if ($status.Behind -gt 0) {
        Write-Status "Pulling remote changes first..."
        $success = $success -and (Sync-Pull)
    }
    
    # 2. Commit если есть локальные изменения
    if ($status.UncommittedFiles -gt 0) {
        Write-Status "Committing local changes..."
        $success = $success -and (Sync-Commit -CommitMessage $CommitMessage)
    }
    
    # 3. Push если есть локальные коммиты
    $newStatus = Get-GitStatus
    if ($newStatus -and $newStatus.Ahead -gt 0) {
        Write-Status "Pushing local commits..."
        $success = $success -and (Sync-Push)
    }
    
    if ($success) {
        Write-Status "Full synchronization completed successfully" "SUCCESS"
    } else {
        Write-Status "Some operations failed during synchronization" "ERROR"
    }
    
    return $success
}

# Главная логика скрипта
switch ($Action.ToLower()) {
    "check" {
        $status = Show-StatusReport
        if ($status -and -not $status.InSync) {
            exit 1
        }
    }
    
    "pull" {
        Sync-Pull
    }
    
    "commit" {
        Sync-Commit -CommitMessage $Message
    }
    
    "push" {
        Sync-Push
    }
    
    "sync" {
        Sync-Full -CommitMessage $Message
    }
    
    default {
        Write-Host ""
        Write-Host "PATRIOT Sync Tool - Usage:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  .\sync.ps1 check                    - Check sync status" -ForegroundColor White
        Write-Host "  .\sync.ps1 pull                     - Pull latest changes" -ForegroundColor White
        Write-Host "  .\sync.ps1 commit -Message \"text\"   - Commit local changes" -ForegroundColor White
        Write-Host "  .\sync.ps1 push                     - Push to GitHub" -ForegroundColor White
        Write-Host "  .\sync.ps1 sync -Message \"text\"     - Full sync (pull + commit + push)" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Cyan
        Write-Host "  .\sync.ps1 commit -Message \"Fixed order execution bug\"" -ForegroundColor Gray
        Write-Host "  .\sync.ps1 sync -Message \"Daily progress update\"" -ForegroundColor Gray
        Write-Host ""
    }
}
