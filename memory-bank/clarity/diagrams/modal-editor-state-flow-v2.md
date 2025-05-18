flowchart TD
    A[Start Open Modal] --> B[Snapshot state of parent & child objects]
    B --> C{Did user make any changes to parent or child state?}
    C -- No --> D[State is pristine]
    C -- Yes --> E[State is dirty]
    D --> F{User clicks Cancel, Save, or Close}
    F --> G[Close Modal]
    E --> H{User clicks Cancel}
    H --> I[Prompt: 'Discard changes?' Options: Yes, Cancel]
    I -- Yes --> J[Reset state, close modal]
    I -- Cancel --> K[Return to modal]
    E --> L{User clicks Save}
    L -- Any --> M[Persist state, reset dirty flag, close modal]
