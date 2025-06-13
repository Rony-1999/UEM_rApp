import requests
import logging
import time

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Load Balancing XApp')

# Constants
POLICY_VIEW_URL = 'http://10.33.42.120:5002/policies/view'
USAGE_THRESHOLD = 12  # No. of UEs

class LoadBalancingXApp:
    def __init__(self):
        self.logger = logger
        self.processed_policy_ids = set()  # Track already handled policies
        self.logger.info("Load Balancing XApp Initialized.")

    def fetch_created_policies(self):
        """Fetch created load balancing policies from the rApp."""
        try:
            response = requests.get(POLICY_VIEW_URL)
            if response.status_code == 200:
                policies = self.extract_json_from_html(response.text)
                self.logger.info(f"Fetched {len(policies)} created policies.")
                return policies
            else:
                self.logger.error(f"Failed to fetch policies. Status code: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Exception during policy fetch: {e}")
            return []

    def extract_json_from_html(self, html_content):
        """Parse HTML table from /policies/view and extract policies as dicts."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        if not table:
            self.logger.warning("No policies table found.")
            return []

        rows = table.find_all("tr")[1:]  # skip header
        policies = []
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            try:
                policies.append({
                    "ric_id": cols[0],
                    "policy_id": cols[1],
                    "service_id": cols[2],
                    "field": cols[3],
                    "value": float(cols[4]),
                    "threshold": float(cols[5]),
                    "policytype_id": int(cols[6])
                })
            except (IndexError, ValueError) as e:
                self.logger.warning(f"Error parsing policy row: {e}")
                continue
        return policies

    def offload_ue_to_neighbor(self, ric_id, ue_id="ue1", neighbor_cell="neighbor_cell_1"):
        """Simulate UE offload to a neighbor via E2 interface (stub)."""
        self.logger.info(f"[E2] Offloading UE {ue_id} from {ric_id} to {neighbor_cell}")
        # TODO: Replace with actual E2AP control interface logic

    def handle_policy(self, policy):
        """Handle a single policy (simulate UE redistribution)."""
        ric_id = policy["ric_id"]
        policy_id = policy["policy_id"]
        value = policy["value"]
        threshold = policy["threshold"]

        if value > threshold:
            self.logger.info(f"Handling policy {policy_id}: {ric_id} usage {value} > threshold {threshold}")
            self.offload_ue_to_neighbor(ric_id=ric_id)
        else:
            self.logger.info(f"Policy {policy_id} does not require action.")

    def main(self):
        """Main loop to poll and process created policies."""
        while True:
            policies = self.fetch_created_policies()
            for policy in policies:
                policy_id = policy.get("policy_id")
                if policy_id not in self.processed_policy_ids:
                    self.handle_policy(policy)
                    self.processed_policy_ids.add(policy_id)
                else:
                    self.logger.debug(f"Policy {policy_id} already handled.")

            time.sleep(30)


if __name__ == '__main__':
    xapp = LoadBalancingXApp()
    xapp.main()

