-- Rename manage_briefing_preferences → update_briefing_preferences
-- Handles databases where 000004 was already applied with the old name.
UPDATE tools SET name = 'update_briefing_preferences'
WHERE name = 'manage_briefing_preferences';
