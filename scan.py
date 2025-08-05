import requests
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

# Configuration
TARGET_URL = "https://example.com"  # Replace with the target URL
REPORT_FILE = "vulnerability_report.txt"
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/1.0"
COMMON_DIRECTORIES = [
    "/admin/", "/administrator/", "/login/", "/wp-admin/", "/wp-includes/",
    "/backup/", "/backups/", "/db/", "/database/", "/sql/",
    "/uploads/", "/files/", "/media/", "/assets/", "/images/",
    "/config/", "/configuration/", "/conf/", "/settings/",
    "/tmp/", "/temp/", "/cache/", "/logs/",
    "/test/", "/testing/", "/dev/", "/staging/",
    "/.git/", "/.svn/", "/.env/", "/.htaccess/",
    "/private/", "/secure/", "/internal/"
]

# Function to log findings to a report file
def log_to_report(message):
    with open(REPORT_FILE, "a") as report:
        report.write(message + "\n")

# Step 1: Identify the technology stack
def get_tech_stack(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        tech = []
        if "wp-content" in str(soup):
            tech.append("WordPress")
        if "sites/default" in str(soup) or soup.find("meta", {"name": "generator", "content": lambda x: x and "Drupal" in x}):
            tech.append("Drupal")
        if "joomla" in str(soup).lower() or soup.find("meta", {"name": "generator", "content": lambda x: x and "Joomla" in x}):
            tech.append("Joomla")
        return tech
    except Exception as e:
        log_to_report(f"Error identifying tech stack: {e}")
        return []

# Step 2: Search NVD for known vulnerabilities
def search_nvd_for_vulnerabilities(tech_stack):
    vulnerabilities = []
    for tech in tech_stack:
        try:
            params = {"keyword": tech, "resultsPerPage": 10}
            response = requests.get(NVD_API_URL, params=params, timeout=5)
            if response.status_code != 200:
                log_to_report(f"NVD API returned status code {response.status_code} for {tech}")
                continue
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                log_to_report(f"Error parsing NVD response for {tech}: {e}")
                log_to_report(f"Response was: {response.text}")
                continue
            for vuln in data.get("result", {}).get("CVE_Items", []):
                cve_id = vuln["cve"]["CVE_data_meta"]["ID"]
                description = vuln["cve"]["description"]["description_data"][0]["value"]
                vulnerabilities.append({"cve_id": cve_id, "description": description})
        except Exception as e:
            log_to_report(f"Error searching NVD for {tech}: {e}")
    return vulnerabilities

# Step 3: Check for open directories with fuzzing
def check_open_directories(url):
    open_dirs = []
    base_dirs = COMMON_DIRECTORIES[:]
    fuzzed_dirs = []
    for directory in base_dirs:
        fuzzed_dirs.append(directory)
        dir_name = directory.strip("/")
        for i in range(1, 11):
            fuzzed_dirs.append(f"/{dir_name}{i}/")
        for year in range(2020, 2026):
            fuzzed_dirs.append(f"/{dir_name}-{year}/")
        for suffix in ["-bak", "-backup", "-old", "-test"]:
            fuzzed_dirs.append(f"/{dir_name}{suffix}/")

    for directory in fuzzed_dirs:
        try:
            response = requests.get(url + directory, timeout=5, allow_redirects=False)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=True)
            if "Index of" in response.text or len(links) > 5:
                if not soup.find("input", {"type": "password"}):
                    open_dirs.append(directory)
        except Exception as e:
            log_to_report(f"Error checking directory {directory}: {e}")
    return open_dirs

# Step 4: Check for external asset hosting and wildcard matches
def check_external_assets(url, open_dirs):
    external_hosts = []
    matched_assets = []
    wildcard_patterns = [
        r".*\.jpg$",
        r".*\.png$",
        r".*\.sql$",
        r".*\.bak$",
        r".*\.zip$",
        r"backup.*",
        r"config.*"
    ]
    regex_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in wildcard_patterns]

    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        tags = (
            soup.find_all("img", src=True) +
            soup.find_all("script", src=True) +
            soup.find_all("video", src=True) +
            soup.find_all("audio", src=True) +
            soup.find_all("link", href=True)
        )
        target_domain = urlparse(url).netloc
        for tag in tags:
            src = tag.get("src") or tag.get("href")
            if not src:
                continue
            full_url = urljoin(url, src)
            host = urlparse(full_url).netloc
            if host and host != target_domain and host not in external_hosts:
                if "s3.amazonaws.com" in host or "s3-" in host or "cloudfront.net" in host:
                    external_hosts.append(f"AWS ({host})")
                elif "cloudflare" in host:
                    external_hosts.append(f"Cloudflare ({host})")
                elif "akamai" in host:
                    external_hosts.append(f"Akamai ({host})")
                else:
                    external_hosts.append(host)
            for pattern in regex_patterns:
                if pattern.match(full_url):
                    matched_assets.append(full_url)

        for directory in open_dirs:
            try:
                response = requests.get(url + directory, timeout=5)
                if response.status_code != 200:
                    continue
                soup = BeautifulSoup(response.text, "html.parser")
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link["href"]
                    full_url = urljoin(url + directory, href)
                    for pattern in regex_patterns:
                        if pattern.match(full_url):
                            matched_assets.append(full_url)
            except Exception as e:
                log_to_report(f"Error checking assets in directory {directory}: {e}")

    except Exception as e:
        log_to_report(f"Error checking external assets: {e}")

    return external_hosts, matched_assets

# Main function
def main():
    log_to_report(f"--- Vulnerability Scan Report for {TARGET_URL} ---")
    log_to_report(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Step 1: Get technology stack
    tech_stack = get_tech_stack(TARGET_URL)
    if tech_stack:
        log_to_report(f"Identified Technologies: {', '.join(tech_stack)}")
        # Step 2: Search for vulnerabilities
        vulnerabilities = search_nvd_for_vulnerabilities(tech_stack)
        if vulnerabilities:
            log_to_report("\nKnown Vulnerabilities:")
            for vuln in vulnerabilities:
                log_to_report(f"- {vuln['cve_id']}: {vuln['description']}")
        else:
            log_to_report("\nNo known vulnerabilities found in NVD for the identified technologies.")
    else:
        log_to_report("No technologies identified.")

    # Step 3: Check for open directories
    open_dirs = check_open_directories(TARGET_URL)
    if open_dirs:
        log_to_report("\nOpen Directories Found:")
        for dir in open_dirs:
            log_to_report(f"- {TARGET_URL}{dir}")
    else:
        log_to_report("\nNo open directories found.")

    # Step 4: Check for external asset hosting and wildcard matches
    external_hosts, matched_assets = check_external_assets(TARGET_URL, open_dirs)
    if external_hosts:
        log_to_report("\nExternal Asset Hosts Found:")
        for host in external_hosts:
            log_to_report(f"- {host}")
    else:
        log_to_report("\nNo external asset hosts found.")
    if matched_assets:
        log_to_report("\nWildcard-Matched Assets Found:")
        for asset in matched_assets:
            log_to_report(f"- {asset}")
    else:
        log_to_report("\nNo wildcard-matched assets found.")

    log_to_report("\n--- End of Report ---")

if __name__ == "__main__":
    main()
