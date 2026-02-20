# SPEC-008: Multi-Gmail Account Support

> **Status:** Draft
> **Author:** spec-writer agent
> **Created:** 2026-02-20
> **Updated:** 2026-02-20

## Goal

Allow users to connect up to 5 Gmail accounts so the agent gets a comprehensive picture of tasks, communications, and priorities across all their email accounts (work, personal, side-project, etc.). Today the system assumes one Gmail per user due to a `UNIQUE(user_id, service_name)` constraint — this spec removes that bottleneck, adds a standalone OAuth flow for additional accounts, fixes the broken token refresh, and updates all Gmail tools to operate across multiple accounts.

## Acceptance Criteria

- [ ] **AC-01:** Users can connect up to 5 Gmail accounts via a standalone FastAPI OAuth flow (accounts 2-5). The first account can still use the existing Supabase OAuth flow. [A1, A11]
- [ ] **AC-02:** The `external_api_connections` unique constraint changes from `(user_id, service_name)` to `(user_id, service_name, service_user_id)` so multiple Gmail rows can coexist per user. [A8]
- [ ] **AC-03:** A database-enforced limit of 5 Gmail connections per user prevents unbounded growth. [A12]
- [ ] **AC-04:** `gmail_search(query, account?)` searches a single account when `account` is specified, or ALL connected accounts when omitted (default). Results include the source account email. [A6, A11]
- [ ] **AC-05:** `gmail_get_message(message_id, account)` retrieves a message from the specified account. [A6]
- [ ] **AC-06:** `gmail_digest(hours_back, account?)` aggregates across all accounts by default, grouped by account email. Single-account mode when `account` is specified. [A6, A11]
- [ ] **AC-07:** Expired access tokens are automatically refreshed using the stored refresh token before any Gmail API call. Refreshed tokens are written back to Vault. [A14]
- [ ] **AC-08:** The frontend Settings/Integrations page shows a list of connected Gmail accounts with email addresses, and allows connecting additional accounts or disconnecting individual ones. [A4, A13]
- [ ] **AC-09:** Disconnecting a specific Gmail account targets by `connection_id`, not by `service_name` alone. [A9]
- [ ] **AC-10:** All RPCs that currently accept `(user_id, service_name)` are updated or supplemented to support multi-account lookup (returning arrays or accepting `connection_id`). [A1]
- [ ] **AC-11:** OAuth state parameter uses server-side nonce validation for CSRF protection. [A12]
- [ ] **AC-12:** Scheduled email digest runs iterate over ALL connected Gmail accounts for a user. [A7]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260221000000_multi_gmail_constraint.sql` | Drop old unique constraint, add new `(user_id, service_name, service_user_id)` unique constraint, add max-5 trigger, update RPCs |
| `chatServer/routers/oauth_router.py` | Standalone OAuth flow endpoints: `/oauth/gmail/connect` and `/oauth/gmail/callback` |
| `chatServer/services/oauth_service.py` | State management (nonce generation/validation), Google token exchange, credential storage |
| `tests/chatServer/routers/test_oauth_router.py` | OAuth router unit tests |
| `tests/chatServer/services/test_oauth_service.py` | OAuth service unit tests |
| `tests/chatServer/tools/test_gmail_tools_multi.py` | Multi-account Gmail tool tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/tools/gmail_tools.py` | Multi-account iteration in all tools, optional `account` parameter, token refresh logic |
| `chatServer/services/vault_token_service.py` | New methods: `get_tokens_for_connection(connection_id)`, `get_all_tokens_for_service(user_id, service_name)`, `update_access_token` to work with `connection_id` |
| `chatServer/routers/external_api_router.py` | Update `delete_api_connection` to accept `connection_id` instead of just `service_name`; update status endpoint to return count and list |
| `chatServer/services/email_digest_service.py` | Iterate over all Gmail connections when generating digest |
| `chatServer/main.py` | Register `oauth_router` |
| `webApp/src/components/features/GmailConnection/GmailConnection.tsx` | Multi-account list UI, "Add another account" button, per-account disconnect |
| `webApp/src/api/hooks/useExternalConnectionsHooks.ts` | New hooks: `useGmailConnections()` (list Gmail accounts), `useDisconnectConnection(connectionId)`, `useConnectAdditionalGmail()` |
| `webApp/src/pages/AuthCallback.tsx` | Handle callback from standalone OAuth flow (new `?source=standalone` parameter) |
| RPC `store_oauth_tokens` | Change `ON CONFLICT` clause from `(user_id, service_name)` to `(user_id, service_name, service_user_id)` |
| RPC `get_oauth_tokens` | Return all active connections for a service (as JSON array), or accept optional `p_connection_id` |
| RPC `get_oauth_tokens_for_scheduler` | Same multi-account support as `get_oauth_tokens` |
| RPC `revoke_oauth_tokens` | Accept optional `p_connection_id` for targeted revocation |
| RPC `check_connection_status` | Return count of active connections, not just boolean |

