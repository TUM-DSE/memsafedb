#!/usr/bin/env python3
import os
import requests
import json
import argparse
import time
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

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
    def __init__(self, name, output_dir, tokens=None, dry_run=False):
        self.name = name
        self.output_dir = output_dir
        self.tokens = tokens or {}
        self.dry_run = dry_run
        self.bugs_saved = 0
        self.session = requests.Session()
        self.data_dir = os.path.join(output_dir, name)
        os.makedirs(self.data_dir, exist_ok=True)

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
    def __init__(self, name, repo_owner, repo_name, output_dir, tokens=None, dry_run=False):
        super().__init__(name, output_dir, tokens, dry_run)
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

    def scrape(self):
        print(f"[{self.name}] Starting GitHub scrape for {self.repo_owner}/{self.repo_name}...")
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
        
        # Keep track of the 'since' timestamp for the CURRENT pagination window
        current_since = None
        # Keep track of the latest timestamp seen in the current batch to be used for the NEXT window
        batch_last_updated = None
        
        while True:
            try:
                # Only apply 'since' if we have a window set
                if current_since:
                    params['since'] = current_since
                
                response = self.session.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                issues = response.json()
                
                if not issues:
                    break
                
                for issue in issues:
                    # Update batch_last_updated to the most recent issue in this batch
                    batch_last_updated = issue['updated_at']
                    
                    if 'pull_request' in issue:
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
                       current_since = batch_last_updated
                       continue
                else:
                    break
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error fetching page {params['page']}: {e}")
                
                # If 422, it's likely the depth limit.
                if "422" in str(e):
                    params['page'] = 1
                    current_since = batch_last_updated
                    continue
                break

class JiraScraper(BugScraper):
    def __init__(self, name, base_url, project_key, output_dir, tokens=None, dry_run=False):
        super().__init__(name, output_dir, tokens, dry_run)
        self.base_url = base_url
        self.project_key = project_key
        self.api_url = f"{base_url}/rest/api/2/search"

    def scrape(self):
        print(f"[{self.name}] Starting Jira scrape for {self.project_key}...")
        start_at = 0
        max_results = 50
        
        while True:
            params = {
                'jql': f'project={self.project_key} ORDER BY created DESC',
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
                        'status': fields.get('status', {}).get('name'),
                        'description': full_text,
                        'created': fields.get('created'),
                        'priority': fields.get('priority', {}).get('name'),
                        'raw': issue
                    }
                    if not self.save_bug(key, bug_data):
                        print(f"  [Dry Run] Reached limit of 50 bugs.")
                        return
                
                total = data.get('total', 0)
                start_at += len(issues)
                if start_at >= total:
                    break
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"Error fetching Jira issues: {e}")
                break

class MySQLScraper(BugScraper):
    def __init__(self, name, output_dir, tokens=None, dry_run=False):
        super().__init__(name, output_dir, tokens, dry_run)
        self.base_url = "https://bugs.mysql.com/search.php"
        
    def scrape(self):
        print(f"[{self.name}] Starting MySQL scrape...")
        # MySQL bugs are hard to scrape linearly without IDs.
        # We can search for recent bugs.
        # Simplified approach: Iterate recent IDs or use search.
        # Searching "All" returns a robust table.
        
        params = {
            'status': 'All',
            'search_for': '',
            'order_by': 'id',
            'severity': 'all',
            'cmd': 'display',
            'begin': 0,
            'limit': 50
        }
        
        try:
            while True:
                print(f"  Fetching MySQL bugs starting at {params['begin']}...")
                response = self.session.get(self.base_url, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # bugs.mysql.com uses status-based classes (e.g., "closed", "notabug") 
                # instead of "odd"/"even". We can reliably find bugs by looking for 
                # the 'td' with class 'id'.
                id_cells = soup.find_all('td', class_='id')
                if not id_cells:
                    break

                for cell in id_cells:
                    try:
                        bug_link = cell.find('a')
                        if bug_link:
                            bug_id = bug_link.text
                            if not self.fetch_bug_details(bug_id):
                                print(f"  [Dry Run] Reached limit of 50 bugs.")
                                return
                            time.sleep(1)
                    except Exception as e:
                        pass
                
                # Check if we should stop (if we got fewer results than the limit)
                if len(id_cells) < params['limit']:
                    break
                
                params['begin'] += params['limit']
                time.sleep(1)
                        
        except Exception as e:
            print(f"Error fetching MySQL list: {e}")

    def fetch_bug_details(self, bug_id):
        url = f"https://bugs.mysql.com/bug.php?id={bug_id}"
        # print(f"    Fetching {bug_id}...")
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract basic info from bugheader
            # Title is usually in the first row's td
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

            # Extract comments/description from divs with class "comment"
            # The first comment is usually the description
            comments = []
            comment_divs = soup.find_all('div', class_='comment')
            for div in comment_divs:
                # We extract text, preserving some structure if possible, but get_text is safest
                text = div.get_text(separator="\n", strip=True)
                comments.append(text)
            
            description = "\n\n".join(comments)

            # Extract status
            # Status is typically in the 2nd row after reporter/email, but lets look for "Status:" th
            status = "Unknown"
            status_th = soup.find('th', string=lambda text: text and 'Status:' in text)
            if status_th:
                # The next sibling td should be the status
                status_td = status_th.find_next_sibling('td')
                if status_td:
                    status = status_td.get_text(strip=True)

            data = {
                'id': bug_id,
                'title': title,
                'status': status,
                'url': url,
                'description': description,
                'html_content': str(soup.find('div', id='content')) 
            }
            return self.save_bug(bug_id, data)
        except Exception as e:
            print(f"Failed to fetch bug {bug_id}")
            return True # Continue even if fetch failed

class SQLiteScraper(BugScraper):
    def __init__(self, name, output_dir, tokens=None, dry_run=False):
        super().__init__(name, output_dir, tokens, dry_run)
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
                        time.sleep(1)
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
    args = parser.parse_args()

    tokens = load_tokens("tokens.txt")

    output_dir = args.output
    
    scrapers = [
        GitHubScraper('DuckDB', 'duckdb', 'duckdb', output_dir, tokens, args.dry_run),
        GitHubScraper('RocksDB', 'facebook', 'rocksdb', output_dir, tokens, args.dry_run),
        GitHubScraper('Redis', 'redis', 'redis', output_dir, tokens, args.dry_run),
        GitHubScraper('LevelDB', 'google', 'leveldb', output_dir, tokens, args.dry_run),
        GitHubScraper('CockroachDB', 'cockroachdb', 'cockroach', output_dir, tokens, args.dry_run),
        GitHubScraper('ClickHouse', 'ClickHouse', 'ClickHouse', output_dir, tokens, args.dry_run),
        JiraScraper('MongoDB', 'https://jira.mongodb.org', 'SERVER', output_dir, tokens, args.dry_run),
        
        JiraScraper('MariaDB', 'https://jira.mariadb.org', 'MDEV', output_dir, tokens, args.dry_run),
        MySQLScraper('MySQL', output_dir, tokens, args.dry_run),
        # SQLiteScraper('SQLite', output_dir, tokens, args.dry_run)
    ]

    for scraper in scrapers:
        try:
            scraper.scrape()
            print()
        except Exception as e:
            print(f"\nScraper {scraper.name} failed: {e}")

if __name__ == '__main__':
    main()
