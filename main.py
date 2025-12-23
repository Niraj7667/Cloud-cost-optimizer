"""
Stage 4: CLI Orchestrator
Main entry point for the Cloud Cost Optimizer.
"""

import os
import sys
import json
from profile_generator import run_profile_extraction
from billing_engine import run_billing_generation
from analyzer import run_cost_analysis, display_report_summary, display_full_recommendations

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("\n" + "="*70)
    print(" " * 15 + "CLOUD COST OPTIMIZER - LLM POWERED")
    print(" " * 20 + "AI-Driven Infrastructure Cost Analysis")
    print("="*70)

def main():
    while True:
        clear_screen()
        print_header()
        
        print("\nMAIN MENU")
        print("-" * 70)
        print("1. Enter new project description.")
        print("2. Run Complete Cost Analysis.")
        print("3. View Recommendations.")
        print("4. Export Report.")
        print("5. Exit.")
        print("-" * 70)
        
        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            clear_screen()
            print_header()
            run_profile_extraction()
            input("\nPress Enter to continue...")

        elif choice == "2":
            clear_screen()
            print_header()
            
            # Check inputs
            if not os.path.exists("project_profile.json"):
                print("No profile found. Running Stage 1 first...")
                if not run_profile_extraction(): continue
            
            # Run Stage 2 & 3
            if run_billing_generation():
                run_cost_analysis()
            
            input("\nPress Enter to continue...")

        elif choice == "3":
            clear_screen()
            print_header()
            if os.path.exists("cost_optimization_report.json"):
                with open("cost_optimization_report.json", 'r') as f:
                    report = json.load(f)
                display_full_recommendations(report)
            else:
                print("No report found. Please run Option 2 first.")
            input("\nPress Enter to continue...")

        elif choice == "4":
            print("\nChecking artifacts...")
            files = ["project_description.txt", "project_profile.json", "mock_billing.json", "cost_optimization_report.json"]
            for f in files:
                status = "OK" if os.path.exists(f) else "MISSING"
                print(f"  {status} {f}")
            print(f"\nLocation: {os.getcwd()}")
            input("\nPress Enter to continue...")

        elif choice == "5":
            print("\nExiting...")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