### Out of Scope

- Google Calendar multi-account support (backlog — gcal not in UI yet)
- Gmail send/reply capabilities (separate spec)
- Per-account tool approval tiers (all Gmail accounts share the same approval tier)
- Account nickname/label in UI (can be added later; email address is sufficient)
- Migration of existing single-account users (the new constraint is backward-compatible — existing rows already have `service_user_id` populated)

## Technical Approach

### 1. Database Migration (database-dev)

Per A8, RLS stays on `external_api_connections`. The migration:

```sql
-- 1. Drop the old unique constraint
ALTER TABLE external_api_connections
  DROP CONSTRAINT external_api_connections_user_id_service_name_key;

-- 2. Add new composite unique constraint (requires service_user_id NOT NULL for gmail)
ALTER TABLE external_api_connections
  ADD CONSTRAINT external_api_connections_user_service_account_key
  UNIQUE (user_id, service_name, service_user_id);

-- 3. Max-5 Gmail connections trigger
CREATE OR REPLACE FUNCTION check_max_gmail_connections()
RETURNS TRIGGER AS $$
DECLARE
  gmail_count INTEGER;
BEGIN
  IF NEW.service_name = 'gmail' THEN
    SELECT COUNT(*) INTO gmail_count
    FROM external_api_connections
    WHERE user_id = NEW.user_id
      AND service_name = 'gmail'
      AND is_active = true
      AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid);

    IF gmail_count >= 5 THEN
      RAISE EXCEPTION 'Maximum of 5 Gmail accounts per user reached';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_max_gmail_connections
  BEFORE INSERT OR UPDATE ON external_api_connections
  FOR EACH ROW EXECUTE FUNCTION check_max_gmail_connections();
```

**RPC updates** (same migration file):

- `store_oauth_tokens`: Change `ON CONFLICT (user_id, service_name)` to `ON CONFLICT (user_id, service_name, service_user_id)`. Require `p_service_user_id` to be NOT NULL for gmail.
- `get_oauth_tokens` / `get_oauth_tokens_for_scheduler`: Add optional `p_connection_id UUID DEFAULT NULL` parameter. When provided, return tokens for that specific connection. When NULL, return a JSON array of all active connections for the service.
- `revoke_oauth_tokens`: Add optional `p_connection_id UUID DEFAULT NULL`. When provided, revoke just that connection. When NULL, revoke all connections for the service (backward-compatible).
- `check_connection_status`: Return `json_build_object('connected', connection_count > 0, 'count', connection_count, 'service', p_service_name)`.

### 2. Standalone OAuth Flow (backend-dev)

Per A1, thin router delegates to service.

