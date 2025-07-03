#!/bin/bash

# BMMR Evaluation Script
# For automated API evaluation and result analysis

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored messages
print_colored() {
    echo -e "${1}${2}${NC}"
}

# Print separator
print_separator() {
    echo "============================================================"
}

# Print header
print_header() {
    print_separator
    print_colored "$CYAN" "  $1"
    print_separator
}

# Main function
main() {
    print_header "BMMR Evaluation Script"
    
    # Record start time
    start_time=$(date +%s)

    
    # Step 1: Run API evaluation
    print_header "Step 1/2: API Evaluation"
    print_colored "$BLUE" "🚀 Starting API evaluation..."
    
    python src/api_eval.py
    api_exit_code=$?
    
    if [ $api_exit_code -eq 0 ]; then
        print_colored "$GREEN" "✅ API evaluation completed"
    else
        print_colored "$RED" "❌ API evaluation failed (exit code: $api_exit_code)"
        exit 1
    fi
    
    # Step 2: Run result analysis
    print_header "Step 2/2: Result Analysis"
    print_colored "$BLUE" "📊 Starting result analysis..."
    
    python src/bmmr.py
    bmmr_exit_code=$?
    
    if [ $bmmr_exit_code -eq 0 ]; then
        print_colored "$GREEN" "✅ Result analysis completed"
    else
        print_colored "$RED" "❌ Result analysis failed (exit code: $bmmr_exit_code)"
        exit 1
    fi
    
    # Calculate total time
    end_time=$(date +%s)
    total_time=$((end_time - start_time))
    
    print_colored "$GREEN" "🎉 All evaluation tasks completed!"
    print_colored "$CYAN" "⏱️ Total time: ${total_time} seconds"
}

# Capture interrupt signal
trap 'print_colored "$RED" "❌ Script interrupted"; exit 1' INT

# Run main function
main "$@"