# AI-Powered Feedback Setup Guide

The RHCSA Simulator now includes **optional AI-powered feedback** to help you learn faster and pass your exam with confidence.

## What Does AI Feedback Do?

The AI agent provides intelligent, contextual feedback during practice sessions:

- **Line-by-line analysis**: Tracks every command you run and analyzes your approach
- **Intelligent failure explanations**: Explains WHY a validation check failed, not just that it failed
- **Approach comparison**: Compares your solution to optimal approaches
- **Next-step suggestions**: Guides you when you're stuck
- **Personalized tips**: Provides RHCSA exam tips relevant to each task

## How It Works

1. **Command Tracking**: Analyzes your bash history during practice sessions
2. **Real-time Validation**: Checks your work against RHCSA requirements
3. **AI Analysis**: Uses Claude 3.5 Sonnet API to provide intelligent feedback
4. **Graceful Fallback**: Works without AI, but provides basic feedback only

## Setup Instructions

### Step 1: Get an Anthropic API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

**Cost**: Claude API is pay-as-you-go. Typical usage for RHCSA practice:
- ~$0.01-0.05 per practice session
- ~$1-5 per month of intensive practice
- First $5 often included as free credit

### Step 2: Install Anthropic Python Package

```bash
# Activate your virtual environment if using one
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install anthropic package
pip install anthropic>=0.7.0

# Or uncomment in requirements.txt and run:
# pip install -r requirements.txt
```

### Step 3: Set Environment Variable

**On Linux/RHEL (Persistent)**:
```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**On Linux/RHEL (Session Only)**:
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**On Windows (Persistent)**:
```cmd
setx ANTHROPIC_API_KEY "sk-ant-your-key-here"
# Restart terminal for changes to take effect
```

**On Windows (Session Only)**:
```cmd
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 4: Verify Setup

Run the simulator and check for AI status:

```bash
python main.py
# Select "Practice Mode" or "Enhanced Practice"
# Look for: "🤖 AI-powered feedback enabled"
```

If you see this message, AI feedback is working!

If you see: "💡 Set ANTHROPIC_API_KEY for AI-powered feedback", the API key is not detected.

## Usage

### In Enhanced Practice Mode

1. Start the simulator: `python main.py`
2. Select **"2) Practice Mode"** or **"3) Enhanced Practice"**
3. Choose a category and difficulty
4. Work on tasks normally
5. When you validate, AI feedback will automatically appear

### Example AI Feedback

**For Failed Tasks**:
```
🤖 AI ANALYSIS:
**What Went Wrong:**
The user account was created, but the UID specification was incorrect.
You used -u 2000 but the task required -u 2500.

**Root Cause:**
Incorrect flag value in useradd command.

**How to Fix:**
1. Delete the user: userdel -r testuser
2. Recreate with correct UID: useradd -u 2500 -m -s /bin/bash testuser
3. Verify: id testuser

**RHCSA Exam Tip:**
Always verify UID/GID with 'id' command after user creation.
```

**For Passed Tasks**:
```
🤖 AI FEEDBACK:
Good work! Your approach was correct and efficient. You used the standard
useradd flags in the right order. For the exam, remember you can also use
usermod to adjust settings after creation if you make a mistake.
```

## Features Enabled by AI

| Feature | Without AI | With AI |
|---------|-----------|---------|
| Basic validation | ✓ | ✓ |
| Pass/fail results | ✓ | ✓ |
| Hardcoded hints | ✓ | ✓ |
| Command tracking | ✓ | ✓ |
| Intelligent failure analysis | ✗ | ✓ |
| Approach comparison | ✗ | ✓ |
| Contextual explanations | ✗ | ✓ |
| Personalized tips | ✗ | ✓ |
| Next-step suggestions | ✗ | ✓ |

## Privacy & Security

- **Command data**: Only commands run during practice sessions are sent to Claude API
- **No system data**: System configurations, passwords, or sensitive data are NOT sent
- **No storage**: Anthropic does not store conversation data for API calls
- **Local validation**: All validation happens locally; AI only provides feedback

## Troubleshooting

### "ANTHROPIC_API_KEY not set" Warning

**Cause**: Environment variable not detected

**Fix**:
1. Verify key is set: `echo $ANTHROPIC_API_KEY` (Linux) or `echo %ANTHROPIC_API_KEY%` (Windows)
2. Restart terminal after setting environment variable
3. Check for typos in variable name

### "anthropic package not installed" Warning

**Cause**: Python package missing

**Fix**:
```bash
pip install anthropic
```

### "AI feedback generation failed" Error

**Possible causes**:
1. Invalid API key - verify key is correct
2. API rate limit exceeded - wait a few minutes
3. Network connectivity issues - check internet connection
4. API service down - check [Anthropic Status](https://status.anthropic.com/)

**Check logs**:
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python main.py
```

### AI Responses Are Slow

**This is normal**. AI feedback typically takes 2-5 seconds to generate. The simulator shows "Validating..." while waiting.

**To skip AI feedback**: Just press Enter when validation completes - you don't need to wait for AI analysis.

## Disabling AI Feedback

To practice without AI (simulating real exam conditions):

1. **Temporary**: Unset the environment variable
   ```bash
   unset ANTHROPIC_API_KEY  # Linux
   set ANTHROPIC_API_KEY=   # Windows
   ```

2. **Permanent**: Remove from ~/.bashrc or Windows environment variables

The simulator will automatically fall back to basic validation feedback.

## Cost Management

To minimize API costs while practicing:

1. **Use hints first**: Try the built-in 3-level hint system before validating
2. **Practice in exam mode**: Less frequent validation = fewer API calls
3. **Set a budget**: Monitor usage in Anthropic Console
4. **Disable for mastered topics**: Only use AI for categories you're struggling with

## Support

- **Simulator Issues**: Check logs with `LOG_LEVEL=DEBUG`
- **API Issues**: Visit [Anthropic Documentation](https://docs.anthropic.com/)
- **RHCSA Content**: Review task hints and learning content

## Exam Day Reminder

**IMPORTANT**: AI feedback is for practice ONLY. You will NOT have AI assistance during the actual RHCSA exam. Use this tool to:
- Learn WHY commands work, not just memorize them
- Understand common mistakes and how to avoid them
- Build confidence in your troubleshooting skills
- Practice the exam format without AI to test readiness

Good luck on your RHCSA exam!