**`chatServer/routers/oauth_router.py`:**
```python
router = APIRouter(prefix="/oauth", tags=["oauth"])

@router.get("/gmail/connect")
async def initiate_gmail_connect(
    user_id: str = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> RedirectResponse:
    """Initiate OAuth flow for connecting an additional Gmail account."""
    auth_url = await oauth_service.create_gmail_auth_url(user_id)
    return RedirectResponse(url=auth_url)

@router.get("/gmail/callback")
async def gmail_oauth_callback(
    code: str,
    state: str,
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> RedirectResponse:
    """Handle OAuth callback from Google."""
    result = await oauth_service.handle_gmail_callback(code, state)
    # Redirect to frontend with success/error status
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?service=gmail&source=standalone&status={result.status}")
```

**`chatServer/services/oauth_service.py`:**
```python
class OAuthService:
    async def create_gmail_auth_url(self, user_id: str) -> str:
        """Generate Google OAuth URL with state parameter."""
        # 1. Generate nonce, store in Redis/DB with user_id + TTL (10 min)
        # 2. Build Flow with prompt="select_account consent", access_type="offline"
        # 3. Return authorization URL with state=nonce

    async def handle_gmail_callback(self, code: str, state: str) -> OAuthResult:
        """Exchange code for tokens, validate state, store in Vault."""
        # 1. Validate nonce from state parameter (CSRF protection — AC-11)
        # 2. Exchange code for tokens via google-auth-oauthlib Flow
        # 3. Call Google userinfo to get sub (service_user_id) and email
        # 4. Check max-5 limit (application-level, trigger is backup)
        # 5. Store tokens via store_oauth_tokens RPC
        # 6. Return success/error result
```

State storage: Use `oauth_states` table (simple approach, no Redis dependency):
```sql
CREATE TABLE oauth_states (
    nonce TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '10 minutes')
);
-- No RLS needed — only accessed by service role
```

### 3. Token Refresh (backend-dev)

Per A14 (pragmatic progressivism), fix the existing broken refresh rather than building a complex refresh daemon.

In `GmailToolProvider._get_google_credentials()`, after creating `Credentials`:

```python
from google.auth.transport.requests import Request as GoogleAuthRequest

# Check if token is expired or about to expire (5-min buffer)
if credentials.expired or (credentials.expiry and
    credentials.expiry < datetime.utcnow() + timedelta(minutes=5)):
    if credentials.refresh_token:
        credentials.refresh(GoogleAuthRequest())
        # Write refreshed token back to Vault
        await self._update_stored_token(connection_id, credentials.token, credentials.expiry)
    else:
        raise ValueError(
            f"Gmail access token expired and no refresh token available for {account_email}. "
            "Please reconnect this account."
        )
```

The `_update_stored_token` method calls `VaultTokenService.update_access_token()` with the `connection_id`.

### 4. Multi-Account Gmail Tools (backend-dev)

Per A6 (tools = capability units), update existing tool classes rather than creating new ones.

**Input schema changes:**

```python
class GmailSearchInput(BaseModel):
    query: str = Field(..., description="Gmail search query")
    max_results: int = Field(default=10, ge=1, le=50)
    account: Optional[str] = Field(
        default=None,
        description="Email address of the account to search. Omit to search ALL connected accounts."
    )

class GmailGetMessageInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID")
    account: str = Field(..., description="Email address of the account this message belongs to")

class GmailDigestInput(BaseModel):
    hours_back: int = Field(default=24, ge=1, le=168)
    include_read: bool = Field(default=False)
    max_emails: int = Field(default=20, ge=1, le=50)
    account: Optional[str] = Field(
        default=None,
        description="Email address of a specific account. Omit to aggregate across ALL accounts."
    )
```

**Multi-account iteration pattern:**

