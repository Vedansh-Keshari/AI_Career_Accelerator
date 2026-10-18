# FAANG level code with Claude Code

## Intro
1. full python application ( production ready that companies pay for )
2. sleek Streamlit interface
3. Built in minutes (~days~)
4. Claude - Autonomous coding agent (~chatbot~ , ~code assistant~) for fully functional applications from a single prompt
- writes
- tests
- debugs
- ships
5. Goal Example : Build an Employee Onboarding Automation System
- Python backend
- Streamlit frontend
- AI integration
- Handles errors
- Runs the app locally for Testing
6. Claude Code ~copying templates~ , ~manual coding~ , ~debugging nightmares~ , only production grade automation

## Avatar What Future of Coding Looks like
1. Real, production ready application (~simple demo~) with a single well-structured prompt
2. Streamlit application
- Business Logic
- Clean Structure
- Working user interface
3. Claude Code helps us focus on Ideas and System Design, instead of 
- Boiler plate
- setting-up files
- wiring everything together manually
4. Onboarding systems, Dashboards, Automation Tools, Internal platforms

## Avatar Watch your App in action
1. streamlit run app.py 		(simplest command)
2. python -m streamlit run app.py	(environment or path issues)
3. Local URL :  ,  Network URL :
4. Up and running -> AI powered employee onboarding system
- Description (About)
- Features
- Instructions
5. Click on “Generate” and review the complete onboarding package
6. Inputs: Name, Role, Department
7. Outputs: Welcome Email, 7-day Onboarding Plan (mapped to roles, departments & sectors), Required Documents Checklist (based on roles and departments), IT Access Checklist (Base Access & Department-specific Access based on role)

## How One File Powers the Whole Application
1. app.py > 
- import streamlit as st
- from datetime import datetime, timedelta
- \# Page configuration > page_title, page_icon, layout
- \# Title and description > title, markdown
- \# Input section > header, multiple columns (defining roles, departments and other selections)
- \# Submit button > Onboarding plan generation is triggered , error message if all other above required fields are not filled correctly
2. FAQ Section in the app as mentioned in the original prompt, each question has predefined answer clearly mapped in the code
3. General Training Resources and Learning Materials assigned to each role
4. Everything (implementation) works exactly as expected based on the original System Design.

## From Prompt to GitHub Repo Automatically
- Claude can directly push changes to GitHub as a separate branch until you allow to merge it to the main branch

## Don’t Skip This README (It’s Powerful)
1. Intro
> A comprehensive Streamlit application that automates and streamlines the employee onboarding process by generating personalized onboarding packages.
2. Features (brief description for each feature)
3. Requirements (packages, libraries and language versions needed)
4. Installation (walks us through the basic steps, also provides necessary commands)
5. Usage (commands, localhost setup, steps to run)
6. Supported Roles
7. Supported Departments
8. Application Structure
9. How it works (overall repository layout)
10. Screenshots (what the app features in itself –> Live Demo)
11. Contributing (guidelines for making contributions)
12. License (essentials)

## This Prompt Made Claude Build Everything
1. Think in Systems (~syntax~) #vibe_coding
2. Using our prompt, Claude gives itself a to-do list to complete and accomplish everything that we have asked it to do

## Watch AI Turn Prompts into Real Code
1. Connect Claude with GitHub and choose project and branch accordingly
2. Paste the detailed modular prompt in Claude to make the app
3. No external API , python only, Streamlit for UI
4. Model : Sonnet

## Stop Wasting Time - Use These Commands
1. Starting Claude Code
- claude 				: start interactive session
- claude “your question” 	: start with an initial prompt
- claude -c 			: continue your recent conversation
- claude -r “session-name” 	: resume a specific session
2. Key Slash Commands
a. session and conversation control
- /help 	: get help with Claude Code
- /clear 	: clear conversation history
- /resume	: resume previous sessions
- /rewind	: undo changes to code or conversation
- /export	: export conversation
- /copy	: copy the last response to clipboard
b. context and memory management
- /compact	: summarize conversation to free context
- /context	: visualize what’s in the context window
- /memory	: view or edit CLAUDE.md project memory
c. model and performance controls
- /model 	: switch ai models ( Haiku / Sonnet / Opus ) ( fastest, lightest / balanced / heavy reasoning specialist )
- /effort	: adjust reasoning depth (low->max)
- /fast	: toggle fast output mode
- /cost , /usage	: view token usage and limits
d. project setup and configuration
- /init		: generate a started CLAUDE.md
- /permissions	: manage tool permissions
- /add-dir		: add another directory for Claude to access
- /config 		: open settings ( theme, defaults, editor mode )
e. code editing and review tools
- /diff			: view uncommitted changes
- /code-review		: review code for bugs or improvements
- /simplify			: Cleanup-only review for efficiency
- /security-review	: scan for security issues
- /plan			: enter read-only plan mode before making changes
f. parallel work and agents
- /tasks		: view background tasks
- /agents		: manage subagents
- /background	: run session as a background agent
g. troubleshooting and diagnostics
- /doctor 	: diagnose installation and environment problems
- /debug	: investigate runtime issues
- /status	: show model, version, and working directory info
3. Critical Keyboard Shortcuts
- ctrl + C	: cancel current operation
- ctrl + D	: exit Claude Code
- ctrl + G	: open in text editor
- ctrl + L	: clear screen
- ctrl + V	: paste images from clipboard
- ctrl + B	: move tasks to background
- shift + tab , alt + M : toggle permission modes
- \ + Enter	: start multiline input
4. Quick Input Modes
- /command 	: run slash commands
- !command	: run bash commands directly
- @path	: file path autocomplete
5. Useful Flags
- --model opus/sonnet/haiku	: choose ai model
- --permission-mode plan/auto/ask	: set permission level
- --tools “Bash,Read,Edit”	: restrict available tools
6. extra features
- Run /help within Claude Code
- Type / to see all available commands
- Press ? to see keyboard shortcuts

## Building a Real Project with Claude Code
1. Simple onboarding application
2. Real usable outputs 
3. Inputs : Employee Name, Role, Department
4. Outputs : Welcome Email, (structured) 7-day onboarding plan, Required Documents Checklist (that HR needs to collect), IT Access Checklist, FAQs, Training Resources (relevant)
5. Technical Requirements : python only, streamlit for ui, no external APIs
6. Easy to understand , Easy to modify , Easy to extend later

## Behind the Scenes-Claude Code Interface

