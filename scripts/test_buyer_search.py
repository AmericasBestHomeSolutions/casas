"""Address typeahead. Same cases as the English buyer-search tests.

    python3 scripts/test_buyer_search.py
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AddressTypeahead(unittest.TestCase):
    def test_address_typeahead_matches(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        script = r"""
const fs = require("fs");
const vm = require("vm");
const ctx = { console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync("buyer-search.js", "utf8"), ctx);
const homes = [
  { id: "oblong-il-807-illinois", address: "807 W Illinois St,", city: "Oblong", state: "IL", zip: "62449", status: "Available" },
  { id: "eastalton-il-136-illinois", address: "136 Illinois St", city: "East Alton", state: "IL", zip: "62024", status: "Available" },
  { id: "eaststlouis-il-541-27th", address: "541 North 27th Street", city: "East St. Louis", state: "IL", status: "Available" },
  { id: "springfield-il-1132-oak", address: "1132 E Oak St", city: "Springfield", state: "IL", status: "Pending" },
  { id: "decatur-il-1-main", address: "1 Main St", city: "Decatur", state: "IL", zip: "62526", status: "Available" },
  { id: "duquoin-il-322-cole", address: "322 S Cole St", city: "Du Quoin", state: "IL", status: "Available" }
];
const ids = (q) => ctx.BuyerSearch.matchAddresses(q, homes).map(h => h.id);
process.stdout.write(JSON.stringify({
  partial: ids("807 W Illinois"),
  mixed: ids("807 illinois oblong"),
  abbrev: ids("541 N 27th"),
  long: ids("541 north 27th st"),
  city: ids("Decatur"),
  zip: ids("62526"),
  none: ids("zzzz-not-a-home"),
  excluded: ids("322 cole"),
  pending: ids("1132 oak")
}));
"""
        out = subprocess.check_output([node, "-e", script], cwd=ROOT, text=True)
        data = json.loads(out)
        self.assertEqual(data["partial"], ["oblong-il-807-illinois"])
        self.assertEqual(data["mixed"], ["oblong-il-807-illinois"])
        self.assertEqual(data["abbrev"], ["eaststlouis-il-541-27th"])
        self.assertEqual(data["long"], ["eaststlouis-il-541-27th"])
        self.assertEqual(data["city"], [])
        self.assertEqual(data["zip"], [])
        self.assertEqual(data["none"], [])
        self.assertEqual(data["excluded"], [])
        self.assertEqual(data["pending"], ["springfield-il-1132-oak"])


if __name__ == "__main__":
    unittest.main()