```python
class GmailToolProvider:
    def __init__(self, user_id: str, connection_id: str = None, context: str = "user"):
        self.user_id = user_id
        self.connection_id = connection_id  # Specific account
        self.context = context

    @classmethod
    async def get_all_providers(cls, user_id: str, context: str = "user") -> list["GmailToolProvider"]:
        """Get providers for ALL connected Gmail accounts."""
        connections = await cls._get_gmail_connections(user_id)
        return [cls(user_id, conn["id"], context) for conn in connections]

    @classmethod
    async def get_provider_for_account(cls, user_id: str, account_email: str, context: str = "user") -> "GmailToolProvider":
        """Get provider for a specific account by email."""
        connection = await cls._find_connection_by_email(user_id, account_email)
        if not connection:
            raise ValueError(f"No Gmail connection found for {account_email}")
        return cls(user_id, connection["id"], context)
```

**Search across all accounts:**
```python
async def _arun(self, query: str, max_results: int = 10, account: Optional[str] = None) -> str:
    if account:
        provider = await GmailToolProvider.get_provider_for_account(self.user_id, account)
        results = await self._search_single(provider, query, max_results)
        return self._format_results(results, account)
    else:
        providers = await GmailToolProvider.get_all_providers(self.user_id)
        all_results = []
        for provider in providers:
            account_email = provider.account_email
            results = await self._search_single(provider, query, max_results)
            all_results.append({"account": account_email, "results": results})
        return self._format_multi_account_results(all_results)
```

### 5. Frontend Multi-Account UI (frontend-dev)

Per A4, server state in React Query. Per A13, users can inspect and manage their connections.

**`useGmailConnections()` hook** — wraps `list_user_connections` RPC, filtered to `service_name='gmail'`:
```typescript
export function useGmailConnections() {
  const user = useAuthStore(state => state.user);
  return useQuery({
    queryKey: [EXTERNAL_CONNECTIONS_QUERY_KEY, user?.id, 'gmail', 'all'],
    queryFn: async () => {
      const { data } = await supabase.rpc('list_user_connections', { p_user_id: user.id });
      return (data.connections || []).filter(c => c.service_name === 'gmail');
    },
    enabled: !!user,
  });
}
```

**`useDisconnectConnection(connectionId)` hook** — calls updated `revoke_oauth_tokens` RPC with `p_connection_id`.

**GmailConnection component update:**
- Show list of connected accounts (email + connected date)
- "Add Gmail Account" button (up to 5) that opens `/oauth/gmail/connect` in same window
- Per-account "Disconnect" button
- Account count indicator (e.g., "2 of 5 accounts connected")

**AuthCallback update:**
- Detect `?source=standalone` parameter
- For standalone callbacks, extract tokens from URL and store via RPC (similar to existing flow but without Supabase Auth session dependency)

### Dependencies

- `google-auth-oauthlib` — already in `requirements.txt` for existing Gmail tools
- No new infrastructure (no Redis — using DB for OAuth state)

## Cross-Domain Contracts

### Migration -> Backend Contract

**Table:** `external_api_connections`
- New unique: `(user_id, service_name, service_user_id)`
- Max-5 trigger on `service_name = 'gmail'`

**RPC signatures (updated):**
```sql
-- Returns JSON array of all connections (when p_connection_id is NULL)
-- or single connection tokens (when p_connection_id is provided)
get_oauth_tokens(p_user_id UUID, p_service_name TEXT, p_connection_id UUID DEFAULT NULL) -> JSON
get_oauth_tokens_for_scheduler(p_user_id UUID, p_service_name TEXT, p_connection_id UUID DEFAULT NULL) -> JSON
store_oauth_tokens(..., p_service_user_id TEXT NOT NULL for gmail) -> JSON
revoke_oauth_tokens(p_user_id UUID, p_service_name TEXT, p_connection_id UUID DEFAULT NULL) -> JSON
check_connection_status(p_user_id UUID, p_service_name TEXT) -> JSON  -- now includes 'count'
```

**New table:** `oauth_states`
```sql
oauth_states(nonce TEXT PK, user_id UUID FK, created_at TIMESTAMPTZ, expires_at TIMESTAMPTZ)
```

### Backend -> Frontend Contract

**New endpoint:** `GET /oauth/gmail/connect`
- Auth: requires JWT
- Response: 302 redirect to Google OAuth
- Frontend opens this URL in same window or popup

