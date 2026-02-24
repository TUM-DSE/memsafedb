#!/usr/bin/env python3
import os
import requests
import json
import csv
import argparse
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

def parse_date(date_str):
    """Parse a YYYY-MM-DD string into an aware UTC datetime, or return None."""
    if not date_str:
        return None
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)

def load_tokens(token_file):
    tokens = {}
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    tokens[key.strip()] = value.strip()
    return tokens

class BugScraper(ABC):
    def __init__(self, name, output_dir, tokens=None, dry_run=False, start_date=None, end_date=None):
        self.name = name
        self.output_dir = output_dir
        self.tokens = tokens or {}
        self.dry_run = dry_run
        self.start_date = start_date
        self.end_date = end_date
        self.bugs_saved = 0
        self.session = requests.Session()
        self.data_dir = os.path.join(output_dir, name)
        os.makedirs(self.data_dir, exist_ok=True)

    def in_date_range(self, dt):
        """Return True if dt (aware UTC datetime) falls within [start_date, end_date]."""
        if dt is None:
            return True  # Can't filter without a date; let it through
        if self.start_date and dt < self.start_date:
            return False
        if self.end_date and dt > self.end_date:
            return False
        return True

    def parse_iso(self, s):
        """Parse an ISO 8601 string to aware UTC datetime, or return None."""
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None

    def save_bug(self, bug_id, data):
        if self.dry_run and self.bugs_saved >= 50:
            return False
        
        filename = os.path.join(self.data_dir, f"{bug_id}.json")
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.bugs_saved += 1
        print(f"\r[{self.name}] Scraped {self.bugs_saved} bugs", end='', flush=True)
        return True

    @abstractmethod
    def scrape(self):
        pass

