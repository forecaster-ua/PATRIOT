#!/usr/bin/env python3
"""
Version Check - Проверка актуальности локальной версии PATRIOT
=============================================================

Автоматически проверяет синхронизацию с GitHub репозиторием
и выдает рекомендации по обновлению.

Author: HEDGER
Version: 1.0
"""

import subprocess
import platform
import sys
from datetime import datetime
from pathlib import Path

class VersionChecker:
    """Проверяет актуальность версии проекта"""
    
    def __init__(self):
        self.computer_name = platform.node()
        self.timestamp = datetime.now()
    
    def run_git_command(self, cmd: list) -> tuple[bool, str]:
        """Выполняет git команду и возвращает результат"""
        try:
            result = subprocess.run(
                ['git'] + cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                cwd=Path.cwd()
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, f"Error: {e.stderr.strip() if e.stderr else str(e)}"
        except FileNotFoundError:
            return False, "Git not found. Please install Git."
    
    def get_local_commit(self) -> tuple[str, str]:
        """Получает информацию о локальном коммите"""
        success, output = self.run_git_command(['rev-parse', 'HEAD'])
        if success:
            commit_hash = output[:8]
            
            # Получаем сообщение коммита
            success_msg, commit_msg = self.run_git_command(['log', '-1', '--pretty=format:%s'])
            message = commit_msg if success_msg else "Unknown"
            
            return commit_hash, message
        return "UNKNOWN", "Unable to get local commit"
    
    def get_remote_commit(self) -> tuple[str, str]:
        """Получает информацию о удаленном коммите"""
        # Сначала обновляем информацию о remote
        success, _ = self.run_git_command(['fetch', 'origin'])
        if not success:
            return "FETCH_ERROR", "Cannot fetch from remote"
        
        # Получаем hash удаленного коммита
        success, output = self.run_git_command(['rev-parse', 'origin/main'])
        if success:
            commit_hash = output[:8]
            
            # Получаем сообщение удаленного коммита
            success_msg, commit_msg = self.run_git_command(['log', '-1', '--pretty=format:%s', 'origin/main'])
            message = commit_msg if success_msg else "Unknown"
            
            return commit_hash, message
        return "UNKNOWN", "Unable to get remote commit"
    
    def get_status_info(self) -> dict:
        """Получает дополнительную информацию о статусе"""
        info = {}
        
        # Проверяем есть ли незакоммиченные изменения
        success, output = self.run_git_command(['status', '--porcelain'])
        if success:
            uncommitted = len(output.strip().split('\n')) if output.strip() else 0
            info['uncommitted_files'] = uncommitted
        
        # Проверяем текущую ветку
        success, branch = self.run_git_command(['branch', '--show-current'])
        if success:
            info['current_branch'] = branch
        
        # Проверяем commits ahead/behind
        success, output = self.run_git_command(['rev-list', '--left-right', '--count', 'origin/main...HEAD'])
        if success and output:
            behind, ahead = output.split('\t')
            info['commits_behind'] = int(behind)
            info['commits_ahead'] = int(ahead)
        
        return info
    
    def get_recent_commits(self, count: int = 5) -> list:
        """Получает список последних коммитов"""
        success, output = self.run_git_command([
            'log', f'-{count}', '--pretty=format:%h|%an|%ar|%s', 'origin/main'
        ])
        
        if success and output:
            commits = []
            for line in output.split('\n'):
                if '|' in line:
                    hash_val, author, time, message = line.split('|', 3)
                    commits.append({
                        'hash': hash_val,
                        'author': author,
                        'time': time,
                        'message': message
                    })
            return commits
        return []
    
    def print_status_report(self):
        """Выводит полный отчет о статусе версии"""
        print("🔍 PATRIOT Version Sync Check")
        print("=" * 60)
        
        # Основная информация
        print(f"💻 Computer: {self.computer_name}")
        print(f"📅 Check time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Directory: {Path.cwd()}")
        
        # Получаем информацию о коммитах
        local_hash, local_msg = self.get_local_commit()
        remote_hash, remote_msg = self.get_remote_commit()
        status_info = self.get_status_info()
        
        print(f"\n📍 Current branch: {status_info.get('current_branch', 'unknown')}")
        print(f"🏠 Local commit:  {local_hash} - {local_msg}")
        print(f"☁️  Remote commit: {remote_hash} - {remote_msg}")
        
        # Анализ статуса
        print(f"\n📊 Status Analysis:")
        
        if local_hash == remote_hash:
            print("✅ STATUS: UP TO DATE")
            print("💚 Your local version matches GitHub")
        else:
            print("⚠️  STATUS: OUT OF SYNC")
            
            behind = status_info.get('commits_behind', 0)
            ahead = status_info.get('commits_ahead', 0)
            
            if behind > 0:
                print(f"📥 You are {behind} commit(s) behind remote")
                print("💡 Recommendation: git pull origin main")
            
            if ahead > 0:
                print(f"📤 You have {ahead} local commit(s) not pushed")
                print("💡 Recommendation: git push origin main")
        
        # Незакоммиченные изменения
        uncommitted = status_info.get('uncommitted_files', 0)
        if uncommitted > 0:
            print(f"📝 You have {uncommitted} uncommitted file(s)")
            print("💡 Recommendation: git add . && git commit")
        
        # Последние изменения в remote
        print(f"\n📜 Recent commits from GitHub:")
        recent_commits = self.get_recent_commits()
        
        if recent_commits:
            for commit in recent_commits[:3]:
                status_icon = "🔴" if commit['hash'] != local_hash[:7] else "🟢"
                print(f"   {status_icon} {commit['hash']} by {commit['author']} ({commit['time']})")
                print(f"      {commit['message']}")
        else:
            print("   ❌ Unable to fetch recent commits")
        
        print("=" * 60)
        
        # Быстрые команды
        if local_hash != remote_hash or uncommitted > 0:
            print("\n🚀 Quick sync commands:")
            if status_info.get('commits_behind', 0) > 0:
                print("   git pull origin main")
            if uncommitted > 0:
                print("   git add .")
                print("   git commit -m \"[Computer update from " + self.computer_name + "]\"")
            if status_info.get('commits_ahead', 0) > 0:
                print("   git push origin main")
            print()
    
    def check_and_exit(self) -> int:
        """Проверяет версию и возвращает exit code"""
        try:
            self.print_status_report()
            
            local_hash, _ = self.get_local_commit()
            remote_hash, _ = self.get_remote_commit()
            status_info = self.get_status_info()
            
            # Определяем exit code
            if local_hash == remote_hash and status_info.get('uncommitted_files', 0) == 0:
                return 0  # Все синхронизировано
            else:
                return 1  # Требуется синхронизация
        
        except Exception as e:
            print(f"❌ Error during version check: {e}")
            return 2  # Ошибка

def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
PATRIOT Version Checker

Usage:
  python version_check.py          - Show full status report
  python version_check.py --help   - Show this help

Exit codes:
  0 - Everything is up to date
  1 - Sync required
  2 - Error occurred
""")
        return 0
    
    checker = VersionChecker()
    return checker.check_and_exit()

if __name__ == "__main__":
    sys.exit(main())
