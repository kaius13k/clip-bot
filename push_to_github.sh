#!/bin/bash

# 🚀 Push AI Agent YouTube Automation System to GitHub
# 
# Instructions:
# 1. First, create a new repository on GitHub.com:
#    - Go to https://github.com/new
#    - Repository name: ai-agent-youtube-automation (or your preferred name)
#    - Description: "Autonomous AI Agent System with YouTube Content Automation - Generate Revenue 24/7"
#    - Set to Public (recommended for showcasing)
#    - Don't initialize with README, .gitignore, or license (we already have them)
#    - Click "Create repository"
#
# 2. Replace 'YOUR_USERNAME' with your GitHub username
# 3. Replace 'YOUR_REPO_NAME' with your repository name
# 4. Run this script: ./push_to_github.sh

echo "🚀 Pushing AI Agent System to GitHub..."

# Set your GitHub details here:
GITHUB_USERNAME="YOUR_USERNAME"          # Replace with your GitHub username
REPO_NAME="ai-agent-youtube-automation"  # Replace with your repository name

# Construct the GitHub URL
GITHUB_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo "📡 Adding GitHub remote..."
git remote add origin $GITHUB_URL 2>/dev/null || git remote set-url origin $GITHUB_URL

echo "🔄 Pushing to GitHub..."
git branch -M main  # Rename branch to main
git push -u origin main

echo ""
echo "✅ SUCCESS! Your AI Agent System is now on GitHub!"
echo ""
echo "🌟 Repository URL: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo ""
echo "🎯 Next Steps:"
echo "   1. Visit your repository and verify everything uploaded correctly"
echo "   2. Update the README.md badge URLs to point to your repository"
echo "   3. Consider adding GitHub Actions for automated testing/deployment"
echo "   4. Add any collaborators if working on a team"
echo "   5. Star your own repository to boost visibility! ⭐"
echo ""
echo "💰 Ready to generate revenue with AI automation!"
echo ""

# Optional: Open the repository in the browser
# Uncomment the next line if you want to automatically open the repo
# xdg-open "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}" 2>/dev/null || open "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}" 2>/dev/null