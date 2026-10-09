# swarm-harvester-data

An hourly copy of the public identity.md launch reward data on Ethereum mainnet, for the [Swarm Harvester](https://harvest.sites.imd.fun) site.

The IMD reward APIs (`explorer.imd.fun/api/earned`, `/api/claim`) don't send CORS headers, so static sites can't read them in the browser. This repo republishes the same data through `raw.githubusercontent.com`, which does send them. The site tries the IMD APIs first and falls back to this snapshot only when they refuse the request.

- `data/wallets/<address>.json`: the launches a wallet has an allocation in, newest first, with each Merkle proof. The site's import format is `{earned, claims}`.
- `data/launches/<id>.json`: the launch record fields the site uses: id, number, status, chain and artifacts.
- `data/trees/<id>.json`: the cached Merkle tree of each live launch. Trees are frozen once live, so each one is fetched only once.
- `data/index.json`: when the snapshot last ran.

The snapshot lists allocations, not claim status. The site checks `claimed(round, account)` on chain and simulates every claim before offering it, so a stale or wrong entry can't cause a bad claim. It only shows up as "claimed" or "unavailable".

Updated by `.github/workflows/snapshot.yml` every hour, running `scripts/snapshot.py`. Source: `https://api.imd.fun`.
