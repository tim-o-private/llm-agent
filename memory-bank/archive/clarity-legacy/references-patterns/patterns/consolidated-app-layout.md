## Pattern 4: Consolidated Application Layout

**Goal:** Have a single, clear component defining the main application structure.

*   **DO:** Use only one component (e.g., `webApp/src/layouts/AppShell.tsx`) for the main application shell (sidebar, content area, header, etc.). This component is responsible for the consistent framing of pages that share this common layout.
*   **DO:** Ensure all routes requiring this main layout utilize this single `AppShell.tsx` component (or its designated equivalent) as their parent layout.
*   **DON'T:** Maintain multiple layout files (e.g., `MainLayout.tsx`, `DashboardLayout.tsx`) that serve the same fundamental purpose of defining the primary application page structure. If such redundant files exist, they should be consolidated or deleted.

This pattern promotes consistency in page structure, simplifies layout management, and makes it easier to apply global layout changes. 