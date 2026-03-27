Write-Host " Activating ChordStrikers signing environment..."

# 1. Clear all keys
ssh-add -D | Out-Null

# 2. Add your project-local key
$projectKey = "$env:USERPROFILE\.ssh\id_ed25519_project_local"
ssh-add $projectKey | Out-Null

# 3. Show the active key
Write-Host "✔ Loaded signing key:"
ssh-add -l

Write-Host " ChordStrikers signing key active."