**New endpoint:** `GET /oauth/gmail/callback`
- Params: `code`, `state`
- Response: 302 redirect to `{FRONTEND_URL}/auth/callback?service=gmail&source=standalone&status=success|error&error_message=...`

**Updated endpoint:** `DELETE /api/external/connections/{connection_id}`
- Changed from `/{service_name}` to `/{connection_id}` (UUID)
- Returns: `{ "message": "..." }`

**Updated RPC response:** `check_connection_status` now returns:
```json
{ "connected": true, "count": 2, "service": "gmail" }
```

### Gmail Tool Response Shapes

**Single-account search result:**
```
[work@gmail.com] Subject: Meeting tomorrow
  From: alice@company.com | Date: 2026-02-20 10:30
  Snippet: Let's discuss the Q1 roadmap...
  Message ID: 18d7a3b4c5e6f7g8 (account: work@gmail.com)
```

**Multi-account search result:**
```
=== work@gmail.com (3 results) ===
1. Subject: Meeting tomorrow...
2. Subject: Invoice #1234...

=== personal@gmail.com (1 result) ===
1. Subject: Flight confirmation...
```

## Testing Requirements

### Unit Tests (required)

**`tests/chatServer/routers/test_oauth_router.py`:**
- `test_initiate_connect_redirects_to_google` — verifies redirect URL format
- `test_initiate_connect_requires_auth` — 401 without JWT
- `test_callback_validates_state_nonce` — rejects invalid/expired nonce
- `test_callback_stores_tokens` — verifies token storage via RPC
- `test_callback_rejects_duplicate_account` — same Google account already connected

**`tests/chatServer/services/test_oauth_service.py`:**
- `test_create_auth_url_includes_required_params` — scope, access_type, prompt
- `test_handle_callback_validates_nonce` — expired nonce rejected
- `test_handle_callback_exchanges_code` — mocked Google token exchange
- `test_handle_callback_enforces_max_5` — 6th account rejected
- `test_nonce_single_use` — nonce deleted after use

**`tests/chatServer/tools/test_gmail_tools_multi.py`:**
- `test_search_single_account` — account param routes to correct connection
- `test_search_all_accounts` — omitted account param iterates all connections
- `test_search_all_includes_account_labels` — results tagged with account email
- `test_get_message_requires_account` — account param is required
- `test_digest_aggregates_across_accounts` — grouped by account
- `test_token_refresh_on_expired` — auto-refresh + vault update
- `test_token_refresh_no_refresh_token` — clear error message
- `test_no_connected_accounts` — graceful error

### Integration Tests

- `test_oauth_flow_end_to_end` — initiate -> callback -> tokens stored -> connection visible
- `test_multi_account_search_integration` — two accounts connected, search returns merged results
- `test_disconnect_specific_account` — disconnect one, other still works
- `test_max_5_enforcement` — 6th connection rejected at DB level

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Unit + Integration | `test_initiate_connect_redirects_to_google`, `test_oauth_flow_end_to_end` |
| AC-02 | Unit | `test_migration_constraint_allows_multi_gmail` (migration test) |
| AC-03 | Unit + Integration | `test_handle_callback_enforces_max_5`, `test_max_5_enforcement` |
| AC-04 | Unit | `test_search_single_account`, `test_search_all_accounts`, `test_search_all_includes_account_labels` |
| AC-05 | Unit | `test_get_message_requires_account` |
| AC-06 | Unit | `test_digest_aggregates_across_accounts` |
| AC-07 | Unit | `test_token_refresh_on_expired`, `test_token_refresh_no_refresh_token` |
| AC-08 | UAT | Manual: connect 2 accounts, verify UI shows list |
| AC-09 | Unit + Integration | `test_disconnect_specific_account` |
| AC-10 | Unit | `test_rpcs_support_connection_id_param` |
| AC-11 | Unit | `test_callback_validates_state_nonce`, `test_nonce_single_use` |
| AC-12 | Unit | `test_digest_service_iterates_all_accounts` |

