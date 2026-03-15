# TASK-033 — OANDA Forex Connectivity & Real Account Pool Mapping

## Goal

Verify and fix the OANDA integration: data streaming for forex pairs, historical backfill, forex account pool with real OANDA sub-account mapping, and order execution through the OANDA practice API. After this task, forex data flows and paper trades execute through OANDA's sandbox with the account pool model enforcing FIFO netting constraints.

## Depends On

TASK-032 (Alpaca connectivity verified first — ensures base pipeline works)

## Scope

**In scope:**
- Verify OANDA streaming connection and authentication
- Verify forex pair data streams and persists
- Verify forex historical backfill
- Implement real OANDA account mapping for the forex pool (virtual → real sub-accounts)
- Verify forex pool allocation and release with real accounts
- Verify OANDA order execution through practice API
- Verify shadow tracking activates when pool accounts are contended
- Document OANDA connectivity in README runbook

**Out of scope:**
- Alpaca changes (done in TASK-032)
- Frontend changes
- Live (non-practice) OANDA accounts
- New trading strategies

---

## Deliverables

### D1 — Verify OANDA streaming connection

**Steps:**
1. Set OANDA credentials in `.env`:
   ```
   OANDA_ACCESS_TOKEN=your-practice-token
   OANDA_ACCOUNT_ID=your-main-account-id
   OANDA_BASE_URL=https://api-fxpractice.oanda.com
   OANDA_STREAM_URL=https://stream-fxpractice.oanda.com
   ```
2. Start backend
3. Check logs for OANDA stream connection
4. Verify forex pairs are subscribed (from watchlist)

**Expected log output:**
```
INFO  market_data.ws: OANDA stream connected
INFO  market_data.ws: Subscribed to N forex pairs
```

**If it fails:** Debug OANDA streaming API format. OANDA uses a different streaming protocol than Alpaca (HTTP streaming, not WebSocket). Check:
- Auth header format (`Authorization: Bearer <token>`)
- Stream URL construction (`/v3/accounts/{id}/pricing/stream?instruments=EUR_USD,GBP_USD`)
- Response parsing (OANDA sends JSON lines, not WebSocket frames)

### D2 — Verify forex data storage and backfill

**Steps:**
1. After OANDA connects, verify bar data persists
2. Query `GET /api/v1/market-data/bars?symbol=EUR_USD&timeframe=1m&limit=5`
3. Verify historical backfill for forex pairs
4. Check that OANDA candle endpoint is called correctly (`/v3/instruments/{pair}/candles`)

**Forex runs 24/5** — unlike equities, forex data should stream Sunday evening through Friday evening ET.

### D3 — Implement real OANDA account pool mapping

The forex pool currently uses virtual account IDs. For real OANDA trading (even practice), each virtual account needs to map to a real OANDA sub-account.

**Account pool config addition to `.env.example`:**

```env
# === Forex Account Pool — Real Account Mapping ===
# Comma-separated OANDA sub-account IDs mapping to pool accounts 1-4
# Each sub-account enforces FIFO netting (one direction per pair per account)
OANDA_POOL_ACCOUNT_1=
OANDA_POOL_ACCOUNT_2=
OANDA_POOL_ACCOUNT_3=
OANDA_POOL_ACCOUNT_4=
# Optional: per-account access tokens (if different from main)
OANDA_POOL_TOKEN_1=
OANDA_POOL_TOKEN_2=
OANDA_POOL_TOKEN_3=
OANDA_POOL_TOKEN_4=
```

**Implementation in pool manager:**

Add to the `ForexAccountPool` (or equivalent) class:

```python
def _load_real_accounts(self):
    """Map virtual pool accounts to real OANDA sub-account IDs."""
    for i in range(1, self.pool_size + 1):
        env_key = f"OANDA_POOL_ACCOUNT_{i}"
        account_id = os.environ.get(env_key, "")
        token_key = f"OANDA_POOL_TOKEN_{i}"
        token = os.environ.get(token_key, settings.oanda_access_token)
        
        if account_id:
            self.accounts[i].broker_account_id = account_id
            self.accounts[i].broker_token = token
            logger.info(f"Pool account {i} mapped to OANDA {account_id}")
        else:
            self.accounts[i].broker_account_id = f"virtual_{i}"
            logger.info(f"Pool account {i} using virtual mode (no OANDA mapping)")
```

**Key behavior:**
- If `OANDA_POOL_ACCOUNT_N` is set → that pool slot uses the real OANDA sub-account for order execution
- If not set → that pool slot uses internal simulation (current behavior)
- Mixed mode is valid (some real, some virtual) for gradual rollout
- The allocation logic (first_come, per-pair isolation) doesn't change

Add the pool account mapping variables to `.env.example` and the Settings class.

### D4 — Verify forex pool allocation with real accounts

**Steps:**
1. Configure at least one real OANDA sub-account in the pool
2. Create a forex strategy and enable it
3. When a signal is generated → verify pool allocates the correct account
4. Verify the OANDA executor uses the mapped sub-account ID for the order
5. Verify allocation release when position closes

**If OANDA sub-accounts aren't available for testing:**
- Verify the mapping code loads correctly from env vars
- Verify the executor receives the correct account ID
- Document that end-to-end verification requires real sub-accounts

