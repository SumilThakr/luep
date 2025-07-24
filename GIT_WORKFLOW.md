# Git Workflow for Land Use Emissions Processor

## What Gets Committed
- ✅ All Python source code (`*.py`)
- ✅ Documentation (`*.md`, `README.txt`)
- ✅ Configuration files (`*.yml`, `*.yaml`) 
- ✅ Small metadata files (`*.csv` in scenarios)
- ✅ Project structure and scripts

## What Gets Ignored (via .gitignore)
- ❌ Input data (`inputs/` - 15GB)
- ❌ Output results (`outputs/` - 11GB) 
- ❌ Intermediate files (`intermediate/` - 41GB)
- ❌ Cache files (`cache/` - 18GB)
- ❌ Large raster files (`*.tif`, `*.nc`, `*.h5`)
- ❌ Python cache (`__pycache__/`, `*.pyc`)
- ❌ System files (`.DS_Store`, etc.)
- ❌ Log files (`*.log`)

## Recommended Workflow

### Initial Setup
```bash
# Add all code files (data files automatically ignored)
git add .

# Commit the reorganized codebase
git commit -m "Reorganize scripts into logical folders

- Move 48+ scripts from main directory into subfolders
- Keep 14 core active scripts in root (main run scripts + UK batch processing)
- Create subfolders: testing/, specialized/, legacy/, analysis/, debug/, archive/
- Add comprehensive .gitignore for large data files
- Preserve all functionality while improving navigation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### For Future Changes
```bash
# Check what's changed (ignores data files)
git status

# Add specific files or all code changes
git add *.py  # Just Python files
# or
git add .     # All changes (data files ignored by .gitignore)

# Commit with descriptive message
git commit -m "Brief description of changes

Longer explanation if needed.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Repository Size Management
- **Before .gitignore**: ~85GB (data + code)
- **After .gitignore**: ~50MB (code only)
- **Storage savings**: >99% reduction

## Data Management
- Large data files remain local and untracked
- Share data separately (cloud storage, data repositories)
- Document data requirements in README.md
- Consider Git LFS for essential binary files if needed

## Key Benefits
1. **Fast operations** - No large file transfers
2. **Clean history** - Only code changes tracked
3. **Collaboration friendly** - Others can work with same code structure
4. **Backup efficiency** - Only important files in version control