### Manual Verification (UAT)

- [ ] Connect first Gmail via existing Supabase OAuth flow, verify it works as before
- [ ] Click "Add Gmail Account" in Settings, complete OAuth for a second Google account
- [ ] Verify both accounts appear in the connections list with correct email addresses
- [ ] Ask agent "search my email for invoices" — verify results from both accounts are returned, labeled by account
- [ ] Ask agent "check my work email for unread" with `account=work@gmail.com` — only that account searched
- [ ] Ask agent for email digest — verify digest groups results by account
- [ ] Disconnect one account, verify agent only searches the remaining account
- [ ] Attempt to connect a 6th account — verify friendly error message
- [ ] Wait for token to expire, then search — verify auto-refresh works transparently
- [ ] Verify scheduled digest still works and covers all connected accounts

## Edge Cases

- **No `service_user_id` on existing connection:** Existing connections pre-dating this spec may have `service_user_id = NULL`. The migration should backfill this from `service_user_email` or the Google userinfo endpoint. If neither is available, the account still works but cannot be deduplicated. The new unique constraint requires `service_user_id` to be NOT NULL for the constraint to function — handle NULL as a special case in the migration.
- **Same Google account connected twice:** The `UNIQUE(user_id, service_name, service_user_id)` constraint prevents this. The OAuth flow checks before inserting and returns a friendly "This account is already connected" message.
- **Token refresh race condition:** Two concurrent requests both detect an expired token and try to refresh. Google's token endpoint is idempotent for the same refresh token, so both get valid new tokens. The last write to Vault wins, which is fine since both tokens are valid.
- **Google revokes refresh token:** If Google revokes the refresh token (e.g., user removes app access from Google Account settings), the refresh attempt fails. The tool returns: "Gmail access expired for {account}. Please reconnect this account in Settings."
- **User deletes their Google account:** Token refresh fails. Same handling as revoked refresh token.
- **Partial failure in multi-account search:** If one account fails (e.g., token expired) but others succeed, return partial results with a warning: "Results from {failed_account} unavailable: {error}. Showing results from other accounts."
- **OAuth state nonce expiry:** If user takes longer than 10 minutes to complete the OAuth flow, the callback returns an error. The frontend shows "Authentication timed out. Please try again."
- **Callback CSRF attempt:** Invalid nonce in state parameter is rejected with 403. No tokens are exchanged.

## Functional Units (PR Breakdown)

### Merge Order

```
Unit 1 (migration) ──┐
                      ├── Unit 3 (Gmail tools multi-account + refresh)
Unit 2 (OAuth flow) ──┤
                      ├── Unit 4 (digest service update)
                      └── Unit 5 (frontend multi-account UI)
```

1. **FU-1:** Migration — constraint change + max-5 trigger + RPC updates + `oauth_states` table (`feat/SPEC-008-migration`) — **database-dev** — merge first
2. **FU-2:** Standalone OAuth flow — router + service + state management (`feat/SPEC-008-oauth-flow`) — **backend-dev** — can develop in parallel with FU-1, merge after FU-1
3. **FU-3:** Multi-account Gmail tools + token refresh (`feat/SPEC-008-gmail-tools`) — **backend-dev** — blocked by FU-1 (needs new RPC signatures)
4. **FU-4:** Email digest service multi-account update (`feat/SPEC-008-digest-multi`) — **backend-dev** — blocked by FU-3
5. **FU-5:** Frontend multi-account UI + hooks (`feat/SPEC-008-frontend`) — **frontend-dev** — blocked by FU-1 (needs updated RPCs) and FU-2 (needs OAuth endpoint)

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-12)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (schema -> API -> UI)
- [x] Technical decisions reference principles (A1, A4, A6, A7, A8, A9, A11, A12, A13, A14)
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