### D5 — Verify OANDA order execution

**Steps:**
1. With pool account mapped to a real OANDA practice account
2. Route a forex signal through the pipeline
3. Verify order submitted to OANDA: `POST /v3/accounts/{pool_account_id}/orders`
4. Verify fill returns and position appears in portfolio

**OANDA order format:**
```json
{
  "order": {
    "type": "MARKET",
    "instrument": "EUR_USD",
    "units": "10000",
    "timeInForce": "FOK"
  }
}
```

**If it fails:**
- Check OANDA order API format (v20 API)
- Check account permissions on the practice account
- Check instrument naming (EUR_USD vs EUR/USD)

### D6 — Verify shadow tracking

**Steps:**
1. Fill all 4 pool accounts with the same forex pair (e.g., EUR_USD)
2. Generate a 5th EUR_USD signal
3. Verify the signal is rejected with `no_available_account`
4. Verify a shadow position is created
5. Verify shadow tracking records what would have happened

### D7 — OANDA runbook section in README

Add to the Operations Runbook:

```markdown
### Connecting OANDA (Forex)

1. Create an OANDA practice account at https://www.oanda.com
2. Generate an API access token in Account Settings → API Management
3. Note your practice account ID (format: 101-001-XXXXX-001)
4. For account pool: create additional sub-accounts (up to 4) in OANDA's interface
5. Add to `.env`:
   ```
   OANDA_ACCESS_TOKEN=your-token
   OANDA_ACCOUNT_ID=your-main-account-id
   OANDA_BASE_URL=https://api-fxpractice.oanda.com
   OANDA_STREAM_URL=https://stream-fxpractice.oanda.com
   
   # Pool accounts (one per sub-account)
   OANDA_POOL_ACCOUNT_1=101-001-XXXXX-001
   OANDA_POOL_ACCOUNT_2=101-001-XXXXX-002
   OANDA_POOL_ACCOUNT_3=101-001-XXXXX-003
   OANDA_POOL_ACCOUNT_4=101-001-XXXXX-004
   ```
6. Restart the backend
7. Forex data should stream immediately (24/5 market)

### Forex Account Pool

The system maintains a pool of 4 OANDA sub-accounts to handle FIFO netting constraints.
Each account can hold one position per pair. When all accounts holding a pair are full,
new signals for that pair are rejected and tracked as shadow positions.

### Troubleshooting Forex

- **No forex data streaming:** Verify OANDA token hasn't expired. Tokens may need periodic regeneration.
- **Orders rejected:** Check OANDA account has sufficient margin. Practice accounts start with virtual funds.
- **Pool full:** Check pool status at GET /api/v1/paper-trading/forex-pool/status
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Backend starts without errors when OANDA credentials are configured |
| AC2 | OANDA data stream connects and authenticates (visible in logs) |
| AC3 | Forex bar data persists to database |
| AC4 | Forex historical backfill runs for configured pairs |
| AC5 | `.env.example` includes OANDA pool account mapping variables |
| AC6 | Pool manager loads real account mappings from environment |
| AC7 | Pool allocation uses real OANDA account ID when mapped |
| AC8 | OANDA executor submits orders to the correct sub-account (or failure documented) |
| AC9 | Shadow tracking creates shadow position when pool is full |
| AC10 | Health endpoint reports OANDA connection status |
| AC11 | README has OANDA connectivity and forex pool runbook section |
| AC12 | All fixes documented in BUILDER_OUTPUT.md |
| AC13 | No frontend code modified |
| AC14 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

None expected unless pool mapping requires a new config module.

## Files to Modify

| File | What Changes |
|------|-------------|
| Pool manager (e.g., `backend/app/paper_trading/forex_pool/pool_manager.py`) | Add real account mapping from env vars |
| `backend/app/common/config.py` | Add OANDA pool account settings |
| `.env.example` | Add OANDA pool account variables |
| `README.md` | Add OANDA runbook section |
| Other backend files | Only if fixes needed (document in BUILDER_OUTPUT.md) |

## Builder Notes

- **You need real OANDA practice credentials.** If not available, verify as much as possible without them and document what requires keys.
- **OANDA sub-accounts:** Creating 4 sub-accounts in OANDA's practice environment may have limitations. If only 1 account is available, map it to pool slot 1 and leave slots 2-4 as virtual. The mixed mode should work.
- **OANDA streaming is HTTP, not WebSocket.** The OANDA adapter may use a different streaming approach than Alpaca. Check how `OandaStreamConnection` is implemented.
- **Forex runs 24/5.** Unlike equities, you can test forex data streaming outside US market hours (Sunday 5 PM ET through Friday 5 PM ET).
- **Instrument naming:** OANDA uses `EUR_USD` format. Verify this matches the internal symbol format.

## References

- market_data_module_spec.md §1 — Broker Abstraction (Alpaca + OANDA adapters)
- market_data_module_spec.md §Forex (OANDA) — universe filter, streaming, backfill
- paper_trading_module_spec.md §8 — Forex Account Pool (allocation, release, real account mapping)
- paper_trading_module_spec.md §9 — Shadow Tracking
- DECISION-005 — Forex account pool model (FIFO netting, per-pair isolation)