class GitHubScraper(BugScraper):
    def __init__(self, name, repo_owner, repo_name, output_dir, tokens=None, dry_run=False, start_date=None, end_date=None):
        super().__init__(name, output_dir, tokens, dry_run, start_date, end_date)
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

    def scrape(self):
        print(f"[{self.name}] Starting GitHub scrape for {self.repo_owner}/{self.repo_name}...")
        if self.start_date:
            print(f"  Date filter: {self.start_date.date()} to {self.end_date.date() if self.end_date else 'now'}")
        headers = {'Accept': 'application/vnd.github.v3+json'}
        github_token = self.tokens.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f"token {github_token}"
        
        params = {
            'state': "closed",
            'per_page': 100,
            'page': 1,
            'sort': 'updated',
            'direction': 'asc'
        }

        # Use the GitHub 'since' param to skip issues created before start_date.
        # The API treats 'since' as updated_at >= date, but sorting by created asc
        # with since set to start_date is a good enough pre-filter.
        if self.start_date:
            params['since'] = self.start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Keep track of the 'since' timestamp for the CURRENT pagination window
        current_since = params.get('since')
        # Keep track of the latest timestamp seen in the current batch to be used for the NEXT window
        batch_last_updated = None
        
        while True:
            try:
                if current_since:
                    params['since'] = current_since
                
                response = self.session.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                issues = response.json()
                
                if not issues:
                    break
                
                for issue in issues:
                    if 'pull_request' in issue:
                        continue

                    batch_last_updated = issue['updated_at']

                    # Post-filter by created_at
                    created_at = self.parse_iso(issue.get('created_at'))
                    if not self.in_date_range(created_at):
                        continue
                    
                    bug_data = {
                        'id': issue['number'],
                        'title': issue['title'],
                        'status': issue['state'],
                        'created_at': issue['created_at'],
                        'body': issue['body'],
                        'labels': [l['name'] for l in issue['labels']],
                        'author': issue['user']['login'] if issue['user'] else None,
                        'url': issue['html_url'],
                        'raw': issue
                    }
                    if not self.save_bug(issue['number'], bug_data):
                        print(f"  [Dry Run] Reached limit of 50 bugs.")
                        return
                
                # Check for pagination
                if 'next' in response.links:
                   params['page'] += 1
                   
                   # Safe guard: If we are close to page 100, reset page and use 'since'.
                   if params['page'] >= 90:
                       params['page'] = 1
                       if batch_last_updated:
                           # Advance by 1 second to make the boundary exclusive,
                           # preventing the last item(s) from being re-fetched.
                           last_dt = self.parse_iso(batch_last_updated)
                           next_since = (last_dt + timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                           current_since = next_since
                       continue
                else:
                    break
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error fetching page {params['page']}: {e}")
                
                # If 422, it's likely the depth limit.
                if "422" in str(e):
                    params['page'] = 1
                    if batch_last_updated:
                        last_dt = self.parse_iso(batch_last_updated)
                        next_since = (last_dt + timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                        current_since = next_since
                    continue
                break

class JiraScraper(BugScraper):
    def __init__(self, name, base_url, project_key, output_dir, tokens=None, dry_run=False, start_date=None, end_date=None):
        super().__init__(name, output_dir, tokens, dry_run, start_date, end_date)
        self.base_url = base_url
        self.project_key = project_key
        self.api_url = f"{base_url}/rest/api/2/search"

    def scrape(self):
        print(f"[{self.name}] Starting Jira scrape for {self.project_key}...")
        if self.start_date:
            print(f"  Date filter: {self.start_date.date()} to {self.end_date.date() if self.end_date else 'now'}")
        start_at = 0
        max_results = 50

        # Build JQL date constraints
        jql_parts = [f'project={self.project_key}']
        if self.start_date:
            jql_parts.append(f'created >= "{self.start_date.strftime("%Y-%m-%d")}"')
        if self.end_date:
            jql_parts.append(f'created <= "{self.end_date.strftime("%Y-%m-%d")}"')
        jql = ' AND '.join(jql_parts) + ' ORDER BY created DESC'
        
        while True:
            params = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': max_results,
                'fields': 'summary,description,status,created,priority,comment,resolution,issuelinks'
            }
            
            try:
                response = self.session.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()
                issues = data.get('issues', [])
                
                if not issues:
                    break
                
                for issue in issues:
                    key = issue['key']
                    fields = issue['fields']
                    summary = fields.get('summary')
                    description = fields.get('description') or ""
                    
                    # Extract comments
                    comments = []
                    if 'comment' in fields and fields['comment']:
                        for c in fields['comment'].get('comments', []):
                            body = c.get('body')
                            if body:
                                comments.append(body)
                    
                    # Combine description and comments
                    full_text = description
                    if comments:
                        full_text += "\n\n--- Comments ---\n\n" + "\n\n".join(comments)

                    bug_data = {
                        'id': key,
                        'title': summary,
                        'status': (fields.get('status') or {}).get('name'),
                        'description': full_text,
                        'created': fields.get('created'),
                        'priority': (fields.get('priority') or {}).get('name'),
                        'raw': issue
                    }
                    if not self.save_bug(key, bug_data):
                        print(f"  [Dry Run] Reached limit of 50 bugs.")
                        return
                
                total = data.get('total', 0)
                start_at += len(issues)
                if start_at >= total:
                    break
                    
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error fetching Jira issues: {e}")
                break

class MySQLScraper(BugScraper):
    def __init__(self, name, output_dir, tokens=None, dry_run=False, start_date=None, end_date=None):
        super().__init__(name, output_dir, tokens, dry_run, start_date, end_date)
        self.base_url = "https://bugs.mysql.com/search.php"
        
    def scrape(self):
        print(f"[{self.name}] Starting MySQL scrape...")
        if self.start_date:
            print(f"  Date filter: {self.start_date.date()} to {self.end_date.date() if self.end_date else 'now'}")
        
        # Compute bug_age (days from today back to start_date) for MySQL's pre-filter.
        # Falls back to a large sentinel (10 years) if no start_date is set.
        if self.start_date:
            bug_age = (datetime.now(timezone.utc) - self.start_date).days + 1
        else:
            bug_age = 365 * 10

        csv_url = 'https://bugs.mysql.com/search-csv.php'
        params = {
            'status[]': 'All',
            'os': 0,
            'cpu_arch': 0,
            'bug_age': str(bug_age),
            'last_updated': 0,
            'order_by': 'id',
            'mine': 0,
            'begin': 0,
        }

        try:
            while True:
                print(f"  Fetching MySQL CSV index at begin={params['begin']}...")
                response = self.session.get(csv_url, params=params)
                response.raise_for_status()

                lines = response.text.splitlines()
                # First line is the header; skip it
                rows = lines[1:]
                if not rows:
                    break

                for row in rows:
                    if not row.strip():
                        continue
                    # CSV columns: ID,Entered,Modified,Type,Status,Severity,Version,OS,Summary
                    parts = next(csv.reader([row]))
                    bug_id = parts[0].strip()
                    entered_str = parts[1].strip() if len(parts) > 1 else ''

                    # Date pre-filter using the Entered timestamp from the CSV
                    if entered_str:
                        try:
                            entered_dt = datetime.strptime(entered_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                            if self.start_date and entered_dt < self.start_date:
                                continue
                            if self.end_date and entered_dt > self.end_date:
                                print(f"  End date filter reached.")
                                return
                        except ValueError:
                            pass

                    result = self.fetch_bug_details(bug_id, entered_str)
                    if not result:
                        print(f"  [Dry Run] Reached limit of 50 bugs.")
                        return
                    time.sleep(0.5)

                # Advance by the actual number of rows the server returned
                if not rows:
                    break
                params['begin'] += len(rows)
                time.sleep(1)

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"  [{self.name}] Rate-limited by MySQL server (403). Stopping CSV index fetch.")
            else:
                print(f"Error fetching MySQL CSV index: {e}")
        except Exception as e:
            print(f"Error fetching MySQL CSV index: {e}")


    def fetch_bug_details(self, bug_id, created_at=None):
        """Fetch and save a single MySQL bug. Returns False on dry-run limit, True otherwise."""
        url = f"https://bugs.mysql.com/bug.php?id={bug_id}"
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title
            title = "Unknown"
            header_title_row = soup.find('tr', id='title')
            if header_title_row:
                td = header_title_row.find('td')
                if td:
                    title = td.get_text(strip=True)
            if title == "Unknown":
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text

            # Extract comments/description
            comments = []
            comment_divs = soup.find_all('div', class_='comment')
            for div in comment_divs:
                text = div.get_text(separator="\n", strip=True)
                comments.append(text)
            description = "\n\n".join(comments)

            # Extract status
            status = "Unknown"
            status_th = soup.find('th', string=lambda text: text and 'Status:' in text)
            if status_th:
                status_td = status_th.find_next_sibling('td')
                if status_td:
                    status = status_td.get_text(strip=True)

            data = {
                'id': bug_id,
                'title': title,
                'status': status,
                'url': url,
                'description': description,
                'html_content': str(soup.find('div', id='content')),
                'created_at': created_at,
            }
            return self.save_bug(bug_id, data)
        except Exception as e:
            print(f"Failed to fetch bug {bug_id}: {e}")
            return True  # Continue even if fetch failed

class SQLiteScraper(BugScraper):
    def __init__(self, name, output_dir, tokens=None, dry_run=False, start_date=None, end_date=None):
        super().__init__(name, output_dir, tokens, dry_run, start_date, end_date)
        self.base_url = "https://sqlite.org/src/rptview"

    def scrape(self):
        print(f"[{self.name}] Starting SQLite scrape...")
        # SQLite uses Fossil. 
        # rptview?rn=1 gives list.
        # We can scrape the list.
        
        params = {'rn': 1}
        try:
            response = self.session.get(self.base_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Fossil tables
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 2:
                    # Usually: Ticket UUID (link), ...
                    link = cols[0].find('a')
                    if link:
                        href = link.get('href')
                        # href is like /src/info/UUID
                        uuid = href.split('/')[-1]
                        if not self.fetch_ticket(uuid):
                            print(f"  [Dry Run] Reached limit of 50 bugs.")
                            return
                        time.sleep(0.5)
        except Exception as e:
            print(f"Error scraping SQLite: {e}")

    def fetch_ticket(self, uuid):
        url = f"https://sqlite.org/src/info/{uuid}"
        # print(f"    Fetching {uuid}...")
        try:
            response = self.session.get(url)
            # Just save the raw HTML or text for now essentially
            # Parse SQLite ticket page
            # Content is often in <div class="ticket-body"> or similar, but structure can vary.
            # A good heuristic for Fossil is to grab text from the content area.
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find('div', class_='content')
            description = content.get_text(separator='\n') if content else response.text

            data = {
                'id': uuid,
                'url': url,
                'description': description,
                'raw_html': response.text
            }
            return self.save_bug(uuid, data)
        except:
            pass
        return True

def main():
    parser = argparse.ArgumentParser(description="Scrape DB bug reports")
    parser.add_argument('--output', required=True, help="Output directory in /scratch")
    parser.add_argument('--dry-run', action='store_true', help="Limit to 50 bugs per system")
    parser.add_argument('--start-date', default="2015-01-01", help="Only fetch bugs created on or after this date (YYYY-MM-DD)")
    parser.add_argument('--end-date', default="2025-12-31", help="Only fetch bugs created on or before this date (YYYY-MM-DD)")
    args = parser.parse_args()

    tokens = load_tokens("tokens.txt")

    output_dir = args.output
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    if start_date or end_date:
        print(f"Date filter: {start_date.date() if start_date else 'any'} → {end_date.date() if end_date else 'any'}")
    
    scrapers = [
        GitHubScraper('DuckDB', 'duckdb', 'duckdb', output_dir, tokens, args.dry_run, start_date, end_date),
        GitHubScraper('RocksDB', 'facebook', 'rocksdb', output_dir, tokens, args.dry_run, start_date, end_date),
        GitHubScraper('Redis', 'redis', 'redis', output_dir, tokens, args.dry_run, start_date, end_date),
        GitHubScraper('LevelDB', 'google', 'leveldb', output_dir, tokens, args.dry_run, start_date, end_date),
        JiraScraper('MongoDB', 'https://jira.mongodb.org', 'SERVER', output_dir, tokens, args.dry_run, start_date, end_date),
        JiraScraper('MariaDB', 'https://jira.mariadb.org', 'MDEV', output_dir, tokens, args.dry_run, start_date, end_date),
        MySQLScraper('MySQL', output_dir, tokens, args.dry_run, start_date, end_date),
        GitHubScraper('CockroachDB', 'cockroachdb', 'cockroach', output_dir, tokens, args.dry_run, start_date, end_date),
        GitHubScraper('ClickHouse', 'ClickHouse', 'ClickHouse', output_dir, tokens, args.dry_run, start_date, end_date),
        # SQLiteScraper('SQLite', output_dir, tokens, args.dry_run, start_date, end_date)
    ]

    for scraper in scrapers:
        try:
            scraper.scrape()
            print()
        except Exception as e:
            print(f"\nScraper {scraper.name} failed: {e}")

if __name__ == '__main__':
    main()
