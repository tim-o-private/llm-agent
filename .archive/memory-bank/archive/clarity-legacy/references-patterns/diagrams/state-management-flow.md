# State Management Architecture: Data Flow Diagrams

## Core Data Flow: UI to Database

```mermaid
graph TD
    User[User Interaction] -->|Triggers action| Component[React Component]
    Component -->|Calls action| ZustandAction[Zustand Store Action]
    
    ZustandAction -->|Updates| LocalState[Local State]
    ZustandAction -->|Records in| PendingChanges[Pending Changes]
    
    LocalState -->|Re-renders| Component
    
    subgraph "Background Sync Process"
        Timer[Sync Timer<br>5-10s] -->|Triggers| SyncProcess[Sync Process]
        PendingChanges -->|Provides changes| SyncProcess
        SyncProcess -->|Uses| ReactQuery[React Query]
        ReactQuery -->|Calls| SupabaseAPI[Supabase API]
        SupabaseAPI -->|Writes to| Database[(Database)]
        
        SupabaseAPI -->|Returns result| ReactQuery
        ReactQuery -->|Returns result to| SyncProcess
        SyncProcess -->|Calls| ZustandUpdateAction[Zustand Update Action]
        ZustandUpdateAction -->|Updates| LocalState
        ZustandUpdateAction -->|Clears| PendingChanges
    end
    
    style User fill:#f9d71c,stroke:#e8c000,color:black
    style Component fill:#61dafb,stroke:#00b4d8,color:black
    style ZustandAction fill:#ffa69e,stroke:#ff686b,color:black
    style ZustandUpdateAction fill:#ffa69e,stroke:#ff686b,color:black
    style LocalState fill:#b39ddb,stroke:#7e57c2,color:white
    style PendingChanges fill:#b39ddb,stroke:#7e57c2,color:white
    style Timer fill:#66bb6a,stroke:#388e3c,color:white
    style SyncProcess fill:#ffb74d,stroke:#f57c00,color:black
    style ReactQuery fill:#90caf9,stroke:#1976d2,color:black
    style SupabaseAPI fill:#a5d6a7,stroke:#4caf50,color:black
    style Database fill:#e0e0e0,stroke:#9e9e9e,color:black
```

## Optimistic Update & Rollback Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React Component
    participant Store as Zustand Store
    participant RQ as React Query
    participant API as Supabase API
    participant DB as Database
    
    User->>UI: Triggers action (e.g., click update)
    UI->>Store: Call store action
    Store->>Store: Update local state immediately
    Store->>UI: Re-render with new state (optimistic)
    Store->>Store: Add to pendingChanges
    
    Note over Store: Background sync triggered
    
    Store->>RQ: Sync pendingChanges
    RQ->>API: Send API request
    
    alt Successful update
        API->>DB: Update data
        API->>RQ: Return success
        RQ->>Store: Clear pendingChanges
    else Failed update
        API->>RQ: Return error
        RQ->>Store: Revert optimistic update
        RQ->>Store: Flag error in pendingChanges
        Store->>UI: Re-render with previous state + error
        UI->>User: Show error notification
    end
```

## Initial Data Loading & Hydration

```mermaid
sequenceDiagram
    actor User
    participant App as App Container
    participant UI as Component
    participant Store as Zustand Store
    participant RQ as React Query
    participant API as Supabase API
    participant DB as Database
    
    User->>App: Load application
    App->>RQ: Initial data fetch request
    RQ->>API: Request tasks
    API->>DB: Query data
    DB->>API: Return data
    API->>RQ: Return response
    RQ->>Store: Hydrate store
    Store->>UI: Provide data
    UI->>User: Display content
    
    Note over Store,UI: Later component mounts
    
    User->>UI: Navigate to new view
    UI->>Store: Request data
    alt Data exists in store
        Store->>UI: Provide cached data immediately
    else Store needs refresh
        UI->>Store: Request refresh
        Store->>RQ: Fetch fresh data
        RQ->>API: Request data
        API->>DB: Query data
        DB->>API: Return data
        API->>RQ: Return response
        RQ->>Store: Update store
        Store->>UI: Provide fresh data
    end
```

## Sync Status & Error Recovery

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle --> SyncInProgress: Auto-sync triggered
    Idle --> SyncInProgress: Manual sync triggered
    
    SyncInProgress --> SyncSuccess: All changes synced
    SyncInProgress --> SyncPartial: Some changes synced
    SyncInProgress --> SyncFailed: Network error
    
    SyncSuccess --> Idle: Clear pending
    
    SyncPartial --> Idle: Retry later
    SyncPartial --> SyncInProgress: Immediate retry
    
    SyncFailed --> Backoff: Start exponential backoff
    Backoff --> SyncInProgress: Retry after delay
    
    SyncFailed --> ManualRecovery: User action required
    ManualRecovery --> SyncInProgress: User triggered sync
    
    state SyncFailed {
        [*] --> NetworkError
        [*] --> ServerError
        [*] --> ValidationError
    }
    
    state ManualRecovery {
        [*] --> RetryButton
        [*] --> DiscardChanges
        RetryButton --> [*]
        DiscardChanges --> [*]
    }
``` 