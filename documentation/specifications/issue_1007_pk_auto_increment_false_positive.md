# Specification: Fix False Positive for BIGINT UNSIGNED AUTO_INCREMENT Primary Keys (Issue #1007)

**Type:** Bug Fix  
**Component:** `mysqltuner.pl` (Table structures analysis / Surrogate Key Recommendation)  
**Reference:** [Issue #1007](https://github.com/major/MySQLTuner-perl/issues/1007)  
**Assignee:** jmrenouard  
**Labels:** `bug`, `modeling`, `sql_schema`  

---

## 1. Problem Statement & Root Cause

When running MySQLTuner with `--structstat` (or `--reportfile`), the `mysql_table_structures` routine evaluates primary keys to verify surrogate key recommendations.
The recommendation advises using `BIGINT UNSIGNED AUTO_INCREMENT` for integer surrogate primary keys.

In MySQL 8.x (and all MySQL/MariaDB versions):
- In `information_schema.columns`, the `COLUMN_TYPE` column holds data type definitions such as `bigint unsigned` or `bigint(20) unsigned`.
- The `AUTO_INCREMENT` property is placed in the `EXTRA` column (`c.EXTRA`), not in `COLUMN_TYPE`.

The previous query in `mysqltuner.pl` only selected:
```sql
SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.COLUMN_TYPE
FROM information_schema.columns c
JOIN information_schema.tables t USING (TABLE_SCHEMA, TABLE_NAME)
WHERE t.TABLE_TYPE = 'BASE TABLE'
  AND c.COLUMN_KEY = 'PRI'
  AND c.TABLE_SCHEMA NOT IN ('sys', 'mysql', 'information_schema', 'performance_schema')
```
And then tested:
```perl
if (   $datatype !~ /int/i
    || $columntype !~ /unsigned/i
    || $columntype !~ /auto_increment/i )
```
Because `c.EXTRA` was omitted from the query and `COLUMN_TYPE` never contains `auto_increment` in MySQL, every properly configured `BIGINT UNSIGNED AUTO_INCREMENT` primary key caused `$columntype !~ /auto_increment/i` to be true. This triggered a false positive:
```text
Table <schema>.<table>: Primary key '<col>' is not a recommended surrogate key (BIGINT UNSIGNED AUTO_INCREMENT)
```

---

## 2. Target Solution

1. **Information Schema Query**:
   Update `SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.COLUMN_TYPE` to:
   ```sql
   SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.COLUMN_TYPE, c.EXTRA
   ```
2. **Column Extraction**:
   Extract `$extra` from the row:
   ```perl
   my ( $schema, $table, $column, $datatype, $columntype, $extra ) = split /\t/, $pk;
   $schema     //= '';
   $table      //= '';
   $column     //= '';
   $datatype   //= '';
   $columntype //= '';
   $extra      //= '';
   ```
3. **Condition Check**:
   Evaluate `extra` alongside `columntype` (maintaining backward compatibility with existing tests/mocks):
   ```perl
   if (   $datatype !~ /int/i
       || $columntype !~ /unsigned/i
       || ( $extra !~ /auto_increment/i && $columntype !~ /auto_increment/i ) )
   ```
4. **Unit Testing**:
   Update `tests/sql_modeling.t` to:
   - Provide realistic 6-column rows with `EXTRA` populated as `'auto_increment'` and `COLUMN_TYPE` without `auto_increment`.
   - Assert that valid surrogate keys (`BIGINT UNSIGNED AUTO_INCREMENT`) produce no false positive warnings.
   - Assert that primary keys missing `auto_increment` in `EXTRA` still properly trigger the recommendation.
