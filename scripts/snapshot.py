"""Rebuild the Swarm Harvester reward snapshot from the public IMD API.

Each launch's Merkle tree is frozen once it is live, so trees are fetched once
and cached under data/trees/. Wallet files are rebuilt from the cache each run.
"""
import json
import os
import shutil
import time
import urllib.request
from datetime import datetime, timezone

API = "https://api.imd.fun"
CHAIN_ID = 1
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def get(url, tries=8):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "swarm-harvester-snapshot"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    os.replace(tmp, path)


def main():
    launches = get(f"{API}/launches?limit=500")["launches"]
    live = [
        l for l in launches
        if l["status"] == "live" and l["chainId"] == CHAIN_ID
        and any(a["role"] == "distributor" for a in l.get("artifacts", []))
    ]
    trees_dir = os.path.join(ROOT, "trees")
    fetched = 0
    for l in live:
        path = os.path.join(trees_dir, l["id"] + ".json")
        if os.path.exists(path):
            continue
        full = get(f"{API}/launches/{l['id']}?claims=1")
        claims = full.get("claims") or {}
        if not claims.get("root") or not claims.get("leaves"):
            continue  # tree not published yet; try again next run
        write(path, {
            "record": {
                "id": full["id"],
                "launchNumber": full.get("launchNumber"),
                "status": full["status"],
                "chainId": full["chainId"],
                "artifacts": [
                    {k: a.get(k) for k in ("role", "address", "txHash", "blockNumber")}
                    for a in full["artifacts"]
                ],
            },
            "root": claims["root"],
            "leaves": [[x["wallet"].lower(), x["amount"], x["proof"]] for x in claims["leaves"]],
        })
        fetched += 1
        time.sleep(0.5)

    live_ids = {l["id"] for l in live}
    # Newest launches first, so the site checks them before older ones.
    order = {l["id"]: l.get("launchNumber") or 0 for l in live}
    wallets = {}
    launch_out = os.path.join(ROOT, "launches.tmp")
    wallet_out = os.path.join(ROOT, "wallets.tmp")
    shutil.rmtree(launch_out, ignore_errors=True)
    shutil.rmtree(wallet_out, ignore_errors=True)
    for name in os.listdir(trees_dir) if os.path.isdir(trees_dir) else []:
        tree = json.load(open(os.path.join(trees_dir, name)))
        lid = tree["record"]["id"]
        if lid not in live_ids:
            continue
        write(os.path.join(launch_out, lid + ".json"), tree["record"])
        for wallet, amount, proof in tree["leaves"]:
            wallets.setdefault(wallet, {})[lid] = {"root": tree["root"], "amount": amount, "proof": proof}
    for wallet, claims in wallets.items():
        ids = sorted(claims, key=lambda i: -order.get(i, 0))
        write(os.path.join(wallet_out, wallet + ".json"), {
            "earned": {"claimable": ids, "unlocks": []},
            "claims": {i: {"claim": claims[i]} for i in ids},
        })
    for final, tmp in (("launches", launch_out), ("wallets", wallet_out)):
        dest = os.path.join(ROOT, final)
        shutil.rmtree(dest, ignore_errors=True)
        os.replace(tmp, dest)
    write(os.path.join(ROOT, "index.json"), {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chainId": CHAIN_ID,
        "launches": len(live_ids),
        "wallets": len(wallets),
    })
    print(f"launches={len(live_ids)} new_trees={fetched} wallets={len(wallets)}")


if __name__ == "__main__":
    main()
