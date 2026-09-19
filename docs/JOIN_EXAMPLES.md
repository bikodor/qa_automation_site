# JOIN scenarios

The schema contains both common relationship types:

- `auth_user → workspace_project → workspace_task`: one-to-many foreign keys.
- `workspace_task ↔ workspace_label`: many-to-many through `workspace_task_labels`.

Run `python manage.py seed_demo --reset` to create three projects, five labels and twelve connected tasks for `demo`. The command only resets demo-owned data.

## Tasks with owner and optional project

```sql
SELECT t.id, t.title, u.username, p.name AS project
FROM workspace_task AS t
JOIN auth_user AS u ON u.id = t.owner_id
LEFT JOIN workspace_project AS p ON p.id = t.project_id
WHERE u.username = 'demo'
ORDER BY t.id;
```

`LEFT JOIN` retains unassigned tasks; change it to `JOIN` to exclude them.

## Tasks with labels through the join table

```sql
SELECT t.title, l.name AS label, l.color
FROM workspace_task AS t
JOIN workspace_task_labels AS tl ON tl.task_id = t.id
JOIN workspace_label AS l ON l.id = tl.label_id
JOIN auth_user AS u ON u.id = t.owner_id
WHERE u.username = 'demo'
ORDER BY t.title, l.name;
```

## Aggregates by project

```sql
SELECT
    p.name,
    COUNT(DISTINCT t.id) AS task_count,
    COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) AS done_count,
    COUNT(DISTINCT tl.label_id) AS label_count
FROM workspace_project AS p
LEFT JOIN workspace_task AS t ON t.project_id = p.id
LEFT JOIN workspace_task_labels AS tl ON tl.task_id = t.id
JOIN auth_user AS u ON u.id = p.owner_id
WHERE u.username = 'demo'
GROUP BY p.id, p.name
ORDER BY p.name;
```

These values are also returned by `GET /api/projects/`.

## Complete project/label matrix

```sql
SELECT p.name AS project, l.name AS label, COUNT(tl.task_id) AS task_count
FROM workspace_project AS p
CROSS JOIN workspace_label AS l
LEFT JOIN workspace_task AS t ON t.project_id = p.id
LEFT JOIN workspace_task_labels AS tl
    ON tl.task_id = t.id AND tl.label_id = l.id
WHERE p.owner_id = l.owner_id
  AND p.owner_id = (SELECT id FROM auth_user WHERE username = 'demo')
GROUP BY p.id, l.id
ORDER BY p.name, l.name;
```

The matching API report is `GET /api/reports/project-summary/`. It includes zero-count combinations, which is useful for exact response and database assertions.

## Deletion assertions

Projects use `ON DELETE SET NULL` at the Django model level: tasks survive project deletion and become unassigned. Labels use a many-to-many join table: deleting a label removes its join rows while tasks and other labels remain. User deletion cascades to that user's projects, labels and tasks.

For isolation tests, create two users and verify that API filters and writes cannot use the other user's project or label IDs. Direct SQL can additionally assert that `task.owner_id`, `project.owner_id`, and `label.owner_id` agree for every relation created through the application.
