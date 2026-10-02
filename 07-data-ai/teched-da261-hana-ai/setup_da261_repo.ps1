# =============================================================================
# DA261 TechEd 2025 - HANA Cloud AI Capabilities
# Setup Script for sap-ai-journey Repository
# Author: Srinivasa Dasari
# =============================================================================

# Navigate to repo
cd C:\Users\nivas\repos\sap-ai-journey

# Create folder structure
Write-Host "Creating folder structure..." -ForegroundColor Green
mkdir teched-da261-hana-ai\docs -Force | Out-Null
mkdir teched-da261-hana-ai\exercises -Force | Out-Null

# Source path - adjust if downloaded elsewhere
$downloads = "$env:USERPROFILE\Downloads"

# Move README
Write-Host "Moving README..." -ForegroundColor Green
if (Test-Path "$downloads\DA261_Complete_README.md") {
    Move-Item "$downloads\DA261_Complete_README.md" "teched-da261-hana-ai\README.md" -Force
}

# Move documentation
Write-Host "Moving documentation..." -ForegroundColor Green
if (Test-Path "$downloads\DA261_Exercises_1_2_Complete_Lab_Guide.docx") {
    Move-Item "$downloads\DA261_Exercises_1_2_Complete_Lab_Guide.docx" "teched-da261-hana-ai\docs\" -Force
}
if (Test-Path "$downloads\DA261_Exercise3_Knowledge_Graph_Concepts.docx") {
    Move-Item "$downloads\DA261_Exercise3_Knowledge_Graph_Concepts.docx" "teched-da261-hana-ai\docs\" -Force
}

# Move Python scripts
Write-Host "Moving Python scripts..." -ForegroundColor Green
if (Test-Path "$downloads\ex1_outlier_detection.py") {
    Move-Item "$downloads\ex1_outlier_detection.py" "teched-da261-hana-ai\exercises\" -Force
}
if (Test-Path "$downloads\ex2_vector_search_classification.py") {
    Move-Item "$downloads\ex2_vector_search_classification.py" "teched-da261-hana-ai\exercises\" -Force
}

# Verify structure
Write-Host "`nFolder structure:" -ForegroundColor Cyan
Get-ChildItem -Path teched-da261-hana-ai -Recurse | Select-Object FullName

# Git commands
Write-Host "`nCommitting to Git..." -ForegroundColor Green
git add teched-da261-hana-ai/
git commit -m "Add TechEd 2025 DA261 - HANA Cloud AI Capabilities lab

- Exercise 1: PAL Isolation Forest for outlier detection on ACDOCA
- Exercise 2: TF-IDF vector search + Random Forest classification
- Exercise 3: Knowledge Graph concepts (RDF/SPARQL/GraphRAG)
- Includes Python scripts and comprehensive documentation"

git push

Write-Host "`n✅ DA261 lab pushed to sap-ai-journey repo!" -ForegroundColor Green
