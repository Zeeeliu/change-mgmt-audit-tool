import requests
import random
import pandas as pd
from datetime import datetime


def github_api_request(endpoint, token):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f'https://api.github.com{endpoint}', headers=headers)
    return response.json()


def audit_repository(owner, repo, token):
    # Define audit period: September 2023 - August 2024
    start_date = datetime(2023, 9, 1)
    end_date = datetime(2024, 9, 7)

    # Get today's date
    today_date = datetime.now().strftime("%Y-%m-%d")

    # Get all pull requests
    pulls = github_api_request(f'/repos/{owner}/{repo}/pulls?state=all', token)

    # Filter pull requests within the audit period
    pulls_within_audit_period = [
        pr for pr in pulls
        if start_date <= datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ") <= end_date
    ]

    total_pull_requests = len(pulls_within_audit_period)

    # Print header documentation
    print(f"Change Management Testing\n"
          f"Testing Date: {today_date}\n"
          f"Github Repo Tested: {repo}\n"
          f"Audit Period: September 2023 - August 2024\n"
          f"Total number of pull requests during audit period: {total_pull_requests}\n"
          f"Number of pull requests sampled for testing: {min(total_pull_requests, 25)}\n")

    # Audit branch protection
    branch_protection = github_api_request(f'/repos/{owner}/{repo}/branches/main/protection', token)
    branch_protection_enabled = 'required_status_checks' in branch_protection

    # Randomly select up to 25 pull requests
    sample_size = min(25, total_pull_requests)
    sampled_pulls = random.sample(pulls_within_audit_period, sample_size)

    # Collect information for audit workpaper
    audit_results = []
    passed_tests = 0
    failed_tests = 0

    for i, pr in enumerate(sampled_pulls, start=1):
        pr_number = pr['number']
        pr_description = pr['title']
        pr_url = pr['html_url']  # Get the PR URL
        pr_created_at = pr['created_at']
        requestor = pr['user']['login']

        # Get details about the PR including the number of commits
        pr_details = github_api_request(f'/repos/{owner}/{repo}/pulls/{pr_number}', token)
        pr_merged_at = pr_details['merged_at']  # Merged date (deployment)
        pr_commits = pr_details['commits']  # Number of commits in the PR

        # Get reviews for this pull request
        reviews = github_api_request(f'/repos/{owner}/{repo}/pulls/{pr_number}/reviews', token)
        review_performed = 'Yes' if reviews else 'No'
        review_date = reviews[0]['submitted_at'] if reviews else 'N/A'
        reviewer = reviews[0]['user']['login'] if reviews else 'N/A'

        # Check if the reviewer and requestor are the same person, or set to "N/A" if no review was performed
        reviewer_same_as_requestor = 'N/A' if review_performed == 'No' else ('Yes' if requestor == reviewer else 'No')

        # Check if the review happened before the PR was merged (deployed)
        review_prior_to_pr_merge = 'N/A'
        if review_performed == 'Yes' and review_date and pr_merged_at:
            pr_merged_at_obj = datetime.strptime(pr_merged_at, "%Y-%m-%dT%H:%M:%SZ")
            review_date_obj = datetime.strptime(review_date, "%Y-%m-%dT%H:%M:%SZ")
            review_prior_to_pr_merge = 'Yes' if review_date_obj <= pr_merged_at_obj else 'No'

        # Determine if the test passes or fails
        if (review_performed == 'Yes' and
                reviewer_same_as_requestor == 'No' and
                review_prior_to_pr_merge == 'Yes' and
                branch_protection_enabled):
            test_result = 'Pass'
            passed_tests += 1
        else:
            test_result = 'Fail'
            failed_tests += 1

        audit_results.append([
            i,
            pr_description,
            pr_url,  # Add PR URL to the audit results
            'Yes' if branch_protection_enabled else 'No',
            pr_created_at,
            requestor,
            pr_commits,  # Number of commits in the PR
            review_performed,
            review_date,
            review_prior_to_pr_merge,
            reviewer_same_as_requestor,
            test_result
        ])

    # Convert audit results to a pandas DataFrame
    columns = [
        'Sample No.', 'PR Description', 'PR URL', 'Branch Protection?',
        'PR Creation Date', 'Requestor', 'Commits in PR', 'Review Performed?',
        'Review Date', 'Review Prior to PR Merge?', 'Reviewer Same as Requestor?', 'Test Result'
    ]

    df_audit = pd.DataFrame(audit_results, columns=columns)

    # Export the DataFrame to a CSV file
    csv_filename = f'audit_results_{repo}_{today_date}.csv'
    df_audit.to_csv(csv_filename, index=False)

    # Print success message
    print(f"Audit results exported to {csv_filename}")

    # Print the final testing result
    print(f"Testing Results: {passed_tests} passed, {failed_tests} failed\n")

    # Print audit workpaper
    print(f"{'Sample No.':<15} | {'PR Description':<35} | {'PR URL':<70} | {'Branch Protection?':<20} | "
          f"{'PR Creation Date':<25} | {'Requestor':<20} | {'Commits in PR':<15} | {'Review Performed?':<20} | "
          f"{'Review Date':<20} | {'Review Prior to PR Merge?':<30} | {'Reviewer Same as Requestor?':<30} | {'Test Result':<10}")
    print("-" * 360)

    for result in audit_results:
        print(f"{result[0]:<15} | {result[1]:<35} | {result[2]:<70} | {result[3]:<20} | "
              f"{result[4]:<25} | {result[5]:<20} | {result[6]:<15} | {result[7]:<20} | "
              f"{result[8]:<20} | {result[9]:<30} | {result[10]:<30} | {result[11]:<10}")



# token
# owner
# repo

audit_repository(owner, repo, token)
