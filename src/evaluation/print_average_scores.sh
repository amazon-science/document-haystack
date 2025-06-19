#!/bin/bash

# Define the list of Benchmarks
Benchmarks=(
    AIG AmericanAirlines APA BankOfMontreal Barclays
    BlackRock BNYMellon CapitalOne CitiGroup Cofinimmo
    CVS DWS Entain GoldmanSachs HSBC
    JPMorgan Kroger NewRiver PNC Reach
    Sagicor United UPS Vesuvius WoltersKluwer
)

# Define the list of NumPages values
NumPages=(5 10 25 50 75 100 150 200)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --results-path)
            RESULTS_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1" >&2
            exit 1
            ;;
    esac
done

# Set default results path if not provided
RESULTS_PATH=${RESULTS_PATH:-"Results"}

for N in "${NumPages[@]}"; do
        sum=0
        count=0
        for Benchmark in "${Benchmarks[@]}"; do
                score=$(tail -1 "${RESULTS_PATH}/${Benchmark}/${Benchmark}_${N}Pages/results_scores.txt" | awk '{print $NF}')
                sum=$(echo "$sum + $score" | bc)
                count=$((count + 1))
        done
        avg=$(echo "scale=10; ($sum / $count) * 100" | bc)
        avg_rounded=$(printf "%.1f" $avg)
        echo "Average score for ${N} pages: ${avg_rounded}% (${count} samples)"
done
