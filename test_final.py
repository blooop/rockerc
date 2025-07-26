from rockerc.renv import get_all_repo_branch_combinations

combinations = get_all_repo_branch_combinations()
print(f"Found {len(combinations)} combinations")
print("First 5:")
for c in combinations[:5]:
    print(f"  {c}")
