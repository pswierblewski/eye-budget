# Database Migrations with Yoyo

This project uses [Yoyo Migrations](https://ollycope.com/software/yoyo/) to manage database schema changes.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure database connection:**
   Edit `yoyo.ini` and update the database connection string:
   ```ini
   database = postgresql://user:password@host:port/database_name
   ```

   Or use environment variables in your connection string:
   ```ini
   database = postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
   ```

## Common Commands

### Apply all pending migrations
```bash
yoyo apply
```

### Apply migrations in non-interactive mode
```bash
yoyo apply --batch
```

### Rollback the last migration
```bash
yoyo rollback
```

### Rollback all migrations
```bash
yoyo rollback --all
```

### Check migration status
```bash
yoyo list
```

### Mark migrations as applied without running them
Useful when migrating from manual SQL scripts:
```bash
yoyo mark
```

## Creating New Migrations

1. **Create a new migration file:**
   ```bash
   yoyo new -m "description of your migration"
   ```
   
   This creates a file like: `migrations/YYYYMMDD_NN_description-of-your-migration.sql`

2. **Edit the migration file:**
   ```sql
   -- Migration: Your description
   -- depends: YYYYMMDD_NN_previous_migration
   
   -- Apply
   CREATE TABLE example (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL
   );
   
   -- Rollback
   DROP TABLE IF EXISTS example;
   ```

### Migration File Structure

- **`-- depends:`** - List the migration(s) this one depends on (uses filename without extension)
- **`-- Apply`** - SQL commands to apply the migration (moving forward)
- **`-- Rollback`** - SQL commands to undo the migration (moving backward)

### Naming Convention

Migration files follow this pattern: `YYYYMMDD_NN_description.sql`
- `YYYYMMDD` - Date (e.g., 20241010)
- `NN` - Sequential number (01, 02, etc.)
- `description` - Brief description with underscores or hyphens

## Existing Migrations

The project currently has these migrations:

1. **20241010_01_receipts_scans.sql** - Creates receipts-scans table with status tracking
2. **20241010_02_categories.sql** - Creates category system with groups and hierarchical categories
3. **20241010_03_products.sql** - Creates products and alternative names tables

## Best Practices

1. **Always test migrations** in a development database first
2. **Write rollback scripts** for every migration (makes it easy to undo mistakes)
3. **Keep migrations small** - one logical change per migration
4. **Never edit applied migrations** - create a new migration instead
5. **Use transactions implicitly** - Yoyo wraps each migration in a transaction automatically
6. **Check dependencies** - ensure migrations run in the correct order

## Migration Workflow

### Typical Development Flow

1. Make schema changes by creating a new migration:
   ```bash
   yoyo new -m "add user_email_to_receipts"
   ```

2. Edit the generated file with your SQL changes

3. Apply the migration to your dev database:
   ```bash
   yoyo apply
   ```

4. Test your changes

5. If something's wrong, rollback:
   ```bash
   yoyo rollback
   ```

6. Fix the migration file and reapply

7. Commit the migration file to version control

### Deploying to Production

```bash
# Check what will be applied
yoyo list

# Apply all pending migrations
yoyo apply --batch
```

## Troubleshooting

### "Migration has already been applied"
If you've manually run SQL and want to mark migrations as applied:
```bash
yoyo mark
```

### "Database connection failed"
Check your `yoyo.ini` configuration and ensure:
- Database exists
- Credentials are correct
- PostgreSQL is running
- Host/port are accessible

### "Migration failed mid-way"
Yoyo uses transactions, so failed migrations are automatically rolled back. Fix the issue in your SQL and reapply.

## Example: Adding a New Column

```bash
# Create migration
yoyo new -m "add_processed_date_to_receipts"
```

Edit `migrations/YYYYMMDD_NN_add_processed_date_to_receipts.sql`:
```sql
-- Migration: Add processed_date column to receipts-scans
-- depends: 20241010_03_products

-- Apply
ALTER TABLE "receipts-scans" ADD COLUMN processed_date TIMESTAMP;

-- Rollback
ALTER TABLE "receipts-scans" DROP COLUMN IF EXISTS processed_date;
```

Apply:
```bash
yoyo apply
```

## Additional Resources

- [Yoyo Documentation](https://ollycope.com/software/yoyo/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

